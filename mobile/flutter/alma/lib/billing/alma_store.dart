import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import '../net/alma_client.dart';
import '../net/models.dart';
import '../state/paywall_guard.dart';
import '../state/session.dart';
import 'ladder.dart';

/// Всё, что этот продукт знает о магазине.
///
/// Порт `mobile/ios/Alma/Billing/AlmaStore.swift`. Спрашивает цены, открывает
/// лист покупки, отдаёт подписанную покупку серверу, восстанавливает и слушает
/// то, что приходит, когда никто не смотрит. Ни один экран не импортирует
/// `in_app_purchase`, и ни один экран не решает, что человек чем-то владеет.
///
/// **Единственное правило, ради которого этот файл существует.** Покупка в
/// руке — это не право. Она уходит на `/v1/billing/iap/verify`, сервер
/// проверяет подпись магазина, и открывает главу **ответ сервера**. Всё, что
/// клиент может решить, клиента можно заставить решить.
///
/// **Почему один на процесс.** Поток `purchaseStream` обязан быть прочитан всю
/// жизнь приложения: одобрение «спросить у родителя», продление, возврат и
/// покупка, сделанная на другом устройстве, приходят туда в моменты, никак не
/// связанные с экранами. Второй слушатель забрал бы ту же покупку дважды.
class AlmaStore extends ChangeNotifier {
  AlmaStore._();

  static final AlmaStore shared = AlmaStore._();

  final InAppPurchase _iap = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _feed;
  AlmaSession? _session;

  /// Цены магазина по ступеням. Пусто — магазин ещё не ответил.
  final Map<LadderKey, ProductDetails> _products = {};

  StoreState _state = StoreState.idle;
  LadderKey? _busy;
  bool _restoring = false;
  StoreNotice? _notice;

  StoreState get state => _state;

  /// Какая ступень сейчас покупается. Пока она есть, лестница не отвечает на
  /// нажатия: два листа покупки подряд — это два списания.
  LadderKey? get busy => _busy;
  bool get restoring => _restoring;
  StoreNotice? get notice => _notice;

  /// Цена ступени строкой — **как её напечатал магазин**.
  ///
  /// Не серверная: доллары, показанные тому, кто платит в иенах, это число,
  /// которого с него не возьмут, — и по правилам App Review, и по-человечески.
  /// `null` значит «магазин молчит», и тогда цена не выдумывается.
  String? price(LadderKey key) => _products[key]?.price;

  /// Магазин не назвал **ни одного** товара.
  ///
  /// **Отличать это от «всё куплено» обязательно.** Обе ситуации оставляют
  /// полку пустой, и экран «все планы», не различив их, сказал человеку без
  /// единой покупки: «всё открыто, сорок одна глава твоя». Найдено глазами на
  /// симуляторе — там товаров в консоли ещё нет, и витрина показала дыру в
  /// пол-экрана с этой фразой над ней.
  ///
  /// Пустая полка при живом магазине — это правда о владельце. Пустая полка при
  /// молчащем магазине — это ничего не значащий факт о сети, и говорить по нему
  /// о правах человека нельзя.
  bool get silent => _products.isEmpty;

  /// Положить цены руками — **только для тестов**.
  ///
  /// Магазина в тестовой среде нет: `InAppPurchase` не отвечает, `_products`
  /// пуст, и витрина навсегда остаётся в состоянии «App Store молчит». Это
  /// состояние тоже надо проверять, но главный критерий эталона — что весь
  /// экран с ценами, кнопкой и юридикой помещается без прокрутки — без цен не
  /// проверяется вовсе: без них нет ни кнопки, ни абзаца о продлении, то есть
  /// нет как раз того, что не влезало.
  @visibleForTesting
  void seedPrices(Map<LadderKey, ProductDetails> products) {
    _products
      ..clear()
      ..addAll(products);
    notifyListeners();
  }

  /// Самая дешёвая из названных ступеней — для строки «от {price}».
  ///
  /// **Сравнение по `rawPrice`, а не по напечатанной строке.** «$4.99» и
  /// «78,99 €» не сравниваются как текст ни лексикографически, ни числом,
  /// вытащенным регуляркой: разделитель дробной части, положение символа
  /// валюты и разрядные пробелы у семи локалей разные. Магазин отдаёт число
  /// отдельно от подписи — оно и решает, а показывается всё равно подпись.
  ///
  /// Порядок ступеней в каталоге не обязан совпадать с порядком цен, поэтому
  /// «первая попавшаяся» здесь не годится: в день, когда неделя подорожает
  /// выше месяца, приглашение начнёт называть цену, которой на полке нет.
  ///
  /// `null` — магазин молчит: цену не выдумывают, а зовущая строка обходится
  /// без неё.
  String? cheapestOf(Iterable<LadderKey> keys) {
    ProductDetails? best;
    for (final key in keys) {
      final product = _products[key];
      if (product == null) continue;
      if (best == null || product.rawPrice < best.rawPrice) best = product;
    }
    return best?.price;
  }

