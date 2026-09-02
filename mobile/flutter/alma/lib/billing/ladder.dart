import '../l10n/alma_l10n.dart';
import '../net/models.dart';

/// Ступени лестницы: всё, что вообще можно купить.
///
/// Порт `mobile/ios/Alma/Billing/LadderKey.swift`. Значения — ключи каталога,
/// один в один с `alma/billing/catalogue.py`: сервер решает, какие ступени
/// сегодня на полке и почём, клиент — как они называются и в каком порядке
/// стоят.
///
/// **Ключ каталога больше не равен слагу системы.** До v3 `'natal'` был и
/// названием товара, и названием того, что он открывает, и полка была «восемь
/// дверей плюс архив». Теперь полка разнородная — пять дверей, пара, бандл,
/// подписка, — и `system` стало отдельным полем. Через `SystemSlug.from(slug)`
/// его больше не вывести: `SystemSlug.from('door.natal')` — это `null`, то есть
/// ступень без названия и без цены на экране.
///
/// **Дверей пять, а не восемь.** Транзиты и соляр пересчитываются, и продать их
/// «навсегда» значит продать подписку, не взяв за неё денег; совместимость
/// покупается на конкретного человека (`pair.check`), а не системой.
enum LadderKey {
  natal('door.natal', SystemSlug.natal),
  numerology('door.numerology', SystemSlug.numerology),
  birthCard('door.birth-card', SystemSlug.birthCard),
  astrocartography('door.astrocartography', SystemSlug.astrocartography),
  synthesis('door.synthesis', SystemSlug.synthesis),

  /// Один отчёт про одну пару. В магазинах — расходуемый: покупается столько
  /// раз, сколько партнёров человек проверит.
  ///
  /// `system` здесь намеренно `null`, а не `compatibility`: покупается не
  /// система, а отчёт про конкретного человека. Ответить системой — значит
  /// нарисовать в хабе «совместимость открыта» после первой покупки и упереться
  /// в пейволл на втором партнёре.
  pairCheck('pair.check', null),

  /// Все пять разборов, которые не меняются, — разом и навсегда.
  bundleStatic('bundle.static', null),

  /// Всё, пока подписка жива.
  subMonthly('sub.monthly', null),

  /// Пачки вопросов (01.09.2026, витрина Co-Star «дешёвый первый платёж»):
  /// кучка ходов сильной модели, тратится после включённых порций.
  /// Расходуемые — покупаются сколько угодно раз, размеры складываются.
  questions5('questions.5', null),
  questions10('questions.10', null),
  questions25('questions.25', null),

  /// «Год вперёд»: полный соляр до следующего дня рождения. Расходуемый —
  /// следующий год покупается снова; `system` намеренно null: это аренда
  /// на год, не дверь, и рисовать её дверью соляра нельзя.
  reportYear('report.year', null);

  /// Расходуемая ли ступень — то есть покупается ли она многократно.
  ///
  /// Ровно одна: проверка пары. От ответа зависит **магазинный вызов**
  /// (`buyConsumable` против `buyNonConsumable`), и ошибка здесь не косметика:
  /// consumable, купленный как non-consumable, Play продаёт один раз за жизнь
  /// аккаунта — вторая пара не купилась бы никогда.
  bool get consumable => const {
        LadderKey.pairCheck,
        // Пачки и год (01.09.2026): non-consumable в Play продавался бы
        // один раз за жизнь аккаунта — вторая пачка не купилась бы никогда.
        LadderKey.questions5,
        LadderKey.questions10,
        LadderKey.questions25,
        LadderKey.reportYear,
      }.contains(this);

  const LadderKey(this.slug, this.system);

  final String slug;

  /// Система, которую открывает ступень, или `null`, если она открывает больше
  /// одной — или, как у пары, вообще не систему.
  final SystemSlug? system;

  static LadderKey? from(String? raw) {
    for (final key in LadderKey.values) {
      if (key.slug == raw) return key;
    }
    return null;
  }

  /// Дверь для системы, если она у неё есть. У транзитов, соляра и
  /// совместимости двери нет — их продаёт подписка и `pair.check`.
  static LadderKey? doorFor(SystemSlug system) {
    for (final key in LadderKey.values) {
      if (key.system == system) return key;
    }
    return null;
  }

  /// Спишет ли магазин ещё раз. От этого зависит, какое раскрытие стоит над
  /// кнопкой: о повторном списании человек обязан узнать до нажатия, а не из
  /// выписки.
  bool get isSubscription => this == LadderKey.subMonthly;

