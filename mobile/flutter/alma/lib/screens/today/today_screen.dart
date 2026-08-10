import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../design/arrival.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
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
      model.load(locale: session.locale);
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
      onRefresh: () async {
        if (model != null && session.hasBirthData) {
          await model.load(locale: session.locale);
        }
      },
      children: [
        if (model != null) ...[
          if (_moonLine(l, model) case final line?)
            Padding(
              padding: const EdgeInsets.only(bottom: AlmaMetrics.gapLarge),
              child: Row(children: [
                const Text('☽',
                    style: TextStyle(fontSize: 17, color: AlmaPalette.goldBright)),
                const SizedBox(width: 8),
                Text(line, style: AlmaType.meta.copyWith(fontSize: 12.5)),
              ]),
            ),
          _DaySection(model: model),
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
/// Разовая покупка его тоже не открывает. Здесь пока показывается сама секция
/// и области; дверь тарифа приедет вместе с экраном покупок.
class _DaySection extends StatelessWidget {
  const _DaySection({required this.model});

  final TodayModel model;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Линейка раздела: подпись и волосяная линия, гаснущая вправо.
        Row(children: [
          Text(l.cabHoroscopeToday.toUpperCase(), style: AlmaType.overline),
          const SizedBox(width: 12),
          Expanded(
            child: Container(
              height: 1,
              decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
            ),
          ),
        ]),
        const SizedBox(height: 14),
        ..._voice(l),
        const SizedBox(height: 4),
        ..._areas(l),
      ],
    );
  }

  List<Widget> _voice(L l) {
    switch (model.line) {
      case LoadRunning():
        return [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Row(children: [
              const _AlmaPresence(size: 24),
              const SizedBox(width: 12),
              Text(l.cabReadingChart, style: AlmaType.meta),
            ]),
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

/// Тёплая точка света — присутствие Alma, у того размера, где кольцо снято.
class _AlmaPresence extends StatelessWidget {
  const _AlmaPresence({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(colors: [
          AlmaPalette.starFill,
          AlmaPalette.gold.withValues(alpha: 0.5),
          AlmaPalette.gold.withValues(alpha: 0.0),
        ], stops: const [0.0, 0.45, 1.0]),
      ),
    );
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
      size.width * 0.48,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AlmaPalette.gold.withValues(alpha: 0.4),
    );

    // Освещённый диск.
    canvas.drawCircle(
      centre,
      radius,
      Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.9),
    );

    // Ночная сторона: второй круг, сдвинутый по горизонтали и **обрезанный по
    // диску**. Сдвиг растёт с освещённостью — в новолуние тень концентрична и
    // накрывает всё, в полнолуние ушла на два радиуса и не видна. Первый порт
    // перепутал направление роста: при серпе в 7% тень почти полностью уезжала
    // с диска, луна рисовалась полной, а сам сдвинутый круг торчал из-за края
    // медальона. Найдено на экране, рядом со строкой «убывающий серп · 7 %» —
    // медальон противоречил собственной подписи.
    if (illumination < 0.995) {
      final shift = illumination.clamp(0.0, 1.0) * radius * 2;
      // Убывающая луна освещена слева: тень уходит вправо, оставляя серп с
      // левого края, — как на медальоне нативного экрана. Растущая наоборот.
      final dx = waxing ? -shift : shift;
      canvas.save();
      canvas.clipPath(Path()..addOval(Rect.fromCircle(center: centre, radius: radius)));
      canvas.drawCircle(
        centre.translate(dx, 0),
        radius,
        // Ночная сторона почти непрозрачна: серп при 7% должен быть нитью,
        // а не широким бликом — как на нативном медальоне.
        Paint()..color = AlmaPalette.night850.withValues(alpha: 0.97),
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(covariant _MoonPainter old) =>
      old.illumination != illumination || old.waxing != waxing;
}