  /// Привязать сессию. Идемпотентно, чтобы каждый экран, который трогает
  /// магазин, мог позвать это у себя, ни с кем не сговариваясь.
  void attach(AlmaSession session) {
    _session = session;
    _feed ??= _iap.purchaseStream.listen(
      _heard,
      onDone: () => _feed = null,
      onError: (Object error) =>
          debugPrint('поток покупок оборвался: $error'),
    );
  }

  /// Спросить магазин, что почём.
  Future<void> load() async {
    if (_state == StoreState.loading) return;
    _state = StoreState.loading;
    notifyListeners();

    if (!await _iap.isAvailable()) {
      // Магазина нет вовсе — и в отладке это тот же случай, что «есть, но
      // молчит»: показать надо витрину, а не жалобу. Ветка ниже одна на оба
      // пути, поэтому здесь только выход к ней, а не второй список цен.
      if (kDebugMode) {
        _products
          ..clear()
          ..addAll(_pretendPrices());
        _state = StoreState.ready;
        if (_notice?.message == StoreMessage.storeSilent) _notice = null;
        notifyListeners();
        return;
      }
      _state = StoreState.silent;
      notifyListeners();
      return;
    }

    final wanted = {for (final key in LadderKey.values) key.storeProductId: key};
    final answer = await _iap.queryProductDetails(wanted.keys.toSet());
    _products.clear();
    for (final product in answer.productDetails) {
      final key = wanted[product.id];
      if (key != null) _products[key] = product;
    }
    // Ни одного товара — это молчащий магазин, а не пустая полка: на
    // симуляторе без конфигурации StoreKit ответ выглядит именно так, и
    // рисовать лестницу без единой цены как «всё продано» было бы враньём.
    //
    // **В отладке молчание подменяется витринными ценами.** Товаров в консолях
    // ещё нет ни одного, и до тех пор каждый экран с ценой показывает «App
    // Store не отвечает» — то есть проверить глазами нельзя ровно то, ради чего
    // эти экраны построены. Владелец попросил прямо: «подставь фейк данные об
    // оплате чтобы я мог посмотреть как это будет выглядеть в финальном
    // варианте».
    //
    // `kDebugMode` — не стиль, а граница: в релизной сборке эта ветка
    // вырезается компилятором целиком, поэтому выдуманная цена физически не
    // может доехать до магазина. Числа те же, что в каталоге сервера, и живут
    // одним списком ниже, чтобы никто не искал их по экранам.
    if (_products.isEmpty && kDebugMode) _products.addAll(_pretendPrices());
    _state = _products.isEmpty ? StoreState.silent : StoreState.ready;
    // **Ответивший магазин гасит жалобу на молчащий.**
    //
    // `storeSilent` ставит неудавшееся восстановление покупок — и оставляло
    // навсегда: в настройках висела красная строка «App Store не отвечает» в то
    // самое время, когда на главе рядом стояла цена $4.99. Найдено глазами.
    //
    // Правда здесь на стороне полки: если магазин назвал товары, он отвечает, и
    // прошлая жалоба — это память о минуте, которой больше нет. Гасится только
    // она: ожидание покупки и отказ сервера принадлежат другим путям и живут
    // своей жизнью.
    if (_state == StoreState.ready &&
        _notice?.message == StoreMessage.storeSilent) {
      _notice = null;
    }
    notifyListeners();
  }

