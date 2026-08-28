import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../design/arrival.dart';
import '../settings/sign_in_screen.dart';
import '../../design/art.dart';
import '../../design/metrics.dart';
import '../../design/buttons.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/nbo.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
import '../onboarding/coach_anchors.dart';
import '../../billing/ladder.dart';
import '../paywall/paywall_router.dart';
import 'reading_screen.dart';
import '../systems/writing_art.dart';
import 'today_model.dart';

/// Первая страница кабинета: сегодняшнее небо против карты рождения.
///
/// Собрана по финальному экрану доски — **s45**. Один рассказ о дне под одним
/// именем: экран когда-то говорил одно и то же небо трижды под заголовками,
/// которые обычный человек не мог разобрать, и владелец спросил, зачем средний.
/// Честным ответом было «в таком порядке мы их строили» — теперь блок один,
/// называется так, как это называют люди, и открывает его подписка: расчёты
/// бесплатны навсегда, продаётся написанное.
///
/// **Один каркас, два состояния.** До 16 августа 2026 порт был посимвольной
/// копией s1: строки лежали прямо на ночи, дата пряталась внутри фразы области,
/// медальон был диском в кольце. s45 — тот же экран, пересобранный: шапка с
/// лучевым медальоном, стеклянная панель гороскопа, стеклянная панель областей,
/// где дата вынесена вправо. Бесплатное состояние — **тот же** каркас, в
/// котором панель гороскопа несёт залоченный блок из s2. Два разных экрана
/// вместо двух состояний одного — это ровно тот способ, которым две страницы
/// расходятся молча и навсегда.
class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key});

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  TodayModel? _model;
  String? _loadedForProfile;

  /// С какими правами экран себя прочитал. `null` — ещё ни с какими.
  ///
  /// **Права — часть запроса, а не только вёрстки.** Глава дня приходит с
  /// сервера в двух разных размерах: подписчику — письмо целиком, бесплатному
  /// — 200 с `locked: true` и открывающим абзацем (`readings.py`,
  /// `_locked_chapter`). Перезагрузка стояла только на смене профиля, так что
  /// заплативший оставался с тем ответом, который сервер дал ему **до**
  /// покупки: каркас страницы менялся сразу (сессия — `InheritedNotifier`), а
  /// внутри панели по-прежнему лежала бесплатная заметка, и письма дня не было
  /// до перезапуска приложения. Худший вид молчания — то, за которое заплатили
  /// минуту назад.
  ///
  /// Признак нужен ровно потому, что `build` зовётся десятки раз: без него
  /// «права изменились» было бы неотличимо от «нас просто перестроили», и
  /// каждый кадр уходил бы в сеть.
  bool? _loadedForSubscriber;

  /// И с каким языком. Третья причина перечитать себя — той же природы, что
  /// две выше: смена языка в настройках приходила в сессию мгновенно
  /// (`InheritedNotifier`), каркас перестраивался на новом, а внутри панели
  /// оставался текст дня на старом до перезапуска. Владелец, 28.08.2026:
  /// после смены языка на экране не остаётся ни строки на старом — сервер
  /// уже написанное переводит дешёвой моделью, так что перечитать не значит
  /// заплатить за генерацию заново.
  String? _loadedForLocale;

  /// Модель со своей подпиской — **и подписка ставится только здесь**.
  ///
  /// Она висела внутри ветки перезагрузки, то есть слушатель добавлялся заново
  /// на каждую причину перечитать экран. Пока причина была одна — смена
  /// профиля, — это почти не замечалось; теперь их две, и вторая срабатывает
  /// на каждой покупке, возврате и продлении. Один слушатель на модель.
  TodayModel _watchedModel(AlmaClient client) {
    final model = TodayModel(client);
    model.addListener(() {
      if (mounted) setState(() {});
    });
    return model;
  }

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final l = L.of(context);

    // Перезагрузка по смене профиля, не по созданию экрана. На iOS это чинилось
    // как «task(id: profile.id)»: все четыре вкладки живут всю жизнь
    // приложения, и загрузка «один раз при создании» означала экран, навсегда
    // застрявший на «Читаю твою карту», если рождение ввели после запуска.
    //
    // И по смене прав — по той же причине и с тем же весом: см.
    // [_loadedForSubscriber]. Покупка, возврат и продление приходят в сессию в
    // любую секунду, а страница обязана перечитать себя, а не ждать, пока
    // человек убьёт приложение.
    final profileId = session.profile?.id;
    final subscriber = session.isSubscriber;
    if (profileId != null &&
        (profileId != _loadedForProfile ||
            subscriber != _loadedForSubscriber ||
            session.locale != _loadedForLocale)) {
      _loadedForProfile = profileId;
      _loadedForSubscriber = subscriber;
      _loadedForLocale = session.locale;
      (_model ??= _watchedModel(session.client))
          .load(locale: session.locale, subscriber: subscriber);
    }

    final model = _model;

    return ScreenScaffold(
      seed: 0x544F4441,
      eyebrow: _deviceDate(l.localeName),
      title: session.account?.displayName?.isNotEmpty == true
          ? session.account!.displayName!
          : l.tabToday,
      titleStyle: AlmaType.displayXl,
      trailing: _moonSeal(model),
      // Фаза — часть заголовочного блока, как `headerText` на нативе: она
      // стоит под именем, слева от медальона, а не под ним.
      underTitle: _moonHeaderLine(l, model),
      onRefresh: () async {
        if (model != null && session.hasBirthData) {
          await model.load(
              locale: session.locale, subscriber: session.isSubscriber);
        }
      },
      children: [
        if (session.isSubscriber) ...[
          if (model != null) ...[
            // 22 от низа шапки до панели — число s45. Раньше здесь стояло 28
            // (`gapLarge`), потому что панели не было вовсе и отбивка была
            // общей.
            const SizedBox(height: 22),
            // Ключ — якорь обучалки: панель дня и есть то, о чём говорит второй
            // шаг. Он один на оба состояния экрана, потому что панель одна:
            // подписка меняет то, что внутри, а не форму страницы.
            _HoroscopePanel(
                key: CoachAnchors.todayPanel, model: model, subscriber: true),
            // Области — вторая панель, и только подписчику: под замком
            // гороскоп целиком, а не его первый абзац.
            const SizedBox(height: 14),
            _AreasPanel(model: model),
          ],
        ] else
          // Бесплатному — те же секции, но их порядок решает NBO (§4).
          ..._freeSections(session, model),
        // **Карточка «сохрани карту» — гостю, которому есть что терять.**
        //
        // Четыре условия, и каждое обязательно: не вошёл, карта уже есть, не
        // отказывался раньше и это **не первый запуск** — первый принадлежит
        // продукту, а не просьбе зарегистрироваться. Отказ помнится в
        // настройках телефона, а не на сервере: это предпочтение «спрашивать
        // ли меня», а не состояние аккаунта, и свежая установка честно
        // является новым поводом спросить.
        if (session.account?.isGuest == true && session.hasBirthData) ...[
          const SizedBox(height: _sectionGap),
          const _SaveAccountCard(),
          // Кнопки «Sign in / Not now» стояли в зоне растворения бара и читались
          // «за баром» (снято на устройстве 22 авг). Добор воздуха — только под
          // этой карточкой: глобальный отступ каркаса трогать нельзя, он уже
          // выверен против дёрганья коротких страниц (см. screen_scaffold).
          const SizedBox(height: 12),
        ],
      ],
    );
  }

  /// Секции бесплатного «Сегодня» в порядке NBO (§4 ТЗ).
  ///
  /// **Порядок решает [nboOrder], а не вёрстка.** У каждой секции есть
  /// карточка-представитель из матрицы §4: панель гороскопа — карточка
  /// «гороскоп дня»; приглашение к плану продаёт живой слой, и его в матрице
  /// представляет соляр — единственная карточка NBO, которая живёт только в
  /// подписке. Карточки пары на этом экране пока нет — когда её построят
  /// (W1), она встанет сюда одной строкой `NboCard.compatibility`, и порядок
  /// ей уже посчитан.
  ///
  /// Секция, чьей карточки в сегодняшнем порядке нет, идёт после названных, в
  /// порядке объявления: NBO упорядочивает, но не выключает — выключает
  /// только `ownsEverything`, а с ним человек не бесплатный.
  ///
  /// **План, сказанный словами, тому, у кого его нет, — остаётся здесь же.**
  /// Он был доступен с лестницы, открывавшейся только тапом в закрытую главу,
  /// — и владелец прошёл собственный продукт из конца в конец, ни разу не
  /// увидев, что подписка вообще предлагается. На ночи, а не в стекле — так
  /// это нарисовано в s2: панель на этом экране принадлежит гороскопу, и
  /// приглашение, одетое в такую же, читалось бы вторым гороскопом.
  List<Widget> _freeSections(AlmaSession session, TodayModel? model) {
    final sections = <(NboCard, Widget)>[
      if (model != null)
        (
          NboCard.horoscope,
          _HoroscopePanel(
              key: CoachAnchors.todayPanel, model: model, subscriber: false)
        ),
      (NboCard.solar, const _PlanInvitation()),
    ];
    final order = nboOrder(todaySignals(session));
    // Слияние руками, а не `sort`: у `List.sort` нет гарантии стабильности, а
    // две секции с ненайденной карточкой обязаны сохранить объявленный
    // порядок.
    final placed = <Widget>[
      for (final card in order)
        ...[
          for (final (own, section) in sections)
            if (own == card) section,
        ],
      for (final (own, section) in sections)
        if (!order.contains(own)) section,
    ];
    return [
      for (final (index, section) in placed.indexed) ...[
        // 22 от низа шапки до первой секции — число s45; дальше — отбивка
        // разделов бесплатного экрана (довод у [_sectionGap]).
        SizedBox(height: index == 0 ? 22 : _sectionGap),
        section,
      ],
    ];
  }

  /// **Календарный день устройства, не начало серверного окна.** Скан
  /// выполняется для «сейчас» в UTC, и всякий, кто достаточно восточнее
  /// Гринвича, видел вчерашнюю дату на экране с названием «Сегодня» — каждый
  /// вечер. Мелкая неправда рядом с крупными обещаниями делает и их менее
  /// заслуживающими доверия.
  String _deviceDate(String locale) =>
      DateFormat.MMMMd(locale).format(DateTime.now());

  /// Строка фазы для заголовочного блока, или `null`, когда фазы ещё нет.
  Widget? _moonHeaderLine(L l, TodayModel? model) {
    if (model == null) return null;
    final line = _moonLine(l, model);
    if (line == null) return null;
    return Row(children: [
      // Глиф засечным и 19-м кеглем — на доске это `400 19px Playfair`, а не
      // строка обычного текста.
      Text('☽',
          style: AlmaType.displayL
              .copyWith(fontSize: 19, color: AlmaPalette.goldBright)),
      const SizedBox(width: 8),
      // Гибкой: строка стоит в колонке шириной с экран минус медальон, и на
      // языке с длинным именем фазы негибкий текст выдавал бы жёлто-чёрную
      // ленту переполнения вместо переноса. Поймано замером на 402 точках.
      Flexible(
        child: Text(line, style: AlmaType.meta.copyWith(color: AlmaPalette.muted2)),
      ),
    ]);
  }

  String? _moonLine(L l, TodayModel model) {
    final moon = model.moonPhase;
    if (moon == null) return null;
    final name = _phaseName(l, moon['phase'] as String? ?? '');
    final lit = ((moon['illumination'] as num?)?.toDouble() ?? 0) * 100;
    return '$name · ${lit.round()} %';
  }

  String _phaseName(L l, String phase) => switch (phase) {
        'new moon' => l.cabPhaseNewMoon,
        'waxing crescent' => l.cabPhaseWaxingCrescent,
        'first quarter' => l.cabPhaseFirstQuarter,
        'waxing gibbous' => l.cabPhaseWaxingGibbous,
        'full moon' => l.cabPhaseFullMoon,
        'waning gibbous' => l.cabPhaseWaningGibbous,
        'last quarter' => l.cabPhaseLastQuarter,
        'waning crescent' => l.cabPhaseWaningCrescent,
        _ => phase,
      };

  /// Печать дня: настоящая сегодняшняя луна в углу заголовка. Причина открыть
  /// этот экран нарисована в его углу — каждое утро новая.
  Widget? _moonSeal(TodayModel? model) {
    if (model == null) return null;
    final moon = model.moonPhase;
    if (moon == null) return null;
    return Padding(
      // 18 сверху — s45; в s1 было 26, и медальон там на 18 точек меньше.
      padding: const EdgeInsets.only(top: 18),
      child: _MoonMedallion(
        illumination: ((moon['illumination'] as num?)?.toDouble() ?? 0),
        waxing: moon['waxing'] as bool? ?? true,
      ),
    );
  }
}

