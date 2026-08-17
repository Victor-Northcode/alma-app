import '../l10n/alma_l10n.dart';
import '../net/models.dart';

/// Ступени лестницы: всё, что вообще можно купить.
///
/// Порт `mobile/ios/Alma/Billing/LadderKey.swift`. Значения — ключи каталога,
/// один в один с `alma/billing/catalogue.py`: сервер решает, какие ступени
/// сегодня на полке и почём, клиент — как они называются и в каком порядке
/// стоят.
enum LadderKey {
  natal('natal'),
  numerology('numerology'),
  birthCard('birth-card'),
  transits('transits'),
  solarReturn('solar-return'),
  compatibility('compatibility'),
  astrocartography('astrocartography'),
  synthesis('synthesis'),

  /// Все сорок одна глава, купленные разом.
  archive('archive'),

  /// Архив по цене полки минус уже оплаченная дверь. Подстановку делает
  /// сервер и говорит о ней полем `replaces`; клиент скидку не считает
  /// никогда — иначе показанная цена и списанная разойдутся.
  archiveUpgrade('archive-upgrade'),

  weekly('weekly'),
  monthly('monthly'),
  annual('annual');

  const LadderKey(this.slug);

  final String slug;

  static LadderKey? from(String? raw) {
    for (final key in LadderKey.values) {
      if (key.slug == raw) return key;
    }
    return null;
  }

  /// Система, которую открывает ступень, или `null`, если она открывает больше
  /// одной.
  SystemSlug? get system => SystemSlug.from(slug);

  /// Спишет ли магазин ещё раз. От этого зависит, какое раскрытие стоит над
  /// кнопкой: о повторном списании человек обязан узнать до нажатия, а не из
  /// выписки.
  bool get isSubscription =>
      this == LadderKey.weekly ||
      this == LadderKey.monthly ||
      this == LadderKey.annual;

  /// Идентификатор товара в консолях магазинов.
  ///
  /// **Вычисляется, а не хранится таблицей** — то же решение, что в
  /// `StoreProvider.store_product_id` на сервере и в `LadderKey.swift`:
  /// правило одно, записано трижды и трижды закрыто тестом, а вторая таблица
  /// была бы вторым местом, которое однажды разойдётся с консолью. Правило:
  /// ключ каталога с приставкой `alma.`, дефисы заменены подчёркиваниями —
  /// дефис в идентификаторе не принимают ни App Store Connect, ни Play.
  static const prefix = 'ai.pazl.alma.';
  String get storeProductId => prefix + slug.replaceAll('-', '_');

  /// Обратное — для покупки, которая пришла из магазина, а не из нажатой
  /// кнопки. Однозначно, потому что подчёркивания нет ни в одном ключе
  /// каталога.
  static LadderKey? fromStoreProductId(String id) {
    if (!id.startsWith(prefix)) return null;
    return LadderKey.from(id.substring(prefix.length).replaceAll('_', '-'));
  }

  String title(L l) => switch (this) {
        LadderKey.archive => l.paywallArchiveTitle,
        LadderKey.archiveUpgrade => l.paywallUpgradeTitle,
        LadderKey.weekly => l.paywallWeeklyTitle,
        LadderKey.monthly => l.paywallMonthlyTitle,
        LadderKey.annual => l.paywallAnnualTitle,
        _ => systemTitle(l, system ?? SystemSlug.natal),
      };