  /// Идентификатор товара в консолях магазинов.
  ///
  /// **Вычисляется, а не хранится таблицей** — то же решение, что в
  /// `StoreProvider.store_product_id` на сервере и в `LadderKey.swift`:
  /// правило одно, записано трижды и трижды закрыто тестом, а вторая таблица
  /// была бы вторым местом, которое однажды разойдётся с консолью. Правило:
  /// ключ каталога с приставкой `ai.pazl.alma.`, дефисы заменены
  /// подчёркиваниями — дефис в идентификаторе не принимают ни App Store
  /// Connect, ни Play, а точку принимают оба.
  static const prefix = 'ai.pazl.alma.';
  String get storeProductId => prefix + slug.replaceAll('-', '_');

  /// Обратное — для покупки, которая пришла из магазина, а не из нажатой
  /// кнопки. Однозначно, потому что подчёркивания нет ни в одном ключе
  /// каталога.
  static LadderKey? fromStoreProductId(String id) {
    if (!id.startsWith(prefix)) return null;
    return LadderKey.from(id.substring(prefix.length).replaceAll('_', '-'));
  }

  /// Названия ступеней — из словаря v3, а не из прежней лестницы.
  ///
  /// **Набор говорил словами архива, и это была ложь о товаре.** Здесь стояли
  /// `paywallArchiveTitle` («All eight systems») и `paywallArchiveNote` («All
  /// eight systems, bought once») — имя и подпись архива за $38.99, которого
  /// в продукте нет с монетизации v3. А продаётся набор из **пяти** разборов
  /// за $19.99. Человек читал про восемь систем и платил за пять; на экране
  /// планов при этом уже стояла верная строка, то есть продукт называл один и
  /// тот же товар двумя разными именами.
  ///
  /// Заимствование помечалось временным «до фазы Ф1» — но словарь `paywall.v3`
  /// давно заведён и переведён на семь языков, ждать было нечего.
  String title(L l) => switch (this) {
        LadderKey.bundleStatic => l.paywallV3BundleTitle,
        LadderKey.subMonthly => l.paywallMonthlyTitle,
        LadderKey.pairCheck => systemTitle(l, SystemSlug.compatibility),
        _ => systemTitle(l, system ?? SystemSlug.natal),
      };

  String note(L l) => switch (this) {
        LadderKey.bundleStatic => l.paywallV3BundleIncludes,
        LadderKey.subMonthly => l.paywallMonthlyNote,
        _ => l.paywallDoorNote,
      };

  /// Имена систем **из словаря витрины**, а не из кабинета: у ступени лестницы
  /// свой набор строк (`paywall.systemName` на iOS), и он короче — на кнопке и
  /// в строке с ценой длинному имени не хватает места.
  static String systemTitle(L l, SystemSlug slug) => switch (slug) {
        SystemSlug.natal => l.paywallSystemNatal,
        SystemSlug.numerology => l.paywallSystemNumerology,
        SystemSlug.birthCard => l.paywallSystemBirthCard,
        SystemSlug.transits => l.paywallSystemTransits,
        SystemSlug.solarReturn => l.paywallSystemSolarReturn,
        SystemSlug.compatibility => l.paywallSystemCompatibility,
        SystemSlug.astrocartography => l.paywallSystemAstrocartography,
        SystemSlug.synthesis => l.paywallSystemSynthesis,
      };
}

/// Зачем открыли продающий экран. Пять поверхностей ТЗ §6 и ни одной больше.
///
/// Прежних было три — дверь, витрина под системой, витрина целиком, — и они
/// описывали лестницу из тринадцати SKU. v3 продаёт по одной цене за раз, и
/// поверхности названы по тому, **что человек только что сделал**, а не по тому,
/// как густо на экране:
///
/// * [PaywallIntent.door] (P1, P2) — тап по закрытой главе статичного разбора;
/// * [PaywallIntent.subscription] (P5) — тап по закрытому живому слою, и
///   [PaywallIntent.questionQuota] (P6) — упёршийся в квоту вопрос; полка у них
///   одна, вид разный;
/// * [PaywallIntent.pair] (P4) — закрытая глава I пары «Притяжение»;
/// * [PaywallIntent.plans] (P7) — тихая ссылка «все планы», единственный экран,
///   где видно всё;
/// * [PaywallIntent.cancelSave] (P8) — вход в отмену подписки.
///
/// ## Дверь и лестница — разные поверхности, и сливать их нельзя
///
/// **Записано здесь, потому что сливали их уже дважды и сольют снова.** Довод
/// каждый раз один и тот же и звучит убедительно: «раз человек всё равно
/// смотрит на цену, покажем рядом и план — вдруг возьмёт дороже». Он неверен, и
/// вот почему.
///
/// *Дверь* открывается тапом по закрытой главе. Человек в эту секунду занят не
/// выбором тарифа: он потянулся к одному конкретному тексту и хочет его
/// прочесть. Работа двери — назвать цену **этой** системы и открыть её одним
/// нажатием. Всё остальное на ней — шум, который превращает «купить и читать» в
/// «сесть и разобраться», а разбираться посреди чтения никто не станет: он
/// закроет экран и уйдёт. Поэтому дверь продаёт ровно одну систему, и
/// [ladderFor] здесь не дописывает **ни одной** ступени — правило живёт в этом
/// файле, а не в разметке экрана, чтобы следующая витрина не завела его заново
/// по-своему.
///
/// *Лестница* ([PaywallIntent.plans]) открывается тогда, когда человек сам
/// спросил «а что тут вообще есть». Её работа прямо противоположная — показать
/// все ступени и дать сравнить. Туда с двери ведёт тихая ссылка «все планы», и
/// это единственная законная дорога от одной к другой: выбор тарифа сделан по
/// своей воле, а не подсунут поверх чужого намерения.
///
/// Витрина под системой (`s37`, «шаг путешествия») из перечня ушла: по §3 ТЗ
/// после расчёта сразу открывается бесплатная глава I, а цена появляется в её
/// конце — то есть дверью, а не лестницей.
enum PaywallSurface { door, subscription, pair, plans, cancelSave }