/// Сигналы NBO (§4 ТЗ), собранные из сессии, — единственное место сборки.
///
/// Отдельной функцией намеренно: сигналы приезжают в модель клиента по одному
/// и в разное время, и каждый подключается здесь одной строкой — не трогая ни
/// одного вызова порядка.
NboSignals todaySignals(AlmaSession session) {
  final rights = session.entitlements;
  return NboSignals(
    // Ответ квиза V0 — из профиля владельца: сервер пишет его только туда,
    // и матрица §4 начинает работать с первого экрана после анкеты. Пусто —
    // человек прошёл анкету до появления вопроса или пропустил его, и порядок
    // честно живёт на универсальной ветке: натал первым.
    interest:
        session.people.where((person) => person.isSelf).firstOrNull?.interest,
    // Пол — тоже ответ квиза, и в клиентской модели его нет по той же
    // причине. Тай-брейкер молчит, а не выдумывается.
    femaleReader: false,
    // TODO(nbo): `ReadingTally` хранит счётчики открытий без времени
    // (`reading.opens.<slug>` — целое на систему), и окно «глава про любовь
    // прочитана за 72 часа» посчитать не из чего. Честное значение — false:
    // модификатор молчит, пока у чтений не появится время; его правильное
    // место — сервер, см. TODO(server) в reading_tally.dart.
    loveChapterReadRecently: false,
    // «Бесплатные главы в ≥3 системах» продукт синхронно не знает: счётчики
    // ReadingTally асинхронные и считают все открытия, а не бесплатные. Ноль
    // — карточка бандла не выдумывается по кривому приближению.
    freeChaptersReadSystems: 0,
    ownsBundle: rights.ownsArchive,
    subscriber: session.isSubscriber,
    // «Всё куплено» здесь значит: подписка держит всё либо все системы
    // открыты правами. Оба факта — слово сервера, а не догадка клиента.
    ownsEverything:
        session.isSubscriber || SystemSlug.values.every(rights.opened),
  );
}