  /// Открыть лист покупки.
  ///
  /// Ничего не открывает сам: успех здесь означает только, что магазин принял
  /// платёж. Право приходит из [_claim], то есть с сервера.
  Future<void> buy(LadderKey key) async {
    final product = _products[key];
    // Ступень без товара — строка, которой не следовало быть нарисованной:
    // лестница строится только по тому, на что магазин ответил. Отказ вместо
    // падения — падать в секунду нажатия «купить» худшее из времён.
    if (_busy != null || product == null) return;
    _busy = key;
    _notice = null;
    notifyListeners();
    // **Ступень воронки отсюда не уходит, и это решение, а не пропуск.**
    //
    // Здесь стоял `checkout_opened`, и он принадлежит не нам. В `funnel.py` эта
    // ступень стоит в веб-цепочке `offer_view → checkout_opened → {покупка |
    // отказ}`, и пишет её **сервер**, когда сам открывает сессию Paddle для
    // браузера; там же сказано прямо: «приложения первый не пишут никогда».
    // Телефонная половина зовётся `checkout_started` и висит под
    // `paywall_shown`.
    //
    // Вред был не в лишней строке. Родителя `offer_view` телефон не шлёт
    // вовсе, так что каждая покупка из приложения надувала числитель веб-этапа
    // при неизменном знаменателе — а от той же ступени считается и конверсия в
    // `purchase`. Две воронки, сложенные в одну, дают число, которое нельзя
    // прочитать ни как веб, ни как телефон.
    //
    // **Почему не заменить имя здесь же.** `checkout_started` обязан нести
    // поверхность (`p0`…`p9`), и сервер без неё отвечает 422 — это его закон, а
    // не оформление. Магазин поверхности не знает и знать не может: он видит
    // ступень лестницы, а не экран, с которого пришли. Знает её оболочка
    // пейволла, и она эту ступень уже шлёт — по одной на каждую поверхность v3.
    //
    // Остаётся один непокрытый путь: старая витрина (`offer_screen.dart`) зовёт
    // `buy` напрямую, минуя оболочку. Её покупки временно не попадают в воронку
    // — и это лучше, чем прежнее враньё: экран снимается вместе с шагом
    // путешествия `s37`, когда построят `V1` (порядок задан в разделе VR
    // `docs/monetization/SCREENS-V3.md`).

    final purchase = PurchaseParam(productDetails: product);
    try {
      // `buyNonConsumable` и для подписок: расходуемых товаров у продукта нет
      // ни одного — ни главы, ни план не «тратятся».
      await _iap.buyNonConsumable(purchaseParam: purchase);
    } catch (error) {
      debugPrint('покупка ${key.slug} не открылась: $error');
      _busy = null;
      _notice = StoreNotice(StoreTone.bad, StoreMessage.storeSilent);
      notifyListeners();
    }
    // Дальше слово за `purchaseStream`: лист закрывается, и покупка приходит
    // туда — успехом, отменой или ожиданием.
  }

  /// То, что App Store требует от каждого приложения, продающего разовые
  /// покупки, и то, что действительно нужно человеку с новым телефоном.
  Future<void> restore() async {
    if (_restoring) return;
    _restoring = true;
    _notice = StoreNotice(StoreTone.waiting, StoreMessage.restoring);
    notifyListeners();
    try {
      await _iap.restorePurchases();
    } catch (error) {
      debugPrint('восстановление не удалось: $error');
      // **«Магазин не отвечает» — только когда он и правда не отвечал.**
      //
      // Здесь стояло это сообщение на любой отказ восстановления, и оно
      // оставалось на экране навсегда. Владелец увидел его под работающей
      // кнопкой «All of Alma · $9.99 / month» и сказал: «эта красная надпись
      // вообще везде, где есть покупка, и в настройках тоже».
      //
      // Полка знает правду: если магазин назвал товары, он отвечает, и
      // сорвавшееся восстановление — это отдельная неудача, а не молчание.
      // Тогда честнее сказать «ничего не восстановлено»: под этой покупкой
      // ничего не открылось, и это ровно тот факт, который человек проверял.
      // Молчание оставляем молчанию — пустой полке.
      _notice = _products.isEmpty
          ? StoreNotice(StoreTone.bad, StoreMessage.storeSilent)
          : StoreNotice(StoreTone.waiting, StoreMessage.restoredNone);
    }
    // Восстановленные покупки приезжают тем же потоком; здесь остаётся снять
    // ожидание, чтобы кнопка не крутилась вечно, если магазин не прислал
    // ничего — «ничего не нашлось» тоже ответ.
    _restoring = false;
    if (_notice?.message == StoreMessage.restoring) {
      _notice = StoreNotice(StoreTone.waiting, StoreMessage.restoredNone);
    }
    notifyListeners();
  }

  void clearNotice() {
    if (_notice == null) return;
    _notice = null;
    notifyListeners();
  }

  /* ── то, что приходит из магазина ─────────────────────────────────────── */