class PaywallIntent {
  /// P1/P2: одна система, одна кнопка, никакой лестницы.
  const PaywallIntent.door(SystemSlug this.system)
      : surface = PaywallSurface.door,
        questions = false;

  /// P5: живой слой — продаётся только подписка.
  const PaywallIntent.subscription()
      : system = null,
        surface = PaywallSurface.subscription,
        questions = false;

  /// P6: квота вопросов. **Поверхность та же, что у P5, и это не небрежность.**
  ///
  /// Поверхностей в ТЗ §6 пять, и шестой здесь не заводится: полка у обоих
  /// экранов одна и та же — один план, `sub.monthly`, — то есть [ladderFor]
  /// обязан ответить им одинаково, а разница живёт в **виде**: V6 продаёт
  /// живой слой тому, кто ткнул в закрытый блок, V7 отвечает на упёршийся в
  /// квоту вопрос и обязан показать этот вопрос удержанным. Разведи их
  /// поверхностями — и лестница получит второй способ сказать «месячный
  /// план», который однажды разойдётся с первым.
  ///
  /// Сам текст вопроса сюда не кладётся: намерение — это про товар, а не про
  /// то, что человек набрал. Вопрос экран получает от того, кто его открыл.
  const PaywallIntent.questionQuota()
      : system = null,
        surface = PaywallSurface.subscription,
        questions = true;

  /// P4: закрытая глава пары. Одна цена, $4.99 за отчёт.
  ///
  /// **Отдельного бесплатного тизера пары больше нет** — решение владельца от
  /// 17 августа 2026. Тизер «Притяжение» и глава I пары — одно и то же: тот же
  /// маршрут главы, тот же паттерн залоченной главы (`locked-chapter-spec.md`,
  /// кадр C6), и цена появляется под написанным абзацем, а не на отдельном
  /// экране до него. Второй бесплатный текст про ту же пару означал бы платить
  /// за генерацию дважды и продавать одно и то же дважды.
  const PaywallIntent.pair()
      : system = null,
        surface = PaywallSurface.pair,
        questions = false;

  /// P7: единственный экран, где видно всё, — «Навсегда» и «Подписка».
  const PaywallIntent.plans()
      : system = null,
        surface = PaywallSurface.plans,
        questions = false;

  /// P8: спасение отмены. Дверь самой читаемой системы, один раз за жизнь
  /// подписки, с кнопкой «просто отменить» такой же силы.
  const PaywallIntent.cancelSave(SystemSlug this.system)
      : surface = PaywallSurface.cancelSave,
        questions = false;

  /// Система, вокруг которой открыли экран, — у двери и у спасения отмены.
  final SystemSlug? system;

  final PaywallSurface surface;

  /// Пришли ли сюда с потраченной квотой вопросов (P6), а не из живого слоя.
  final bool questions;

