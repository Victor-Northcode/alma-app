import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../design/arrival.dart';
import '../settings/sign_in_screen.dart';
import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/section_label.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
import '../offer_screen.dart';
import '../systems/writing_art.dart';
import 'today_model.dart';

/// Первая страница кабинета: сегодняшнее небо против карты рождения.
///
/// Порт `mobile/ios/Alma/Screens/Today/TodayScreen.swift`. Один рассказ о дне
/// под одним именем: экран когда-то говорил одно и то же небо трижды под
/// заголовками, которые обычный человек не мог разобрать, и владелец спросил,
/// зачем средний. Честным ответом было «в таком порядке мы их строили» — теперь
/// блок один, называется так, как это называют люди, и открывает его подписка:
/// расчёты бесплатны навсегда, продаётся написанное.
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
          const SizedBox(height: AlmaMetrics.gapLarge),
          _DaySection(model: model, subscriber: session.isSubscriber),
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
        if (!session.isSubscriber) ...[
          const SizedBox(height: AlmaMetrics.gapSection),
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
          const SizedBox(height: AlmaMetrics.gapSection),
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
      // Глиф засечным и 19-м кеглем — на нативе это `AlmaFonts.display(19)`,
      // а не строка обычного текста.
      Text('☽',
          style: AlmaType.displayL
              .copyWith(fontSize: 19, color: AlmaPalette.goldBright)),
      const SizedBox(width: 8),
      Text(line, style: AlmaType.meta.copyWith(color: AlmaPalette.muted2)),
    ]);
  }

  String? _moonLine(L l, TodayModel model) {
    final moon = _moonPhase(model);
    if (moon == null) return null;
    final name = _phaseName(l, moon['phase'] as String? ?? '');
    final lit = ((moon['illumination'] as num?)?.toDouble() ?? 0) * 100;
    return '$name · ${lit.round()} %';
  }

  Map<String, dynamic>? _moonPhase(TodayModel model) {
    final sky = model.sky;
    if (sky is! LoadDone<CalcResult>) return null;
    final now = sky.value.data['sky_now'];
    if (now is! Map) return null;
    final moon = now['moon_phase'];
    return moon is Map ? moon.cast<String, dynamic>() : null;
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
    final moon = _moonPhase(model);
    if (moon == null) return null;
    return Padding(
      padding: const EdgeInsets.only(top: 26),
      // Дышит, как на iOS: осевший рисунок не замирает — иначе читается как
      // пропавший. «Анимация пропадает, она должна оставаться».
      child: Breathing(
        child: SizedBox(
          width: 68,
          height: 68,
          child: CustomPaint(
            painter: _MoonPainter(
              illumination: ((moon['illumination'] as num?)?.toDouble() ?? 0),
              waxing: moon['waxing'] as bool? ?? true,
            ),
          ),
        ),
      ),
    );
  }
}

/// «Гороскоп на сегодня» — блок дня.
///
/// **Только подписчикам, по решению владельца**: не первый абзац, не проба.
/// Разовая покупка его тоже не открывает — ни блюра, ни пустой карточки. Одна
/// фраза о том, что это такое и где живёт, и дверь.
class _DaySection extends StatelessWidget {
  const _DaySection({required this.model, required this.subscriber});