/* ── стекло ─────────────────────────────────────────────────────────────── */

/// Отбивка между разделами бесплатного экрана.
///
/// **Тридцать, а не сорок четыре, и это не вкус.** С `gapSection` бесплатное
/// «Сегодня» переваливало за нижнюю кромку на 33 точки — измерено на
/// симуляторе смахом: страница уезжала ровно на столько и возвращалась,
/// «дёргалась», хотя листать на ней нечего. Тридцать — число самого макета
/// (s2, отбивка перед «Everything open, every day»); второй раздел получает
/// его же, потому что 38 точек, которые в макете занимает пилюля между ними, у
/// нас живут в накладке над экраном, а не в потоке.
///
/// Кегль при этом не тронут: тело текста в этом продукте не ужимается никогда.
const _sectionGap = 30.0;

/// Верхний тон стеклянной панели.
///
/// **Числа держатся здесь, а не в `palette.dart`, потому что стекло пока живёт
/// на одном экране.** Тон 0x10131F в палитре продукта не назван — он пришёл с
/// доски вместе с панелями (s45, s46). Когда стекло выйдет за «Сегодня», ему
/// место в палитре; до тех пор именованный токен обещал бы общность, которой
/// ещё нет.
const _panelTop = Color(0xFF10131F);

/// Стеклянная панель s45: градиент ночи, золотой кант, радиус 20.
///
/// Панель — не карточка: она не отделяет содержимое от экрана, а собирает его в
/// одно тело, за которым видно то же небо, только размытое. Отсюда и размытие
/// подложки: без него панель читается плашкой, положенной поверх звёзд, а не
/// стеклом, лежащим в них.
///
/// Вторая панель (области) на доске **без** размытия и с более слабыми
/// градиентом и кантом — так две панели не спорят за одно и то же внимание.
class _GlassPanel extends StatelessWidget {
  const _GlassPanel({
    required this.child,
    required this.padding,
    this.topAlpha = 0.72,
    this.bottomAlpha = 0.55,
    this.borderAlpha = 0.28,
    this.blur = true,
  });

  final Widget child;
  final EdgeInsets padding;
  final double topAlpha;
  final double bottomAlpha;
  final double borderAlpha;
  final bool blur;

  static final _radius = BorderRadius.circular(20);

  @override
  Widget build(BuildContext context) {
    final panel = Container(
      padding: padding,
      decoration: BoxDecoration(
        borderRadius: _radius,
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            _panelTop.withValues(alpha: topAlpha),
            AlmaPalette.night850.withValues(alpha: bottomAlpha),
          ],
        ),
        border: Border.all(color: AlmaPalette.gold.withValues(alpha: borderAlpha)),
      ),
      child: child,
    );
    if (!blur) return panel;
    // `blur(10px)` в CSS — гауссиана со стандартным отклонением в половину
    // радиуса, отсюда 5.
    return ClipRRect(
      borderRadius: _radius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
        child: panel,
      ),
    );
  }
}

/// Подпись раздела **внутри** панели: надзаголовок и линия до правого канта.
///
/// Не `SectionLabel`: тот отдаёт подписи 30.5 % ширины, потому что на голой
/// странице «ГОРОСКОП НА СЕГОДНЯ» переносится ровно так же, как на нативном
/// кадре. Внутри панели доска переноса не делает — подпись стоит строкой, линия
/// забирает остаток, — и втиснутая в треть панели она встала бы в две строки
/// там, где в эталоне одна. Запас в 28 точек оставлен линии: он и есть то
/// «сжимайся, но не исчезай», которое в вёрстке делает `flex`.
class _PanelLabel extends StatelessWidget {
  const _PanelLabel(this.text, {this.badge});

  final String text;

  /// Тихая метка сразу за подписью — бейдж `subscribed` из W5. Не в хвосте
  /// строки: у правого канта стоит время чтения, и две метки рядом читались
  /// бы одной.
  final Widget? badge;

  /// Во сколько раз подпись важнее линии при дележе свободного места.
  ///
  /// **Вся починка в этом числе, и раньше оно было единицей.** Подпись стояла
  /// `Flexible` (вес 1) рядом с `Expanded`-линией (вес 1), то есть два гибких
  /// ребёнка с равными правами: подписи доставалась ровно половина свободного
  /// места, сколько бы ей ни было нужно. На «YOUR HOROSCOPE TODAY» рядом с
  /// бейджем половины не хватало даже на одно слово целиком, и перенос уходил
  /// **внутрь** слова — «YOUR HOR / OSCOPE / TODAY», на первом же экране,
  /// который видит человек.
  ///
  /// Гибкой подпись при этом обязана остаться: на 402 точках места для неё в
  /// одну строку вместе с бейджем и временем чтения нет вовсе, и негибкая дала
  /// бы полосу переполнения вместо переноса — ровно то, о чём предупреждал
  /// прежний комментарий на этом месте. Значит вопрос не «гибкая или нет», а
  /// «кто уступает первым», и уступать обязана декоративная линия: пять к
  /// одному оставляют подписи заведомо больше её самого длинного слова, то есть
  /// перенос — только между словами.
  static const int _labelWeight = 5;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) => Row(
        children: [
          Flexible(
            flex: _labelWeight,
            child: ConstrainedBox(
              constraints:
                  BoxConstraints(maxWidth: math.max(0, box.maxWidth - 40)),
              child: Text(text.toUpperCase(), style: AlmaType.overline),
            ),
          ),
          if (badge != null) ...[
            const SizedBox(width: 10),
            badge!,
          ],
          const SizedBox(width: 12),
          Expanded(
            child: Container(
              height: 1,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    const Color(0x00000000),
                    AlmaPalette.gold.withValues(alpha: 0.4),
                    const Color(0x00000000),
                  ],
                ),
              ),
            ),
          ),
          // «3 мин» у правого канта снято владельцем (29.08.2026): время
          // чтения на карточке — «какая-то бессмысленная тема». Линия теперь
          // доходит до правого канта сама.
        ],
      ),
    );
  }
}

/* ── гороскоп ───────────────────────────────────────────────────────────── */

