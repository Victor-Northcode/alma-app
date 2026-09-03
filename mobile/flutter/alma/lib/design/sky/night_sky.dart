import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart' show Ticker;

import '../art.dart';
import '../palette.dart';
import 'sky_field.dart';

/// Вуаль над фотографией — три остановки скрима из `SKILL.md`. Ночь как она
/// есть: сверху полупрозрачно, к низу почти глухо.
const _veilNight = <Color>[
  Color(0x800A0D1C),
  Color(0xAD090C1A),
  Color(0xF0070A16),
];

/// Та же вуаль, но плотнее: `.55 / .70 / .95` вместо `.50 / .68 / .94`.
/// Числа кадра V9 (`SCREENS-V3` §V9) — см. [SkyMood.hushed].
const _veilHushed = <Color>[
  Color(0x8C0A0D1C),
  Color(0xB3090C1A),
  Color(0xF2070A16),
];

/// Что это за экран — и сколько неба ему полагается.
///
/// Порт `NightSky.Mood`.
enum SkyMood {
  /// Кабинет — Сегодня, Системы, Настройки. Полное поле, одна аура в стороне
  /// от текста.
  cabinet(starIntensity: 0.9, density: 1.0, grain: 0.26, hasMotes: true, hasComet: false),

  /// Глава или беседа. Поле приглушено, кометы нет: продукт на этом экране —
  /// слова, а свет, пересекающий страницу, пока человек читает, — самое
  /// раздражающее, что может сделать фон.
  reading(starIntensity: 0.45, density: 0.6, grain: 0.18, hasMotes: false, hasComet: false),

  /// Путешествие — вопросы, церемония, портрет. Всё включено и поднято. Это
  /// единственный экран, где небо **и есть** содержание.
  ceremony(starIntensity: 1.0, density: 1.25, grain: 0.30, hasMotes: true, hasComet: true),

  /// Кабинет с приглушённым куполом — отмена подписки (V9) и её сестра W6.
  ///
  /// **Почему числа именно такие.** Холст рисует V9 тем же небом, что и
  /// остальные кадры, кроме двух величин: купол там `rgba(58,52,132,.4)`
  /// вместо `.5`, а вертикальная вуаль плотнее — `.55/.70/.95` против
  /// `.50/.68/.94`. Отсюда обе цифры: [domeAlpha] `0.8` — это ровно `.4 / .5`,
  /// то есть купол гасится долей, а не переписывается своим цветом (цвет у
  /// него один на продукт, и второй завёл бы вторую ночь); [veil] — те же три
  /// остановки, пересчитанные в байты.
  ///
  /// **Поле звёзд не тронуто.** Спека называет ровно две величины, и
  /// приглушать заодно звёзды значило бы дорисовать за холст: экран отмены
  /// обязан быть тише, а не темнее целиком. Небо здесь — фон разговора о
  /// деньгах, и вся его приглушённость в том, чтобы карточка разбора и две
  /// кнопки читались первыми.
  hushed(
    starIntensity: 0.9,
    density: 1.0,
    grain: 0.26,
    hasMotes: true,
    hasComet: false,
    domeAlpha: 0.8,
    veil: _veilHushed,
  );

  const SkyMood({
    required this.starIntensity,
    required this.density,
    required this.grain,
    required this.hasMotes,
    required this.hasComet,
    this.domeAlpha = 1.0,
    this.veil = _veilNight,
  });

  final double starIntensity;
  final double density;
  final double grain;
  final bool hasMotes;

  /// Доля яркости купола — той самой ауры, которой порт собирает верхнее
  /// свечение кадра. `1.0` у всех, кому холст рисует полный купол.
  final double domeAlpha;

  /// Три остановки вуали над фотографией.
  final List<Color> veil;

  /// **Только церемония.** Это решение дизайна, а не настройка.
  ///
  /// Правило кометы — одна на экран, никогда за основным текстом. На вебе оно
  /// выполнимо: комета живёт в пустом герое посадочной. На телефоне такой
  /// области у экрана кабинета нет — надзаголовок, крупный заголовок и первый
  /// абзац занимают верхние 45%, остальное прокручивается сквозь середину, а
  /// хвост длиной 180 точек это почти половина ширины экрана. Куда ни помести
  /// голову, хвост окажется на тексте; засеивание лишь двигало столкновение,
  /// а не убирало его.
  ///
  /// Церемония другая по существу: её верхние 40% — рисунок на пустой ночи,
  /// она коротка, и небо там и есть содержание.
  final bool hasComet;
}