  final TodayModel model;
  final bool subscriber;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionLabel(l.cabHoroscopeToday),
        const SizedBox(height: 14),
        if (subscriber) ...[
          ..._voice(l),
          const SizedBox(height: 4),
          ..._areas(l),
        ] else ...[
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Text(l.cabHoroscopeLocked, style: AlmaType.body),
          ),
          AlmaActionRow(
            label: l.cabHoroscopeOpen,
            onTap: () => openOffer(context),
          ),
        ],
      ],
    );
  }

  List<Widget> _voice(L l) {
    switch (model.line) {
      case LoadRunning():
        // **Ожидание — это страница, а не строка.** Здесь стояли неподвижная
        // точка и подпись «читаю твою карту» над пустотой, и полминуты это
        // выглядело сломанным экраном. В макете (s27) на месте будущего текста
        // лежат заготовки строк, по которым идёт блик: человек видит, сколько
        // текста придёт и куда он ляжет, ещё до первого слова.
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
        // Подписчику — весь день; остальным первая строка. Сейчас, до экрана
        // покупок, показывается всё тело: тестовый аккаунт владельца подписан.
        return [
          for (final paragraph in answer.reading.body)
            Padding(
              padding: const EdgeInsets.only(top: 6, bottom: 8),
              child: Text(paragraph, style: AlmaType.dayVoice),
            ),
        ];
      case LoadFailed<ReadingResponse>(error: final error):
        return [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
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

  /// Четыре области жизни, у каждой ближайший контакт — или честное «здесь
  /// сегодня тихо». Пустая область, заполненная чем-нибудь, была бы ровно тем
  /// провалом, ради избегания которого экран существует: это строка, которую
  /// не может написать ни один гороскоп по знаку Солнца.
  List<Widget> _areas(L l) {
    final sky = model.sky;
    // Пока небо считается, области стоят заготовками — по макету s27: золотая
    // метка 52×11 и строка под ней, отбивка 30 у первой группы и 22 у
    // остальных (первая получает 26, потому что четыре точки над ней уже
    // отдал `build`). Заготовка ничего не обещает про содержание: она держит
    // место, чтобы страница не прыгнула, когда придут настоящие строки.
    if (sky is LoadRunning<CalcResult>) {
      return [
        for (var i = 0; i < 4; i++)
          Padding(
            padding: EdgeInsets.only(top: i == 0 ? 26 : 22),
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
    final data = sky.value.data;

    // **Оба списка, и пропуск одного — то, что опустошало экран.** `active` —
    // что в орбе прямо сейчас, `upcoming` — что на подходе; читая только
    // первый, владелец открыл гороскоп, где все четыре области сказали «тихо».
    // Они говорили правду про active — а в upcoming стояло сорок контактов.
    final hits = <Map<String, dynamic>>[
      ...(data['active'] as List? ?? const []).whereType<Map>().map((e) => e.cast<String, dynamic>()),
      ...(data['upcoming'] as List? ?? const []).whereType<Map>().map((e) => e.cast<String, dynamic>()),
    ];

    // Порядок серверный, зеркалится здесь, чтобы двое молча не разошлись в
    // том, что идёт первым.
    const order = ['work', 'love', 'money', 'body'];

    return [
      for (final area in order)
        Padding(
          padding: const EdgeInsets.only(top: 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                CabinetWords.area(l, area),
                style: AlmaType.meta.copyWith(
                  color: AlmaPalette.goldBright,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 3),
              Builder(builder: (context) {
                final mine = hits.where((h) => h['area'] == area).toList()
                  ..sort((a, b) => ((b['urgency'] as num?) ?? 0)
                      .compareTo((a['urgency'] as num?) ?? 0));
                if (mine.isEmpty) {
                  return Text(l.cabAreaQuiet, style: AlmaType.meta);
                }
                return Text(_sentence(l, mine.first), style: AlmaType.meta);
              }),
            ],
          ),
        ),
    ];
  }

  /// «Сатурн сейчас и Середина неба в твоей карте: соединение, 14 августа.»
  /// Дата — только когда она у движка есть: контакту, уже прошедшему точность,
  /// выдумывать «сегодня» нельзя именно на этом экране.
  String _sentence(L l, Map<String, dynamic> hit) {
    final phrase = CabinetWords.contact(
      l,
      transiting: hit['transiting'] as String? ?? '',
      aspect: hit['aspect'] as String? ?? '',
      natal: hit['natal'] as String? ?? '',
    );
    final exact = hit['exact'] as String?;
    final day = exact == null ? null : DateTime.tryParse(exact);
    if (day == null) return '$phrase.';
    return '$phrase, ${DateFormat.MMMMd(l.localeName).format(day.toLocal())}.';
  }
}

/// Луна медальона: диск и тень, посчитанные из освещённости.
///
/// Тень — второй круг, сдвинутый по горизонтали: на растущей луне он уходит
/// влево, на убывающей вправо. Та же геометрия, что у `MoonMedallion` на iOS.
class _MoonPainter extends CustomPainter {
  _MoonPainter({required this.illumination, required this.waxing});

  final double illumination;
  final bool waxing;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = Offset(size.width / 2, size.height / 2);
    // Диск заметно меньше кольца — воздух между ними и есть «печать»; при
    // 0.36 диск почти касался кольца, и медальон читался как кнопка. Сверено
    // с нативным кадром бок о бок на одном симуляторе.
    final radius = size.width * 0.30;

    // Кольцо вокруг — золотая волосяная линия.
    canvas.drawCircle(
      centre,
      size.width * 0.47,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AlmaPalette.gold.withValues(alpha: 0.35),
    );

    // **Ночная сторона и обводка рисуются всегда, свет ложится поверх.**
    //
    // Порядок был обратный — светлый диск, а сверху тень, — и в новолуние от
    // медальона не оставалось ничего: чёрный кружок без края. На нативе в ту же
    // ночь виден тёмно-синий диск в тонкой золотой обводке, потому что там
    // ночная сторона это заливка, а не то, чем закрашивают свет
    // (`MoonMedallion.swift`: fill Night700 0.9, stroke Gold 0.3 шириной 0.7).
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
        ..color = AlmaPalette.gold.withValues(alpha: 0.3),
    );

    // Освещённая доля: диск света, из которого вырезан сдвинутый круг тени.
    // Сдвиг растёт с освещённостью — в новолуние тень концентрична и съедает
    // весь свет, в полнолуние ушла на два радиуса. Первый порт перепутал
    // направление роста: при серпе в 7% луна рисовалась полной. Найдено на
    // экране, рядом со строкой «убывающий серп · 7 %».
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
/// Порт `PlanInvitation` из `TodayScreen.swift`: заголовок, что внутри, одна
/// кнопка. Не карточка и не баннер — три строки на ночи, как всё остальное на
/// этом экране.
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