/// «Гороскоп на сегодня» — блок дня в стеклянной панели.
///
/// **Только подписчикам, по решению владельца**: не первый абзац, не проба.
/// Разовая покупка его тоже не открывает — ни блюра, ни пустой карточки. Одна
/// фраза о том, что это такое и где живёт, и дверь. Панель при этом остаётся
/// той же самой: подписка меняет то, что внутри, а не форму экрана.
class _HoroscopePanel extends StatefulWidget {
  const _HoroscopePanel(
      {super.key, required this.model, required this.subscriber});

  final TodayModel model;
  final bool subscriber;

  @override
  State<_HoroscopePanel> createState() => _HoroscopePanelState();
}

class _HoroscopePanelState extends State<_HoroscopePanel> {
  /// Развёрнут ли бесплатный абзац дня. По брендбуку гороскоп — вкладочка:
  /// свёрнут в несколько строк, тап разворачивает (владелец, 22 авг). Живёт на
  /// панели, а не глубже: состояние показа, не содержания.
  bool _expanded = false;

  TodayModel get model => widget.model;
  bool get subscriber => widget.subscriber;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return _GlassPanel(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PanelLabel(
            l.cabHoroscopeToday,
            // Тихая метка W5: подписчику всё открыто, и бейдж отвечает на
            // «почему» — не продаёт. Не золотая кнопка, а подпись.
            badge: subscriber ? const _SubscribedBadge() : null,
          ),
          if (subscriber) ..._voice(l) else ..._free(context, l),
        ],
      ),
    );
  }

  /// Бесплатное состояние — кадр W4: написанный абзац дня, а под ним закрытый
  /// живой слой.
  ///
  /// Абзац — `opening` закрытого ответа: сорок слов, написанных из настоящих
  /// позиций до покупки; это доказательство «текст про тебя», которого у
  /// стены не было. Пустой `opening` — законный ответ (потолок месяца выбран,
  /// модель промолчала), и тогда панель остаётся прежним замком из s2:
  /// честная строка и дверь, без ретрая и без филлера. Живой слой в этом
  /// случае тоже не рисуется: три двери без единого написанного слова — та
  /// самая стена, от которой W4 уходит.
  List<Widget> _free(BuildContext context, L l) {
    switch (model.line) {
      case LoadRunning():
        // Заготовки строк — как у подписчика, только короче: опенинг — один
        // абзац, и блики на пол-экрана обещали бы письмо целиком.
        return const [
          SizedBox(height: 20),
          WaitingBar(height: 15),
          SizedBox(height: 13),
          WaitingBar(
            height: 15,
            widthFactor: 0.62,
            delay: Duration(milliseconds: 150),
          ),
        ];
      case LoadDone<ReadingResponse>(value: final answer):
        // Опенинг — только у закрытого ответа. Открытая глава у человека без
        // плана — гонка прав между кадрами; показывать её здесь значило бы
        // раздать письмо даром, поэтому падение в тот же честный замок.
        final opening = answer.locked ? answer.opening : null;
        final paragraphs = opening?.body
                .where((paragraph) => paragraph.trim().isNotEmpty)
                .toList() ??
            const <String>[];
        if (paragraphs.isEmpty) return _locked(context, l);
        return [
          const SizedBox(height: 14),
          // **Вкладочка, а не простыня.** Абзац дня лежал развёрнутым целиком, и
          // владелец сверил с брендбуком: гороскоп — карточка, «нажимаешь — и он
          // разворачивается» (22 авг). Свёрнуто — четыре строки с растворением
          // (той же гаснущей строкой, что у подписчика); тап по тексту или по
          // шеврону раскрывает и сворачивает. AnimatedSize ведёт высоту плавно.
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () {
              HapticFeedback.selectionClick();
              setState(() => _expanded = !_expanded);
            },
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AnimatedSize(
                  duration: AlmaMotion.ui,
                  curve: AlmaMotion.uiCurve,
                  alignment: Alignment.topCenter,
                  child: Text(
                    paragraphs.join('\n\n'),
                    style: AlmaType.readingBody(),
                    maxLines: _expanded ? null : 4,
                    overflow:
                        _expanded ? TextOverflow.visible : TextOverflow.fade,
                  ),
                ),
                const SizedBox(height: 6),
                Align(
                  alignment: Alignment.center,
                  child: AnimatedRotation(
                    turns: _expanded ? 0.5 : 0,
                    duration: AlmaMotion.ui,
                    curve: AlmaMotion.uiCurve,
                    child: Icon(
                      Icons.expand_more,
                      size: 22,
                      color: AlmaPalette.gold.withValues(alpha: 0.8),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          _LivingLayer(model: model),
        ];
      case LoadFailed<ReadingResponse>():
        // Отказ сети — не повод выдумывать заметку: прежний замок честен и
        // работает без сервера.
        return _locked(context, l);
      case _:
        return _locked(context, l);
    }
  }

  /// Залоченное состояние — блок из s2, целиком: строка о том, что это такое и
  /// когда приходит, и строка-дверь. Ни блюра поверх настоящего текста, ни
  /// пустой карточки: показывать размытым то, за что просят денег, — это
  /// обещание, которого продукт не давал. Осталось запасным путём W4: сюда
  /// панель падает, когда опенинг не написан.
  List<Widget> _locked(BuildContext context, L l) => [
        const SizedBox(height: 20),
        Text(l.cabHoroscopeLocked, style: AlmaType.body),
        const SizedBox(height: 6),
        AlmaActionRow(
          label: l.cabHoroscopeOpen,
          onTap: () => openSubscription(context),
        ),
      ];

  List<Widget> _voice(L l) {
    switch (model.line) {
      case LoadRunning():
        // **Ожидание — это страница, а не строка.** Здесь стояли неподвижная
        // точка и подпись «читаю твою карту» над пустотой, и полминуты это
        // выглядело сломанным экраном. В макете (s27) на месте будущего текста
        // лежат заготовки строк, по которым идёт блик: человек видит, сколько
        // текста придёт и куда он ляжет, ещё до первого слова. Заготовки лежат
        // **в той же панели**, в которой встанет текст, — иначе страница
        // прыгнет в момент, когда он придёт.
        //
        // Числа макета: отбивка 24 сверху и 18 снизу у строки присутствия,
        // строки высотой 15 через 13, ширины 100/94/62 %, блик 1.9 с линейно
        // со сдвигом 0.15 с на строку.
        return [
          Padding(
            padding: const EdgeInsets.only(top: 24, bottom: 18),
            child: Row(children: [
              const WaitingDot(size: 24),
              const SizedBox(width: 12),
              Text(l.cabReadingChart, style: AlmaType.meta),
            ]),
          ),
          const WaitingBar(height: 15),
          const SizedBox(height: 13),
          const WaitingBar(
            height: 15,
            widthFactor: 0.94,
            delay: Duration(milliseconds: 150),
          ),
          const SizedBox(height: 13),
          const WaitingBar(
            height: 15,
            widthFactor: 0.62,
            delay: Duration(milliseconds: 300),
          ),
        ];
      case LoadDone<ReadingResponse>(value: final answer):
        // **Здесь стоял весь текст целиком, и это была ошибка размером в
        // экран.** Гороскоп подписчика — две тысячи знаков и больше; вылитый
        // сюда дисплейной антиквой, он давал два экрана прокрутки, полоса
        // вкладок наезжала на строки, а блок областей уходил за сгиб.
        //
        // `today-reading-spec §2` разводит это на два места: на «Сегодня»
        // остаётся лид одной фразой, **один** абзац и дверь; весь текст живёт
        // в читалке. Правило там сформулировано без исключений: «Полный текст
        // на Today не выводится никогда».
        //
        // Лид — `teaser` сервера, а не первая фраза, отрезанная клиентом:
        // схема просит у модели «одну фразу, называющую, что глава нашла»,
        // и это ровно лид. Резать текст на клиенте спека запрещает отдельно.
        final reading = answer.reading;
        // **Закрытую главу карточка дня не показывает вовсе.** Ответ на главу
        // теперь один на оба случая: у закрытой `reading` пуст, а вместо неё
        // приезжает `opening` — сорок слов, написанных до покупки. Подписчику
        // этого не приходит, но право может истечь между кадрами, и напечатать
        // открывающий абзац как письмо дня значило бы выдать пробу за
        // купленное. Карточка остаётся в своём непрочитанном виде.
        if (reading == null) return const <Widget>[];
        final first = reading.body.isEmpty ? null : reading.body.first;
        return [
          if (reading.teaser.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(reading.teaser, style: AlmaType.readingLead),
          ],
          if (first != null) ...[
            const SizedBox(height: 12),
            // **Четыре строки, дальше — растворение.**
            //
            // Спека требует двух вещей сразу: «один абзац» и «экран обязан
            // заканчиваться до бара без скролла». У сервера абзац дня — шесть
            // сотен знаков, и обе разом не выполняются: один такой абзац сам по
            // себе длиннее экрана.
            //
            // Растворение — решение показа, а не содержания: текст не режется
            // на части (это спека запрещает клиенту прямо) и не переписывается,
            // просто карточка показывает его начало, а дверь под ней стоит в
            // одном касании. Многоточие на этом месте читалось бы обрывом, а
            // гаснущая строка — приглашением.
            //
            // **Правильное место починки — движок.** Спека писалась под
            // короткий открывающий абзац; пока его нет, честнее гасить, чем
            // ломать раскладку. Записано владельцу.
            Text(
              first,
              style: AlmaType.readingBody(),
              maxLines: 4,
              overflow: TextOverflow.fade,
            ),
          ],
          const SizedBox(height: 16),
          _WholeSkyDoor(reading: reading),
        ];
      case LoadFailed<ReadingResponse>(error: final error):
        return [
          Padding(
            padding: const EdgeInsets.only(top: 14),
            child: Text(
              error is ServerRefused && error.message.isNotEmpty
                  ? error.message
                  : l.stateUnavailable,
              style: AlmaType.meta,
            ),
          ),
        ];
      case _:
        return const [];
    }
  }
}

/// Дверь в читалку: контур высотой 50 под абзацем (`today-reading-spec §2`).
///
/// Не `AlmaActionRow` со стрелкой в строке: у двери на карточке гороскопа есть
/// заданная высота, и она — единственное на этом экране, что человек нажимает,
/// чтобы продолжить чтение. Строка-ссылка на её месте читалась бы сноской.
class _WholeSkyDoor extends StatelessWidget {
  const _WholeSkyDoor({required this.reading});

  final Reading reading;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return SizedBox(
      height: 50,
      width: double.infinity,
      child: OutlinedButton(
        onPressed: () => Navigator.of(context).push(
          CupertinoPageRoute(
            builder: (_) => TodayReadingScreen(
              reading: reading,
              // Гороскоп пишется на сегодня по определению: ручка зовётся
              // `transits/active`, и другого дня у неё не бывает.
              day: DateTime.now(),
            ),
          ),
        ),
        style: OutlinedButton.styleFrom(
          side: BorderSide(color: AlmaPalette.hairlineGold),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AlmaPalette.buttonRadius),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(l.todayReadWholeSky,
                style: AlmaType.body.copyWith(color: AlmaPalette.gold)),
            const SizedBox(width: 8),
            const Icon(Icons.arrow_forward, size: 15, color: AlmaPalette.gold),
          ],
        ),
      ),
    );
  }
}