/// Холст. Каждый экран приложения стоит на одном из них.
///
/// Собран здесь, а не каждым экраном, чтобы потолки бренд-бука были
/// структурными, а не советом: одна комета, не больше двух аур, три пылинки.
/// Экрану, которому нужно другое небо, полагается другой [SkyMood]; получить
/// четвёртую ауру случайно невозможно — её некуда положить.
///
/// Небо всегда **фон, а не контейнер**:
///
/// ```dart
/// NightSky(mood: SkyMood.cabinet, child: CustomScrollView(...))
/// ```
class NightSky extends StatefulWidget {
  const NightSky({
    super.key,
    this.mood = SkyMood.cabinet,
    this.seed = 0x414C4D41,
    required this.child,
  });

  final SkyMood mood;

  /// Отличает небо одного экрана от неба другого. Передавайте что-то
  /// устойчивое и своё для экрана, чтобы переход между двумя экранами был
  /// видимым переходом, а не теми же звёздами дважды.
  final int seed;

  final Widget child;

  @override
  State<NightSky> createState() => _NightSkyState();
}

class _NightSkyState extends State<NightSky> with SingleTickerProviderStateMixin {
  late SkyField _field;
  late final Ticker _ticker;
  final ValueNotifier<double> _clock = ValueNotifier<double>(0);

  @override
  void initState() {
    super.initState();
    _field = SkyField.generate(seed: widget.seed, density: widget.mood.density);
    // Одни часы на всё небо. Каждый слой берёт из них своё время, поэтому
    // звёзды, пылинки и аура не заводят три независимых таймера на экран.
    //
    // **Тридцать тиков в секунду, а не каждый кадр.** Тикер шёл с частотой
    // дисплея — на ProMotion это сто двадцать перерисовок полноэкранного
    // холста в секунду ради мерцания с периодом шесть-девять секунд и дрейфа
    // в полминуты. Медленному свету хватает тридцати: между соседними тиками
    // звезда меняет яркость меньше чем на процент, глазу разницы нет, а
    // работы у растеризатора — вчетверо меньше на каждом экране продукта.
    _ticker = createTicker((elapsed) {
      final t = elapsed.inMicroseconds / 1e6;
      if (t - _clock.value >= 1 / 30) _clock.value = t;
    })..start();
  }

  @override
  void didUpdateWidget(covariant NightSky old) {
    super.didUpdateWidget(old);
    if (old.seed != widget.seed || old.mood.density != widget.mood.density) {
      _field = SkyField.generate(seed: widget.seed, density: widget.mood.density);
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    _clock.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Движение выключается, если система просит. «Меньше движения» не значит
    // «без неба»: звёзды — это холст, и убрать их означало бы поменять дизайн,
    // а не успокоить его. Значит — звёзды перестают двигаться.
    final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;

    return Container(
      color: AlmaPalette.night,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // **Туманность и скрим — самый нижний слой продукта.**
          //
          // До дизайн-проекта небо было целиком нарисованным: аура плюс точки.
          // Фотография даёт то, чего кистью не сделать, — неровность, из-за
          // которой фон перестаёт читаться как заливка. Она всегда под скримом
          // и никогда сама по себе: на голой туманности текст нечитаем, а
          // сорок восемь эталонных экранов ставят её именно так.
          _SkyPhoto(widget.mood.veil),
          // Аура стоит высоко и в стороне. Никогда по центру: центральное
          // свечение оказывается ровно под первым абзацем.
          Positioned(
            left: -110 - 260,
            top: -220 - 260,
            width: 520 + 520,
            height: 520 + 520,
            child: _Aura(
              tone: widget.mood == SkyMood.ceremony ? AuraTone.violet : AuraTone.indigo,
              diameter: 520,
              drift: still ? AuraDrift.none : AuraDrift.a,
              clock: _clock,
              dim: widget.mood.domeAlpha,
            ),
          ),
          if (widget.mood == SkyMood.ceremony)
            Positioned(
              right: -130 - 210,
              bottom: -260 - 210,
              width: 420 + 420,
              height: 420 + 420,
              child: _Aura(
                tone: AuraTone.deep,
                diameter: 420,
                drift: still ? AuraDrift.none : AuraDrift.b,
                clock: _clock,
              ),
            ),
          RepaintBoundary(
            child: CustomPaint(
              painter: _StarfieldPainter(
                field: _field,
                intensity: widget.mood.starIntensity,
                clock: _clock,
                still: still,
                motes: widget.mood.hasMotes,
              ),
              isComplex: true,
              willChange: !still,
              size: Size.infinite,
            ),
          ),
          widget.child,
        ],
      ),
    );
  }
}

