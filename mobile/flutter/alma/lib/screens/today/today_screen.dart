import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../design/arrival.dart';
import '../settings/sign_in_screen.dart';
import '../../design/buttons.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
import '../offer_screen.dart';
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

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final l = L.of(context);

    // Перезагрузка по смене профиля, не по созданию экрана. На iOS это чинилось
    // как «task(id: profile.id)»: все четыре вкладки живут всю жизнь
    // приложения, и загрузка «один раз при создании» означала экран, навсегда
    // застрявший на «Читаю твою карту», если рождение ввели после запуска.
    final profileId = session.profile?.id;
    if (profileId != null && profileId != _loadedForProfile) {
      _loadedForProfile = profileId;
      final model = _model ??= TodayModel(session.client);
      model.addListener(() {
        if (mounted) setState(() {});
      });
      model.load(locale: session.locale, subscriber: session.isSubscriber);
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
        if (model != null) ...[
          // 22 от низа шапки до панели — число s45. Раньше здесь стояло 28
          // (`gapLarge`), потому что панели не было вовсе и отбивка была общей.
          const SizedBox(height: 22),
          _HoroscopePanel(model: model, subscriber: session.isSubscriber),
          // Области — вторая панель, и только подписчику: под замком гороскоп
          // целиком, а не его первый абзац.
          if (session.isSubscriber) ...[
            const SizedBox(height: 14),
            _AreasPanel(model: model),
          ],
        ],
        // **План, сказанный словами, тому, у кого его нет.**
        //
        // Он был доступен с лестницы, которая открывалась, только если сперва
        // ткнуть в закрытую главу, — и владелец прошёл собственный продукт из
        // конца в конец, ни разу не увидев, что подписка вообще предлагается.
        // «Один тап в настройках» оказалось фразой, не стоящей ничего: никто
        // не открывает настройки, чтобы ему что-нибудь продали.
        //
        // Здесь — потому что это экран, которым подписчик пользуется каждый
        // день, и, значит, экран, где причина подписки читается: транзиты над
        // ним движутся, а купленная однажды глава — нет. Исчезает в ту секунду,
        // когда план появляется.
        //
        // **На ночи, а не в стекле** — так это нарисовано в s2: панель на этом
        // экране принадлежит гороскопу, и приглашение, одетое в такую же,
        // читалось бы вторым гороскопом.
        if (!session.isSubscriber) ...[
          const SizedBox(height: _sectionGap),
          const _PlanInvitation(),
        ],
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
        ],
      ],
    );
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
  const _PanelLabel(this.text, {this.trailing});

  final String text;

  /// Что стоит у правого канта вместо конца линии — время чтения на карточке
  /// гороскопа (`today-reading-spec §2`). Линия отдаёт ему место, а не
  /// упирается в него.
  final String? trailing;

  @override
  Widget build(BuildContext context) {
    final tail = trailing;
    return LayoutBuilder(
      builder: (context, box) => Row(
        children: [
          ConstrainedBox(
            constraints: BoxConstraints(maxWidth: math.max(0, box.maxWidth - 40)),
            child: Text(text.toUpperCase(), style: AlmaType.overline),
          ),
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
          if (tail != null) ...[
            const SizedBox(width: 10),
            Text(tail,
                style: AlmaType.meta.copyWith(color: AlmaPalette.muted3)),
          ],
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
class _HoroscopePanel extends StatelessWidget {
  const _HoroscopePanel({required this.model, required this.subscriber});

  final TodayModel model;
  final bool subscriber;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return _GlassPanel(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PanelLabel(l.cabHoroscopeToday, trailing: _minutes(l)),
          if (subscriber) ..._voice(l) else ..._locked(context, l),
        ],
      ),
    );
  }

  /// Залоченное состояние — блок из s2, целиком: строка о том, что это такое и
  /// когда приходит, и строка-дверь. Ни блюра поверх настоящего текста, ни
  /// пустой карточки: показывать размытым то, за что просят денег, — это
  /// обещание, которого продукт не давал.
  List<Widget> _locked(BuildContext context, L l) => [
        const SizedBox(height: 20),
        Text(l.cabHoroscopeLocked, style: AlmaType.body),
        const SizedBox(height: 6),
        AlmaActionRow(
          label: l.cabHoroscopeOpen,
          onTap: () => openOffer(context),
        ),
      ];

  /// «3 мин» у правого канта подписи — сколько читать целиком.
  ///
  /// **Считается по словам, а не приходит с сервера.** Это измерение готового
  /// текста, а не его разрезание: клиенту запрещено делить текст на части
  /// (`§3` — «движок помечает части, клиент не разрезает текст сам»), но
  /// сосчитать, сколько в нём слов, он вправе.
  ///
  /// 140 слов в минуту — темп внимательного чтения, не просмотра: этот текст
  /// про самого читающего, и его перечитывают, а не проглядывают. Округление
  /// вверх и пол в одну минуту: «0 мин» на карточке выглядело бы поломкой.
  String? _minutes(L l) {
    if (!subscriber) return null;
    if (model.line case LoadDone<ReadingResponse>(value: final answer)) {
      final words = answer.reading.body
          .expand((p) => p.split(RegExp(r'\s+')))
          .where((w) => w.isNotEmpty)
          .length;
      if (words == 0) return null;
      return l.todayReadMinutes('${math.max(1, (words / 140).ceil())}');
    }
    return null;
  }

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

  /// Дальше этого экран дат не обещает.
  ///
  /// **«Jun 13» в августе — обещание не про сегодня.** Движок отдаёт `upcoming`
  /// на месяцы вперёд, и на живом аккаунте четыре области показали «Jun 13 /
  /// Sep 14 / May 8 / Jun 9» — колонку дат, к сегодняшнему дню не относящихся
  /// ни одной. На s1 дата рядом с областью читается как «это случится скоро»,
  /// и растягивать «скоро» на полгода значит врать оформлением.
  ///
  /// Правило владельца: ближе тридцати дней — с датой, дальше — та же строка
  /// области и та же фраза, но без даты справа. Точные далёкие аспекты живут в
  /// «Транзитах» (`ahead`/`long`), где у них есть и место, и контекст.
  static const _horizon = Duration(days: 30);

  /// Дата, если она в пределах горизонта. Прошедшую не трогаем: контакт,
  /// перешедший точность, всё ещё про эти дни — режется только даль.
  static DateTime? _dated(DateTime? day) {
    if (day == null) return null;
    return day.toLocal().difference(DateTime.now()) <= _horizon ? day : null;
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final quiet = hit == null;
    final exact = hit?['exact'] as String?;
    final day = _dated(exact == null ? null : DateTime.tryParse(exact));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Expanded(
              child: Text(
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
            ),
            // Дата — только когда она у движка есть: контакту, уже прошедшему
            // точность, выдумывать «сегодня» нельзя именно на этом экране.
            if (day != null) ...[
              const SizedBox(width: 12),
              Text(
                // «Aug 18», а не «August 18»: в колонке справа полное имя
                // месяца съедало бы половину строки области.
                DateFormat.MMMd(l.localeName).format(day.toLocal()),
                style: AlmaType.numeral.copyWith(fontSize: 13),
              ),
            ],
          ],
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

/// Открыть витрину планов.
///
/// `rootNavigator`, потому что вкладка «Мои системы» держит свой стек, а
/// витрина — страница поверх всего кабинета, включая бар: продажа не должна
/// оказаться внутри одной вкладки.
void openOffer(BuildContext context, {SystemSlug? system}) {
  Navigator.of(context, rootNavigator: true).push(
    CupertinoPageRoute(builder: (context) => OfferScreen(system: system)),
  );
}

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
          // Без системы: приглашение к плану открывает лестницу планами
          // вперёд. На нативе здесь стоит `.offer(system: .natal)`, и это
          // ставит первой ступенью натальную дверь — то есть отвечает на
          // «покажи планы» ценой одной главы.
          onTap: () => openOffer(context),
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