  Future<void> _heard(List<PurchaseDetails> purchases) async {
    for (final purchase in purchases) {
      switch (purchase.status) {
        case PurchaseStatus.pending:
          // «Спросить у родителя» или способ оплаты, которому нужен шаг вне
          // приложения. Ничего не списано и заканчивать нечего: покупка придёт
          // сюда же, если и когда её одобрят.
          _notice = StoreNotice(StoreTone.waiting, StoreMessage.pending);
          notifyListeners();

        case PurchaseStatus.canceled:
          // Молчание на экране, намеренно: закрывший лист сказал «нет», и
          // приложение, отвечающее на это сообщением, начинает спорить. Но в
          // отчёт это уходит — «закрыл лист Apple» и «нажал не сейчас» оба
          // `offer_declined`, и на нативе они шлются из обоих мест. Без
          // первого воронка теряет ровно тех, кто дошёл до оплаты и передумал
          // на последнем шаге.
          final cancelled = LadderKey.fromStoreProductId(purchase.productID);
          if (cancelled != null) {
            _session?.client.track(FunnelStage.offerDeclined,
                meta: {'product': cancelled.slug});
          }
          _busy = null;
          notifyListeners();

        case PurchaseStatus.error:
          debugPrint('магазин отказал: ${purchase.error}');
          _busy = null;
          _notice = StoreNotice(StoreTone.bad, StoreMessage.storeSilent);
          notifyListeners();

        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          // **Завершать — только когда завершать безопасно.**
          //
          // Здесь стояло «завершать обязательно и всегда», и это была самая
          // дорогая строка во всём файле. Незавершённая покупка возвращается
          // при каждом запуске — это неприятно; завершённая раньше времени не
          // возвращается **никогда**, и человек, с которого магазин взял
          // деньги, остаётся без главы и без способа её получить. Из двух
          // сторон ошибаться можно только в первую.
          //
          // Правило снято с натива дословно (`StoreProblem.mayFinishTransaction`):
          // завершать на успехе и на отказе, который никогда не станет
          // согласием, — не тот товар, покупка отозвана, аккаунта больше нет.
          // Всё остальное — неподтверждённая подпись, молчащий сервер, мёртвая
          // сеть — может получиться со следующей попытки, а транзакция это
          // единственное доказательство, что деньги ушли.
          final mayFinish = await _claim(purchase);
          if (mayFinish && purchase.pendingCompletePurchase) {
            await _iap.completePurchase(purchase);
          }
      }
    }
  }

  /// Отдать покупку серверу и перечитать права.
  ///
  /// Возвращает, **можно ли завершать транзакцию** — единственное необратимое
  /// решение во всей этой работе, и потому оно возвращается значением, а не
  /// угадывается на месте вызова.
  Future<bool> _claim(PurchaseDetails purchase) async {
    final session = _session;
    // Аккаунт должен существовать раньше, чем уйдёт чек: иначе сервер заведёт
    // под покупку нового гостя, и оплаченное откроется у того, кого человек
    // никогда не увидит.
    await session?.whenReady();
    final key = LadderKey.fromStoreProductId(purchase.productID);
    if (session == null || key == null) {
      // Товар, которого этот клиент не знает: сборка старше сервера или
      // наоборот. Держать транзакцию вечно смысла нет — она не станет нашей
      // от ожидания, — но и завершать чужую покупку мы не вправе, поэтому
      // ждём следующего запуска, где сборка может оказаться новее.
      debugPrint('покупка с неизвестным товаром: ${purchase.productID}');
      _busy = null;
      notifyListeners();
      return false;
    }
    try {
      final answer = await session.client.verifyPurchase(
        // **`googleplay`, а не `playstore`.** Так называется адаптер на
        // сервере (`alma/billing/googleplay.py`), и он отвечает 400 «магазин,
        // которого эта сборка не знает» на любое другое слово — то есть
        // каждая покупка на Android отваливалась бы на последнем шаге.
        platform: Platform.isIOS ? 'appstore' : 'googleplay',
        // Слаг каталога — из подписанного магазином идентификатора, а не из
        // нажатой кнопки.
        product: key.slug,
        transaction: purchase.verificationData.serverVerificationData,
      );
      await session.refreshRights();
      // **«Открыто» говорится по списку прав, а не по факту ответа 200.**
      //
      // Сервер отвечает 200 и на случай «ничего не выдано»: `status` бывает
      // `not_offered`, и единственное поле, которому можно верить, — это
      // `unlocked`, тот же список, что отдаёт `/billing/entitlements`.
      // Радостная строка над закрытой главой — худшее, что можно показать
      // человеку, который только что заплатил.
      final unlocked = ((answer['unlocked'] as List?) ?? const []).isNotEmpty ||
          session.entitlements.hasPlan;
      if (unlocked) {
        // **Только когда сервер действительно выдал.** Ступень «куплено»,
        // отправленная по факту ответа 200, считала бы и те покупки, под
        // которыми ничего не открылось.
        session.client.track(FunnelStage.purchaseCompleted,
            meta: {'product': key.slug});
        // И с этой секунды продукт десять минут ничего не продаёт (§5 ТЗ,
        // правило 3). Часы заводятся **здесь**, а не на экране покупки:
        // покупка приходит и без экрана — восстановлением, отложенным
        // одобрением, покупкой на другом устройстве, — а тишина после денег
        // положена в любом случае.
        PaywallGuard.notePurchase();
      }
      _notice = unlocked
          ? StoreNotice(
              StoreTone.good,
              purchase.status == PurchaseStatus.restored
                  ? StoreMessage.restored
                  : StoreMessage.unlocked,
            )
          : StoreNotice(StoreTone.waiting, StoreMessage.verifyLater);
      _busy = null;
      notifyListeners();
      // Сервер ответил и записал, что смог: транзакция своё дело сделала.
      return true;
    } on AlmaError catch (error) {
      // Деньги магазин уже взял. Разница между «мы не смогли спросить» и «это
      // не та покупка» существенна и для того, кто читает, и для того,
      // завершать ли транзакцию.
      debugPrint('сервер не подтвердил покупку: $error');
      final refused = error is ServerRefused ? error : null;
      final code = refused?.code;
      // Отказ, который никогда не станет согласием: не тот товар, покупка
      // отозвана магазином, аккаунт удалён. Держать такую транзакцию — значит
      // слать один и тот же запрос при каждом запуске до конца жизни установки.
      final permanent = code == 'product_mismatch' ||
          code == 'purchase_incomplete' ||
          refused?.status == 410;
      _notice = StoreNotice(
        StoreTone.bad,
        switch (true) {
          _ when error is NetworkDown => StoreMessage.offline,
          _ when code == 'purchase_incomplete' => StoreMessage.withdrawn,
          _ when (refused?.status ?? 0) >= 500 => StoreMessage.verifyLater,
          _ => StoreMessage.notVerified,
        },
      );
      _busy = null;
      notifyListeners();
      return permanent;
    }
  }