/// Два слоя звёзд, мерцающих на двух часах, и пылинки — одним холстом.
///
/// **Один рисовальщик, а не сто шестьдесят виджетов.** Сто шестьдесят
/// анимированных узлов — это сто шестьдесят сравнений на каждом кадре; один
/// `CustomPainter` — одно. На экране, которому надо ещё и прокручивать главу,
/// эта разница и есть разница между «небо фоновое» и «из-за неба дёргается
/// прокрутка».
///
/// **У каждой звезды своя фаза.** CSS анимирует *слой* — все звёзды светлеют и
/// гаснут разом, что на девяти звёздах читается как мерцание, а на ста
/// шестидесяти читалось бы как дышащее небо. Период тот же, сдвиг у каждой
/// свой.
class _StarfieldPainter extends CustomPainter {
  _StarfieldPainter({
    required this.field,
    required this.intensity,
    required this.clock,
    required this.still,
    required this.motes,
  }) : super(repaint: clock);

  final SkyField field;
  final double intensity;
  final ValueNotifier<double> clock;
  final bool still;
  final bool motes;

  /// Секунд на одно полное разгорание-угасание ближнего слоя. Дальний идёт в
  /// полтора раза медленнее и начинает на 1.6 с позже, поэтому два слоя не
  /// совпадают никогда.
  static const _nearPeriod = 6.0;
  static const _farPeriod = 9.0;
  static const _farOffset = 1.6;

  /// Насколько пылинка поднимается за один свой цикл, долей высоты.
  static const _rise = 90.0;

  @override
  void paint(Canvas canvas, Size size) {
    final now = still ? null : clock.value;
    _drawLayer(canvas, size, field.far, now, base: 0.5, period: _farPeriod, offset: _farOffset);
    _drawLayer(canvas, size, field.near, now, base: 1.0, period: _nearPeriod, offset: 0);
    if (motes && !still) _drawMotes(canvas, size, clock.value);
  }

  void _drawLayer(
    Canvas canvas,
    Size size,
    List<SkyStar> stars,
    double? time, {
    required double base,
    required double period,
    required double offset,
  }) {
    final paint = Paint();
    for (final star in stars) {
      final double brightness;
      if (time != null) {
        // Кривая CSS — ease-in-out между 0.25 и 1. Приподнятый косинус даёт ту
        // же форму без таблицы ключевых кадров и непрерывен, поэтому звезда не
        // прыгает, когда часы заворачиваются.
        final t = ((time + offset) / period + star.phase) % 1;
        final eased = (1 - math.cos(t * 2 * math.pi)) / 2;
        brightness = 0.25 + eased * 0.75;
      } else {
        brightness = 0.7;
      }
      paint.color = star.tint.colour.withValues(alpha: brightness * base * intensity);
      canvas.drawCircle(
        Offset(star.x * size.width, star.y * size.height),
        star.radius,
        paint,
      );
    }
  }