/* ── живой слой ─────────────────────────────────────────────────────────── */

/// Тихая метка подписчика — бейдж `subscribed` из W5: Golos 600 9.5,
/// разрядка 1.3, прописные, кант золота на 0.4, радиус 4, паддинг 3 × 7.
///
/// Не кнопка и не зов: внутри оплаченного коммерции ноль (правило 3 спеки), и
/// метка лишь отвечает на вопрос «почему всё открыто».
class _SubscribedBadge extends StatelessWidget {
  const _SubscribedBadge();

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(4),
        // Прозрачность — число кадра W5. В палитре такой ступени нет, и
        // тянуться к hairlineGold (0.16) нельзя: кант вдвое тише нарисованного
        // — то самое незаметное расхождение (довод в §1 SCREENS-V3).
        border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.4)),
      ),
      child: Text(
        l.paywallV3SubBadge.toUpperCase(),
        style: AlmaType.overline
            .copyWith(fontSize: 9.5, letterSpacing: 1.3, height: 1),
      ),
    );
  }
}

/// Три закрытых блока живого слоя — кадр W4: транзиты · соляр · глубина дня.
///
/// **Замка нет — стоит `✦`.** Решение холста, и оно продуктовое: замок
/// говорит «тебе нельзя», звёздочка — «тут есть ещё». Продаётся написанное, а
/// не доступ, и иконография обязана это повторять. Тап по любому блоку —
/// пейволл подписки (P5): живое продаётся из живого, дверей у этих систем в
/// v3 нет.
///
/// Цены на блоках нет ни одной — она живёт на V6, куда ведёт тап (правило
/// кадра «чего на экране быть не должно»).
class _LivingLayer extends StatelessWidget {
  const _LivingLayer({required this.model});

  final TodayModel model;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _LivingLayerLabel(),
        // Отбивки кадра: 10 до первого блока, 11 между следующими.
        const SizedBox(height: 10),
        _LiveBlock(
          image: AlmaArt.card(SystemSlug.transits),
          title: l.liveTransitsTitle,
          note: _transitsNote(l),
        ),
        const SizedBox(height: 11),
        _LiveBlock(
          image: AlmaArt.card(SystemSlug.solarReturn),
          title: l.liveSolarTitle,
          note: l.liveSolarNote,
        ),
        const SizedBox(height: 11),
        // «День целиком» — не система, а глубина дня; у него нет своей карты
        // в колоде. Стояла вклейка V6 (`plate-sky`) — на ней лицо, и с
        // 29.08.2026 лица убраны отовсюду, кроме совместимости; до новых
        // картин блок держит ту же туманность, что и соседние два.
        _LiveBlock(
          image: AlmaArt.sky,
          title: l.liveDayTitle,
          note: l.liveDayNote,
        ),
      ],
    );
  }

  /// Подпись транзитов несёт живое число из расчёта — не из словаря (W4).
  ///
  /// Небо ещё не пришло или неделя тихая — строка без числа: выдумывать «три
  /// точных аспекта» нельзя ровно на том экране, который держится на правде о
  /// сегодняшнем небе.
  String _transitsNote(L l) {
    final count = model.exactUntilSunday;
    if (count == null || count == 0) return l.liveTransitsNoteQuiet;
    return l.liveTransitsNote(count);
  }
}