  @override
  void dispose() {
    _feed?.cancel();
    super.dispose();
  }
}

/// Что сейчас с полкой.
enum StoreState {
  idle,
  loading,

  /// Магазин ответил, цены есть.
  ready,

  /// Магазин не отвечает: цен нет и купить нельзя, но полка всё равно
  /// показывается — что на ней лежит, известно и без App Store.
  silent,
}

enum StoreTone { good, waiting, bad }

/// Что сказать человеку. Перечислением, а не строкой: строку берёт экран, у
/// которого есть язык, — здесь его нет и быть не должно.
enum StoreMessage {
  storeSilent,
  pending,
  offline,
  notVerified,

  /// Магазин деньги взял, а мы в эту секунду не смогли подтвердить. Само
  /// откроется: у обоих магазинов есть своё уведомление, которое дойдёт до
  /// сервера независимо от приложения.
  verifyLater,

  /// Возврат или отмена: под этой покупкой ничего не открыто и не откроется.
  withdrawn,
  unlocked,
  restoring,
  restored,
  restoredNone,
}

class StoreNotice {
  const StoreNotice(this.tone, this.message);

  final StoreTone tone;
  final StoreMessage message;
}

/// Витринные цены для отладочной сборки — см. довод в [AlmaStore.load].
///
/// Значения те же, что в `backend/alma/billing/catalogue.py`: пять дверей и
/// проверка пары по $4.99, бандл $19.99, подписка $9.99 в месяц. Валюта
/// доллар — настоящий магазин подставил бы местную, и это одно из отличий,
/// которое здесь нельзя увидеть.
Map<LadderKey, ProductDetails> _pretendPrices() {
  const money = <LadderKey, String>{
    LadderKey.natal: '4.99',
    LadderKey.numerology: '4.99',
    LadderKey.birthCard: '4.99',
    LadderKey.astrocartography: '4.99',
    LadderKey.synthesis: '4.99',
    LadderKey.pairCheck: '4.99',
    LadderKey.bundleStatic: '19.99',
    LadderKey.subMonthly: '9.99',
  };
  return {
    for (final entry in money.entries)
      entry.key: ProductDetails(
        id: entry.key.storeProductId,
        title: entry.key.slug,
        description: '',
        price: '\$${entry.value}',
        rawPrice: double.parse(entry.value),
        currencyCode: 'USD',
      ),
  };
}