  void _drawMotes(Canvas canvas, Size size, double now) {
    final paint = Paint();
    for (final mote in field.motes) {
      final t = ((now + mote.delay) / mote.duration) % 1;
      final double opacity;
      if (t < 0.20) {
        opacity = t / 0.20 * 0.70;
      } else if (t < 0.80) {
        opacity = 0.70 - (t - 0.20) / 0.60 * 0.20;
      } else {
        opacity = 0.50 * (1 - (t - 0.80) / 0.20);
      }
      paint.color = AlmaPalette.starFill.withValues(alpha: opacity * intensity);
      canvas.drawCircle(
        Offset(mote.x * size.width, mote.y * size.height - t * _rise),
        mote.size / 2,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _StarfieldPainter old) =>
      old.field != field || old.intensity != intensity || old.still != still;
}

/// Какой оттенок у пятна. Единственное место, где в продукте появляется индиго.
enum AuraTone { indigo, deep, gold, violet }

/// На каком дрейфе аура. Две ауры на одном экране не должны делить один — иначе
/// они движутся парой и экран начинает дышать.
enum AuraDrift {
  none(0),
  a(30),
  b(36);

  const AuraDrift(this.period);
  final double period;
}

/// Размытое пятно цвета за ночью.
class _Aura extends StatelessWidget {
  const _Aura({
    required this.tone,
    required this.diameter,
    required this.drift,
    required this.clock,
    this.dim = 1.0,
  });

  final AuraTone tone;
  final double diameter;
  final AuraDrift drift;
  final ValueNotifier<double> clock;

  /// Доля яркости пятна. Гасится **прозрачностью цвета, а не `Opacity`**:
  /// слой поверх размытого пятна во весь экран — это лишний буфер на каждом
  /// кадре ради того, что складывается в одно умножение.
  final double dim;

  List<Color> get _colours => switch (tone) {
        AuraTone.indigo => [
            AlmaPalette.indigoBright.withValues(alpha: 0.42 * dim),
            AlmaPalette.indigo.withValues(alpha: 0.22 * dim),
            const Color(0x00000000),
          ],
        AuraTone.deep => [
            AlmaPalette.indigoDeep.withValues(alpha: 0.38 * dim),
            const Color(0x00000000),
          ],
        AuraTone.gold => [
            AlmaPalette.gold.withValues(alpha: 0.20 * dim),
            const Color(0x00000000),
          ],
        AuraTone.violet => [
            const Color(0xFF4A3A9E).withValues(alpha: 0.34 * dim),
            const Color(0x00000000),
          ],
      };

  List<double> get _stops => switch (tone) {
        AuraTone.indigo => const [0.00, 0.44, 0.70],
        AuraTone.deep => const [0.0, 0.70],
        AuraTone.gold => const [0.0, 0.66],
        AuraTone.violet => const [0.0, 0.68],
      };

  @override
  Widget build(BuildContext context) {
    final blob = Center(
      child: SizedBox(
        width: diameter,
        height: diameter,
        child: DecoratedBox(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: _colours, stops: _stops),
          ),
        ),
      ),
    );

    // CSS размывает на 34 пикселя поверх и без того мягкого градиента. Один
    // градиент заметно полосил на OLED при этих прозрачностях; убирает кольца
    // именно размытие.
    //
    // **Граница перерисовки — чтобы размытие посчиталось один раз.** Дрейф —
    // это `Transform.translate` над пятном, и без собственного слоя сдвиг на
    // каждом тике заставлял растеризатор заново размывать тысячу точек
    // диаметра — самая дорогая операция кадра ради движения на три сотых.
    // Со слоем пятно размывается однажды, а дальше по экрану ездит готовая
    // картинка. Половина «неоптимизированности» Android (владелец,
    // 02.09.2026) сидела здесь: аура есть на каждом экране продукта.
    final blurred = RepaintBoundary(
      child: ImageFiltered(
        imageFilter: ImageFilter.blur(sigmaX: 34, sigmaY: 34),
        child: blob,
      ),
    );

    if (drift == AuraDrift.none) return IgnorePointer(child: blurred);

    return IgnorePointer(
      child: AnimatedBuilder(
        animation: clock,
        builder: (context, child) {
          final t = clock.value / drift.period;
          final sway = math.sin(t * 2 * math.pi);
          return Transform.translate(
            offset: Offset(
              (drift == AuraDrift.a ? -1 : 1) * sway * diameter * 0.035,
              (drift == AuraDrift.a ? 1 : -1) * sway * diameter * 0.035,
            ),
            child: child,
          );
        },
        child: blurred,
      ),
    );
  }
}

/// Фотография туманности под градиентным скримом.
///
/// Снимок один на всё приложение и лежит в бандле: он нужен на первом же
/// экране, до всякой сети. Скрим — три остановки из `SKILL.md`: сверху
/// полупрозрачно, к низу почти глухо, чтобы нижние две трети экрана держали
/// текст.
class _SkyPhoto extends StatelessWidget {
  const _SkyPhoto(this.veil);

  /// Три остановки скрима — приходят от [SkyMood], потому что плотность вуали
  /// это свойство кадра, а не фотографии.
  final List<Color> veil;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        Image.asset(
          AlmaArt.sky,
          fit: BoxFit.cover,
          alignment: Alignment.topCenter,
          // Ошибка загрузки не должна оставлять белую дыру во весь экран:
          // ночь под фотографией уже залита, и её достаточно.
          errorBuilder: (_, _, _) => const SizedBox.shrink(),
        ),
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: veil,
              stops: const [0, 0.55, 1],
            ),
          ),
        ),
      ],
    );
  }
}