/// Строка раздела W4: оверлайн `the living layer` и линия, гаснущая вправо.
///
/// Не `_PanelLabel`: у того кегль 11.5 с разрядкой 2.5 и линия до правого
/// канта с местом под хвост; здесь числа кадра — 11/2.2 золотом на 0.85 и
/// линия в одну сторону.
class _LivingLayerLabel extends StatelessWidget {
  const _LivingLayerLabel();

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Row(children: [
      Text(
        l.homeLivingLayer.toUpperCase(),
        style: AlmaType.readingPart
            .copyWith(color: AlmaPalette.gold.withValues(alpha: 0.85)),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Container(
          height: 1,
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [
              AlmaPalette.gold.withValues(alpha: 0.3),
              const Color(0x00000000),
            ]),
          ),
        ),
      ),
    ]);
  }
}

/// Один закрытый блок живого слоя: фото под блюром, скрим, `✦`, заголовок и
/// подпись. Числа — кадр W4: высота 112, радиус 16, кант золота на 0.22.
class _LiveBlock extends StatelessWidget {
  const _LiveBlock({
    required this.image,
    required this.title,
    required this.note,
  });

  final String image;
  final String title;
  final String note;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: title,
      child: GestureDetector(
        onTap: () => openSubscription(context),
        behavior: HitTestBehavior.opaque,
        child: Container(
          height: 112,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border:
                Border.all(color: AlmaPalette.gold.withValues(alpha: 0.22)),
          ),
          // Граница перерисовки: гаусс по фотографии — работа растеризатора,
          // а блок статичен; без границы прокрутка «Сегодня» пересчитывала бы
          // все три размытия на каждом кадре, с ней — один раз на блок.
          child: RepaintBoundary(
              child: ClipRRect(
            // Радиус картины на толщину канта меньше рамы — иначе угол
            // картинки вылезает из-под золота светлой ниткой (как у вклеек).
            borderRadius: BorderRadius.circular(15),
            child: Stack(fit: StackFit.expand, children: [
              // Блюр 3 px холста — сигма 1.5, по той же арифметике
              // CSS→Flutter, что у стекла панели (`blur(10px)` → 5). Ровно
              // столько, чтобы картинка читалась содержимым, а не заглушкой.
              ImageFiltered(
                imageFilter: ImageFilter.blur(sigmaX: 1.5, sigmaY: 1.5),
                child: Opacity(
                  opacity: 0.5,
                  child: Image.asset(
                    image,
                    fit: BoxFit.cover,
                    // `object-position: center 34%` кадра.
                    alignment: const Alignment(0, -0.32),
                  ),
                ),
              ),
              // Скрим кадра: ночь-900 от .55 к .8 — без него подпись не
              // читается ни на одной фотографии.
              DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      AlmaPalette.night900.withValues(alpha: 0.55),
                      AlmaPalette.night900.withValues(alpha: 0.8),
                    ],
                  ),
                ),
              ),
              Positioned(
                left: 16,
                right: 16,
                top: 0,
                bottom: 0,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      // ✦ — настроение блока: не замок. Golos 13 золотом.
                      Text('✦',
                          style: AlmaType.meta.copyWith(
                              fontSize: 13, color: AlmaPalette.gold)),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Text(
                          title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: AlmaType.headingM.copyWith(
                            fontSize: 18,
                            height: 1.2,
                            color:
                                AlmaPalette.inkLight.withValues(alpha: 0.9),
                          ),
                        ),
                      ),
                    ]),
                    const SizedBox(height: 4),
                    Text(
                      note,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: AlmaType.meta
                          .copyWith(fontSize: 12.5, color: AlmaPalette.muted3),
                    ),
                  ],
                ),
              ),
            ]),
          )),
        ),
      ),
    );
  }
}

/* ── области ────────────────────────────────────────────────────────────── */

/// Четыре области жизни, у каждой ближайший контакт — или честное «здесь
/// сегодня тихо».
///
/// Пустая область, заполненная чем-нибудь, была бы ровно тем провалом, ради
/// избегания которого экран существует: это строка, которую не может написать
/// ни один гороскоп по знаку Солнца.
///
/// **Дата вынесена из предложения на правый край панели.** В s1 она стояла
/// внутри фразы — «Сатурн сейчас соединяется с твоей Серединой неба, 18
/// августа», — и четыре такие строки читались одним слипшимся абзацем. На s45
/// строка отвечает «что», а колонка справа — «когда», и глаз берёт даты
/// столбцом, не перечитывая фразы.
class _AreasPanel extends StatelessWidget {
  const _AreasPanel({required this.model});

  final TodayModel model;

  /// Порядок серверный, зеркалится здесь, чтобы двое молча не разошлись в том,
  /// что идёт первым.
  static const _order = ['work', 'love', 'money', 'body'];

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final rows = _rows(l);
    if (rows.isEmpty) return const SizedBox.shrink();
    return _GlassPanel(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      topAlpha: 0.6,
      bottomAlpha: 0.45,
      borderAlpha: 0.2,
      blur: false,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: rows),
    );
  }

  List<Widget> _rows(L l) {
    final sky = model.sky;
    // Пока небо считается, области стоят заготовками — по макету s27: золотая
    // метка 52×11 и строка под ней, 12 между ними и 22 между группами.
    // Заготовка ничего не обещает про содержание: она держит место, чтобы
    // страница не прыгнула, когда придут настоящие строки.
    if (sky is LoadRunning<CalcResult>) {
      return [
        for (var i = 0; i < 4; i++)
          Padding(
            padding: EdgeInsets.only(top: i == 0 ? 0 : 22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                WaitingBar(
                  height: 11,
                  width: 52,
                  tone: WaitingTone.gold,
                  delay: Duration(milliseconds: 450 + i * 300),
                ),
                const SizedBox(height: 12),
                WaitingBar(
                  height: 13,
                  widthFactor: i.isEven ? 0.84 : 0.70,
                  delay: Duration(milliseconds: 600 + i * 300),
                ),
              ],
            ),
          ),
      ];
    }
    if (sky is! LoadDone<CalcResult>) return const [];

    final rows = <Widget>[];
    for (final area in _order) {
      final hit = model.nearest(area);
      if (rows.isNotEmpty) {
        rows.add(const SizedBox(height: 12));
        rows.add(Container(
          height: 1,
          color: AlmaPalette.body.withValues(alpha: 0.08),
        ));
        rows.add(const SizedBox(height: 12));
      }
      rows.add(_AreaRow(area: area, hit: hit, written: model.areaLine(area)));
    }
    return rows;
  }
}