  /// Код поверхности §3 ТЗ — тот, которого сервер ждёт в каждом событии
  /// монетизации (`alma/funnel.py`, `SURFACES`).
  ///
  /// **Считается здесь, а не на экране.** Событие `paywall_shown` без
  /// поверхности сервер не пишет вовсе, а посчитанное по месту оно разойдётся
  /// с поверхностью ровно тогда, когда появится второй экран, продающий то же
  /// самое: `p5` и `p6` — две когорты, и склеенные они отвечают на вопрос
  /// «какая поверхность продаёт» одним числом, то есть никак.
  String get surfaceCode => switch (surface) {
        PaywallSurface.door => 'p2',
        PaywallSurface.subscription => questions ? 'p6' : 'p5',
        PaywallSurface.pair => 'p4',
        PaywallSurface.plans => 'p7',
        PaywallSurface.cancelSave => 'p8',
      };

  /// Показывать ли больше одной ступени. Только на «Всех планах» — принцип 2
  /// ТЗ: одна цена на экране, лестниц из трёх строк не существует нигде ещё.
  bool get ladder => surface == PaywallSurface.plans;

  bool get isDoor =>
      surface == PaywallSurface.door || surface == PaywallSurface.cancelSave;
}

/// Какие ступени показать и в каком порядке.
///
/// Порт `Storefront.offers(for:held:)`, переписанный под полку v3. Здесь стоит
/// вся выстраданная логика натива, и переносится она дословно:
///
/// * **дверь она и есть дверь**: у [PaywallSurface.door] лестницы нет вовсе, и
///   эта функция возвращает ровно одну ступень. Довод целиком — в шапке
///   [PaywallIntent]; коротко: экран, открытый тапом по закрытой главе, продаёт
///   одну систему, и всё, что дописано к ней, отвечает на вопрос, которого
///   человек не задавал;
/// * **у живых систем двери нет**, и тап по их закрытой главе — это не пустой
///   экран, а пейволл подписки (ТЗ P2). Транзиты пересчитываются каждый день, а
///   соляр переписывается к каждому дню рождения: продать их «навсегда» значит
///   продать подписку, не взяв за неё денег;
/// * **ступень исчезает у того, кто ей уже владеет**: предложить купить то, что
///   куплено, — самый быстрый способ выглядеть мошенником;
/// * **планы исчезают целиком у того, у кого план уже есть**: смена плана — это
///   изменение внутри группы подписок на экране магазина, а не вторая покупка.
///
/// Цены здесь нет намеренно: какие ступени существуют, решает наш каталог,
/// сколько они стоят — магазин. Ступень без цены всё равно рисуется, пустой
/// колонкой: то, что мы знаем сами, показывается и тогда, когда App Store
/// молчит, — иначе на отвалившейся сети подписки просто не существует нигде в
/// продукте.
List<LadderKey> ladderFor({
  required PaywallIntent intent,
  required Entitlements held,
  required List<Plan> shelf,
}) {
  final onTheShelf = <LadderKey>{};
  for (final plan in shelf) {
    if (plan.offered != 'shelf') continue;
    final key = LadderKey.from(plan.slug);
    if (key != null) onTheShelf.add(key);
  }

  List<LadderKey> only(Iterable<LadderKey> keys) {
    final seen = <LadderKey>{};
    return [
      for (final key in keys)
        if (onTheShelf.contains(key) && seen.add(key)) key,
    ];
  }

  final door = intent.system;
  switch (intent.surface) {
    case PaywallSurface.door:
    case PaywallSurface.cancelSave:
      if (door == null) return const [];
      if (held.unlocked.contains(door.slug)) return const [];
      final key = LadderKey.doorFor(door);
      // Двери нет — значит система живая, и продаётся она подпиской. Пустой
      // список здесь был бы экраном с заголовком и без единой кнопки.
      return only([key ?? LadderKey.subMonthly]);

    case PaywallSurface.subscription:
      return held.hasPlan ? const [] : only(const [LadderKey.subMonthly]);

    case PaywallSurface.pair:
      // Пара покупается поштучно, поэтому «уже куплено» здесь не бывает: это
      // всегда следующий партнёр. Кредит подписчицы («входит в подписку»)
      // считает сервер — Ф0.4, — и он же решает, показывать ли эту цену вообще.
      return only(const [LadderKey.pairCheck]);

    case PaywallSurface.plans:
      // Две подписанные группы ТЗ P7: «Навсегда» — двери, бандл, пара;
      // «Подписка» — одна строка. Порядок внутри «Навсегда» — от дешёвого к
      // общему: сначала то, за чем пришли, потом то, что дороже и шире.
      final keys = <LadderKey>[];
      for (final key in LadderKey.values) {
        final system = key.system;
        if (system != null && !held.unlocked.contains(system.slug)) {
          keys.add(key);
        }
      }
      if (!held.ownsArchive) keys.add(LadderKey.bundleStatic);
      keys.add(LadderKey.pairCheck);
      if (!held.hasPlan) keys.add(LadderKey.subMonthly);
      return only(keys);
  }
}