  String note(L l) => switch (this) {
        LadderKey.archive => l.paywallArchiveNote,
        LadderKey.archiveUpgrade => l.paywallUpgradeNote,
        LadderKey.weekly => l.paywallWeeklyNote,
        LadderKey.monthly => l.paywallMonthlyNote,
        LadderKey.annual => l.paywallAnnualNote,
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

/// Зачем открыли продающий экран: это дверь, витрина под одной системой или
/// витрина целиком.
///
/// Порт `PaywallIntent`, расширенный третьим случаем 16 августа 2026.
///
/// ## Дверь и лестница — разные поверхности, и сливать их нельзя
///
/// **Записано здесь, потому что сливали их уже дважды и сольют снова.** Довод
/// каждый раз один и тот же и звучит убедительно: «раз человек всё равно
/// смотрит на цену, покажем рядом и план — вдруг возьмёт дороже». Он неверен, и
/// вот почему.
///
/// *Дверь* ([PaywallIntent.door], экран `s46`) открывается тапом по закрытой
/// главе. Человек в эту секунду занят не выбором тарифа: он потянулся к одному
/// конкретному тексту и хочет его прочесть. Работа двери — назвать цену **этой**
/// системы и открыть её одним нажатием. Всё остальное на ней — шум, который
/// превращает «купить и читать» в «сесть и разобраться», а разбираться посреди
/// чтения никто не станет: он закроет экран и уйдёт. Поэтому дверь продаёт ровно
/// одну систему, и [ladderFor] здесь не дописывает **ни одной** ступени —
/// правило живёт в этом файле, а не в разметке экрана, чтобы следующая витрина
/// не завела его заново по-своему.
///
/// *Лестница* ([PaywallIntent.everything], экран `s8`) открывается тогда, когда
/// человек сам спросил «а что тут вообще есть». Её работа прямо противоположная
/// — показать все ступени и дать сравнить. Туда с двери ведёт тихая ссылка «See
/// the plans», и это единственная законная дорога от одной к другой: выбор
/// тарифа сделан по своей воле, а не подсунут поверх чужого намерения.
///
/// *Витрина под системой* ([PaywallIntent.showcase], экран `s37`) — третья
/// роль, а не компромисс между первыми двумя: тот же перечень ступеней, но
/// возглавляемый системой, которую только что посчитали. Она показывается один
/// раз, шагом путешествия, когда числа уже на руках, а читать ещё нечего, — то
/// есть в единственную минуту, когда сравнивать тарифы человеку и правда
/// уместно.
class PaywallIntent {
  /// Дверь `s46`: одна система, одна кнопка, никакой лестницы.
  const PaywallIntent.door(SystemSlug this.system) : ladder = false;

  /// Витрина `s37`: лестница, возглавляемая одной системой.
  const PaywallIntent.showcase(SystemSlug this.system) : ladder = true;

  /// Витрина `s8`: лестница целиком.
  const PaywallIntent.everything()
      : system = null,
        ladder = true;

  final SystemSlug? system;

  /// Показывать ли что-нибудь, кроме самой двери. У двери — нет.
  final bool ladder;

  bool get isDoor => system != null;
}

/// Какие ступени показать и в каком порядке.
///
/// Порт `Storefront.offers(for:held:)`. Здесь стоит вся выстраданная логика
/// натива, и переносится она дословно:
///
/// * дверь, за которой пришли, стоит первой и выбрана заранее — продавать то,
///   к чему человек потянулся, старейший закон этой лестницы;
/// * **дверь она и есть дверь**: у [PaywallIntent.door] лестницы нет вовсе, и
///   эта функция возвращает ровно одну ступень. Довод целиком — в шапке
///   [PaywallIntent]; коротко: экран, открытый тапом по закрытой главе, продаёт
///   одну систему, и всё, что дописано к ней, отвечает на вопрос, которого
///   человек не задавал;
/// * планы идут снизу вверх — **неделя, месяц, год**, — и первой, то есть
///   предвыбранной, оказывается неделя. Это решение владельца от 16 августа
///   2026, и оно сознательно отменяет прежнее «первым идёт год, на него
///   приходится 60–70% продаж плана». Тот довод верен только для человека,
///   который платить уже решил; до этой развилки предвыбранный год работает
///   якорем-перевёртышем — он не поднимает средний чек, а переворачивает
///   вопрос с «сколько платить» на «платить ли вообще», и ровно на этом якоре
///   тонут Nebula и Pattern. Наша школа другая: маленький честный первый
///   платёж. Год никуда не убран — он продаёт свою математику последним,
///   когда неделя и месяц уже названы и с ними есть что сравнивать. Если
///   следующий читающий соберётся переставить обратно «чтобы продавалось
///   лучше» — так и стояло, и это отменили осознанно, а не по недосмотру;
/// * планы исчезают целиком у того, у кого план уже есть: смена плана — это
///   изменение внутри группы подписок на экране Apple, а не вторая покупка;
/// * архив исчезает у того, кто им владеет, и ровно одна из двух ступеней
///   архива показывается — какая, решил сервер полем `offered`.
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
  final onTheShelf = <LadderKey, Plan>{};
  for (final plan in shelf) {
    if (plan.offered != 'shelf') continue;
    final key = LadderKey.from(plan.slug);
    if (key != null) onTheShelf[key] = plan;
  }

  final keys = <LadderKey>[];
  final door = intent.system;
  if (door != null && !held.unlocked.contains(door.slug)) {
    keys.addAll(LadderKey.values.where((k) => k.system == door));
  }
  // Дверь кончается здесь, на своей единственной ступени. Отсечка стоит до
  // архива и до планов намеренно: и то и другое — «а ещё у нас есть», то есть
  // ровно тот довесок, из-за которого дверь перестаёт быть дверью.
  if (!intent.ladder) {
    return [
      for (final key in keys)
        if (onTheShelf.containsKey(key)) key,
    ];
  }
  if (!held.hasPlan && !intent.isDoor) {
    keys.addAll(const [LadderKey.weekly, LadderKey.monthly, LadderKey.annual]);
  }
  if (!held.ownsArchive) {
    for (final key in const [LadderKey.archive, LadderKey.archiveUpgrade]) {
      if (onTheShelf.containsKey(key)) {
        keys.add(key);
        break;
      }
    }
  }
  if (!held.hasPlan && intent.isDoor) {
    // Тот же порядок, что и без двери: под конкретной дверью и разовым архивом
    // лестница подписок обязана читаться одинаково — неделя, месяц, год.
    keys.addAll(const [LadderKey.weekly, LadderKey.monthly, LadderKey.annual]);
  }

  final seen = <LadderKey>{};
  return [
    for (final key in keys)
      if (onTheShelf.containsKey(key) && seen.add(key)) key,
  ];
}