/// Одна область: имя слева, дата справа, фраза под ними.
class _AreaRow extends StatelessWidget {
  const _AreaRow({required this.area, required this.hit, this.written});

  final String area;

  /// Что об этой области написано словами. `null` — не писал никто.
  ///
  /// **Здесь никогда не было ни одного промта, и это было видно.** Строка
  /// собиралась шаблоном прямо из расчёта — «{планета} {аспект} your {натал}»,
  /// — и под заголовком «Работа» стояло «Chiron conjunct your Midheaven»:
  /// правда про небо и ничего про работу. Владелец: «как будто ты забыл туда
  /// промты добавить… он вообще не по теме».
  ///
  /// Теперь четыре строки пишет модель, в том же вызове, которым пишется
  /// дневной текст (`Chapter.areas`). Шаблон остался запасным путём: главы,
  /// написанные до этой правки, лежат в кэше сервера без нового поля, и
  /// вернуться к факту честнее, чем показать пустоту.
  final String? written;

  /// Ближайший контакт или `null` — «здесь сегодня тихо».
  final Map<String, dynamic>? hit;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final quiet = hit == null;
    // Колонка дат справа снята владельцем (29.08.2026): «есть дата … в
    // нижнем блоке — эта дата не нужна». Экран называется «Сегодня», и любое
    // число справа читалось обещанием события на дату — сначала его резали
    // тридцатидневным горизонтом (правило 22.08, «Jun 13 в августе — не про
    // сегодня»), теперь дата снята целиком. Фраза области осталась той же;
    // точные даты живут в «Транзитах», где им место.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          CabinetWords.area(l, area),
          style: AlmaType.meta.copyWith(
            // Тихая область не золотится: у неё нечего подсвечивать, и
            // ряд золотых меток над «здесь сегодня тихо» обещал бы
            // четыре события там, где их два.
            color: quiet
                ? AlmaPalette.body.withValues(alpha: 0.6)
                : AlmaPalette.goldBright,
            fontWeight: FontWeight.w500,
            // Вес вариативному шрифту задаётся осью: один `fontWeight`
            // выбирает ближайший **объявленный** инстанс, а объявлен один,
            // и метка молча оставалась тонкой. См. `typography.dart`.
            fontVariations: const [FontVariation('wght', 500)],
          ),
        ),
        const SizedBox(height: 4),
        Text(
          quiet ? l.cabAreaQuiet : (written ?? '${_phrase(l, hit!)}.'),
          style: AlmaType.meta.copyWith(
            height: 1.5,
            color: AlmaPalette.body.withValues(alpha: quiet ? 0.55 : 0.78),
          ),
        ),
      ],
    );
  }

  /// «Сатурн сейчас соединяется с твоей Серединой неба» — без даты: она стоит
  /// колонкой справа.
  String _phrase(L l, Map<String, dynamic> hit) => CabinetWords.contact(
        l,
        transiting: hit['transiting'] as String? ?? '',
        aspect: hit['aspect'] as String? ?? '',
        natal: hit['natal'] as String? ?? '',
      );
}

/* ── медальон ───────────────────────────────────────────────────────────── */

/// Печать дня: лучевой венец, а внутри него луна сегодняшней фазы.
///
/// **Кольцо стало венцом.** В s1 медальон был диском в тонком золотом кольце —
/// две окружности, между которыми ничего не происходит. На s45 вокруг луны
/// стоит венец из тонких лучей, и он медленно поворачивается: 80 секунд на
/// оборот — движение, которое нельзя поймать взглядом, но которое видно, если
/// вернуться к экрану через минуту. Это то же «небо движется, интерфейс — нет»,
/// что и везде: медальон — небо, а не элемент управления.
class _MoonMedallion extends StatefulWidget {
  const _MoonMedallion({required this.illumination, required this.waxing});

  final double illumination;
  final bool waxing;

  /// Числа s45: коробка 86, диск 52 по центру, лучи от 0.52 до 0.76 радиуса
  /// маски (то есть от 31.6 до края коробки).
  static const box = 86.0;
  static const disc = 52.0;

  @override
  State<_MoonMedallion> createState() => _MoonMedallionState();
}

class _MoonMedallionState extends State<_MoonMedallion>
    with SingleTickerProviderStateMixin {
  late final AnimationController _spin = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 80),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      // «Меньше движения» оставляет венец неподвижным — не замедленным:
      // половина движения читается как подтормаживание.
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (!still) _spin.repeat();
    });
  }

  @override
  void dispose() {
    _spin.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: _MoonMedallion.box,
      height: _MoonMedallion.box,
      child: Stack(
        alignment: Alignment.center,
        children: [
          AnimatedBuilder(
            animation: _spin,
            builder: (context, _) => CustomPaint(
              size: const Size.square(_MoonMedallion.box),
              painter: _RayCrownPainter(turn: _spin.value),
            ),
          ),
          // Дышит, как на доске (7 с туда-обратно): осевший рисунок не
          // замирает — иначе читается как пропавший. «Анимация пропадает, она
          // должна оставаться».
          Breathing(
            child: SizedBox(
              width: _MoonMedallion.disc,
              height: _MoonMedallion.disc,
              child: CustomPaint(
                painter: _MoonPainter(
                  illumination: widget.illumination,
                  waxing: widget.waxing,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Венец: 45 лучей через 8°, каждый шириной 2.4°, гаснущие с обоих концов.
///
/// Кольцевая маска доски — радиальный градиент с мягкими краями (прозрачно до
/// 0.52 радиуса, золото с 0.54 по 0.72, прозрачно к 0.76); радиус там считается
/// до дальнего угла коробки, отсюда 0.707 в долях стороны.
class _RayCrownPainter extends CustomPainter {
  const _RayCrownPainter({required this.turn});

  /// Доля оборота, 0…1.
  final double turn;

  static const _rays = 45;
  static const _width = 2.4 * math.pi / 180;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = size.center(Offset.zero);
    // Дальний угол квадрата — то, от чего CSS считает проценты радиального
    // градиента.
    final reach = size.width * 0.7071;
    final gold = AlmaPalette.gold.withValues(alpha: 0.55);
    final paint = Paint()
      ..shader = RadialGradient(
        radius: 0.7071,
        colors: [
          gold.withValues(alpha: 0),
          gold,
          gold,
          gold.withValues(alpha: 0),
        ],
        stops: const [0.52, 0.54, 0.72, 0.76],
      ).createShader(Offset.zero & size);

    final path = Path();
    for (var i = 0; i < _rays; i++) {
      final a = turn * 2 * math.pi + i * 2 * math.pi / _rays;
      path.moveTo(centre.dx, centre.dy);
      path.arcTo(
        Rect.fromCircle(center: centre, radius: reach),
        a - _width / 2,
        _width,
        false,
      );
      path.close();
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _RayCrownPainter old) => old.turn != turn;
}

/// Луна медальона: диск и тень, посчитанные из освещённости.
///
/// Тень — второй круг, сдвинутый по горизонтали: на растущей луне он уходит
/// влево, на убывающей вправо.
///
/// **Геометрия оставлена своя, а не снята с доски.** На s45 освещённая доля
/// вырезана эллипсом `ellipse(74% 100% at 74% 50%)`, и это выражение при любой
/// освещённости от половины и выше накрывает диск целиком: 74 % там нарисованы
/// полной луной. Иллюстрации это не мешает, живому экрану — мешает ровно так,
/// как уже случалось здесь однажды: рядом со строкой «убывающий серп · 7 %»
/// стояла полная луна, и владелец это увидел. Со сдвинутой тенью 74 % выглядят
/// теми же 74 %, а 7 % остаются серпом.
class _MoonPainter extends CustomPainter {
  _MoonPainter({required this.illumination, required this.waxing});

  final double illumination;
  final bool waxing;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = size.center(Offset.zero);
    final radius = size.width / 2;

    // **Ночная сторона и обводка рисуются всегда, свет ложится поверх.**
    //
    // Порядок был обратный — светлый диск, а сверху тень, — и в новолуние от
    // медальона не оставалось ничего: чёрный кружок без края. На доске в ту же
    // ночь виден тёмно-синий диск в тонкой золотой обводке, потому что там
    // ночная сторона это заливка, а не то, чем закрашивают свет (s45: заливка
    // Night700 0.9, кант Gold 0.35 шириной 0.7).
    canvas.drawCircle(
      centre,
      radius,
      Paint()..color = AlmaPalette.night700.withValues(alpha: 0.9),
    );
    canvas.drawCircle(
      centre,
      radius,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.7
        ..color = AlmaPalette.gold.withValues(alpha: 0.35),
    );

    // Освещённая доля: диск света, из которого вырезан сдвинутый круг тени.
    if (illumination > 0.005) {
      // Сдвиг растёт **с** освещённостью: в новолуние тень концентрична и
      // съедает весь свет, в полнолуние ушла на два радиуса. Написанное
      // наоборот давало полную луну в новолуние — поймано на кадре рядом с
      // подписью «новолуние · 1 %».
      final shift = illumination.clamp(0.0, 1.0) * radius * 2;
      // Убывающая луна освещена слева: тень уходит вправо. Растущая наоборот.
      final dx = waxing ? -shift : shift;
      final bounds = Rect.fromCircle(center: centre, radius: radius + 1);
      canvas.saveLayer(bounds, Paint());
      canvas.drawCircle(
        centre,
        radius,
        Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.92),
      );
      canvas.drawCircle(
        centre.translate(dx, 0),
        radius,
        Paint()..blendMode = BlendMode.clear,
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(covariant _MoonPainter old) =>
      old.illumination != illumination || old.waxing != waxing;
}

/* ── продажа ────────────────────────────────────────────────────────────── */

/// Открыть пейволл подписки — поверхность **P5**.
///
/// **Живое продаётся из живого.** Всё, что закрыто на «Сегодня», — транзиты,
/// соляр, глубина дня — принадлежит подписке и только ей: дверей у этих систем
/// в v3 нет, потому что они пересчитываются, и «навсегда» им не обещают. Раньше
/// отсюда открывалась лестница целиком, то есть на вопрос «что в этом блоке»
/// продукт отвечал прайс-листом.
///
/// [trigger] — по чему тапнули; уходит в воронку ярлыком.
Future<void> openSubscription(BuildContext context,
        {String trigger = 'live_block'}) =>
    showPaywall(context, const PaywallIntent.subscription(), trigger: trigger);

/// План, объяснённый там, где видно, зачем он.
///
/// Блок из s2: заголовок, что внутри, одна кнопка. Не карточка и не баннер —
/// три строки на ночи, как всё остальное на этом экране.
class _PlanInvitation extends StatelessWidget {
  const _PlanInvitation();

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l.cabPlansTitle, style: AlmaType.headingM),
        const SizedBox(height: 8),
        Text(l.cabPlansBody, style: AlmaType.meta),
        const SizedBox(height: 16),
        AlmaButton(
          kind: AlmaButtonKind.outline,
          fills: false,
          label: l.cabPlansCta,
          // Приглашение ведёт на подписку, а не на лестницу: оно стоит в
          // закрытой секции живого слоя и обещает именно её — «всё открыто,
          // каждый день». Лестница в v3 открывается только тихой ссылкой.
          onTap: () => openSubscription(context, trigger: 'today_invite'),
        ),
      ],
    );
  }
}


/// «Сохрани свою карту» — единственная просьба войти во всём кабинете.
class _SaveAccountCard extends StatefulWidget {
  const _SaveAccountCard();

  @override
  State<_SaveAccountCard> createState() => _SaveAccountCardState();
}

class _SaveAccountCardState extends State<_SaveAccountCard> {
  static const _dismissedKey = 'alma.saveAccountDismissed';
  static const _launchesKey = 'alma.saveAccountLaunches';

  /// Сколько раз приложение запускали. Считается **при запуске**, а не при
  /// показе карточки: счёт визитов на экран считал бы совсем другое.
  static Future<void> _noteLaunch() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_launchesKey, (prefs.getInt(_launchesKey) ?? 0) + 1);
  }

  bool _show = false;

  @override
  void initState() {
    super.initState();
    _decide();
  }

  Future<void> _decide() async {
    final prefs = await SharedPreferences.getInstance();
    final dismissed = prefs.getBool(_dismissedKey) ?? false;
    final launches = prefs.getInt(_launchesKey) ?? 0;
    if (mounted) setState(() => _show = !dismissed && launches >= 2);
  }

  Future<void> _later() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_dismissedKey, true);
    if (mounted) setState(() => _show = false);
  }

  @override
  Widget build(BuildContext context) {
    if (!_show) return const SizedBox.shrink();
    final l = L.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l.scrSaveAccountTitle, style: AlmaType.headingM),
        const SizedBox(height: 10),
        Text(l.scrSaveAccountBody, style: AlmaType.meta),
        const SizedBox(height: 14),
        Row(children: [
          AlmaButton(
            kind: AlmaButtonKind.veil,
            fills: false,
            label: l.scrSaveAccountCta,
            // Экран входа появился — кнопка ведёт на него. До этого она стояла
            // выключенной, и это было честно: обещать вход, которого нет, хуже,
            // чем не обещать.
            onTap: () => Navigator.of(context, rootNavigator: true).push(
              CupertinoPageRoute(builder: (_) => const SignInScreen()),
            ),
          ),
          const SizedBox(width: 18),
          TextButton(
            onPressed: _later,
            child: Text(l.scrSaveAccountLater, style: AlmaType.meta),
          ),
        ]),
      ],
    );
  }
}


/// Отметить запуск приложения — для карточки «сохрани карту».
Future<void> noteLaunch() => _SaveAccountCardState._noteLaunch();
