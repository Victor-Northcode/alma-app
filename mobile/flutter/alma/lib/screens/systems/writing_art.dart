import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/plates.dart';
import '../../design/self_drawing.dart' show phase;
import '../../net/models.dart' show SystemSlug;

/// Экраны ожидания: то, на что человек смотрит, пока Alma считает и пишет.
///
/// Здесь живут четыре вещи из макета — рисунок письма (s29), заготовка колеса
/// (s28), дышащая точка присутствия и мерцающая полоса (s27). Они собраны в
/// одном файле не по родству формы, а по родству повода: это всё «ещё не
/// пришло», и правила у них общие — ничего не пропадает, ничего не выдумывает
/// данных, ничего не жжёт батарею дольше необходимого.
///
/// **Числа взяты из макета, а не подобраны.** Ключевые кадры HTML-эталона:
/// `draw660` — 3.2 с ease-in-out (та самая «чертит себя»), `spinSlow` — 70 с
/// линейно на рисунке главы и 40/26 с на кольцах заготовки, `breathe` — 2.6 с
/// у точки и 2.4 с у центра колеса, `shimmer` — 1.9 с линейно.
///
/// **Про «меньше движения».** Система, попросившая покоя, получает не пустоту,
/// а осевший рисунок: вступление доигрывается в один кадр и застывает. Экран
/// ожидания, с которого исчезла картинка, читался бы как сломанный — это ровно
/// то, чего просьба о покое не просила.

// ── s29 · рисунок, который чертит себя ──────────────────────────────────────

/// Что человек видит те сорок-девяносто секунд, пока глава пишется.
///
/// Порт `WritingArt.swift`, доведённый до экрана s29 макета. Раньше здесь
/// стояла одна фигура на пустом небе: «пара тонких дуг», начинавшихся с нуля
/// каждый цикл, — и полторы минуты это читалось как мигание, а не как письмо.
///
/// Теперь у рисунка два слоя, и они отвечают за разное:
///
/// * **Небо** — постоянная часть макета: пунктирная орбита, две наклонные
///   эллиптические, круг, внутреннее кольцо и три звезды. Оно чертит себя один
///   раз за 3.2 с и дальше стоит. Стоит буквально — кэшированным слоем, без
///   единой перерисовки: полторы минуты перекладывать эти линии кадр в кадр
///   значило бы греть телефон ради картинки, которая не меняется.
/// * **Перо** — золотая дуга, которая пишется и стирается, и фигура самой
///   системы. Это единственное, что живёт кадр в кадр, и это одна тонкая
///   линия.
///
/// Рисунок ничего не утверждает о карте: это не диаграмма, а ожидание, и
/// поэтому у него нет данных на входе. Диаграммы систем — отдельная работа и
/// читают свои payload'ы.
class WritingArt extends StatefulWidget {
  const WritingArt({super.key, this.size = 260, this.seed = 0, this.grain = 0});

  final double size;

  /// Чей это рисунок. Каждая система ждёт по-своему: у одной орбиты, у другой
  /// решётка, у третьей комета. На нативе у каждой из восьми систем своя
  /// анимация письма, и порт держит то же правило — иначе восемь ожиданий
  /// выглядят одной заставкой. Небо вокруг у всех общее: это макет.
  final int seed;

  /// Какая это глава внутри своей системы — [chapterGrain].
  ///
  /// Семейство задаёт система, экземпляр — глава: число элементов, наклон,
  /// плотность, ритм. У натальной карты шестнадцать глав, каждая ждёт по
  /// сорок-девяносто секунд, и все шестнадцать ожиданий под одной картинкой
  /// читались как «опять то же самое», а не как шестнадцать разных работ.
  ///
  /// Ноль — первый экземпляр семейства. Экраны, у которых главы нет вовсе
  /// (церемония анкеты, пустая система, стена закрытой главы), берут его и
  /// получают то же, что и раньше.
  final int grain;

  @override
  State<WritingArt> createState() => _WritingArtState();
}

/// Зерно главы: пара «система + слаг главы» → номер экземпляра в семействе.
///
/// **Почему номер, а не хеш слага.** Хеш детерминирован, но раскладывает
/// шестнадцать натальных глав по параметрам как повезёт: две главы с заметной
/// вероятностью выпадают на один и тот же набор — то есть на одну картинку, и
/// починить такую пару, не сдвинув все остальные, нельзя. Порядковый номер
/// этого не допускает по построению: шестнадцать глав — шестнадцать разных
/// мест в таблице параметров.
///
/// Список слагов берётся из карты вклеек: это единственное место в приложении,
/// где перечислены все сорок одна глава, и перечислены в порядке движка
/// (`alma/ai/chapters.py`). Индекс главы с сервера для этого не годится — он
/// приезжает вместе с оглавлением, то есть уже после первого кадра, и рисунок
/// менялся бы на глазах у ждущего.
///
/// Незнакомый слаг — глава появилась в движке раньше, чем картина к ней, —
/// откатывается на хеш: он всё-таки постоянен для этой главы, а соседний
/// экземпляр семейства ему достанется разве что случайно.
int chapterGrain(SystemSlug system, String chapter) {
  final slugs = AlmaPlates.all[system]?.keys;
  if (slugs != null) {
    var at = 0;
    for (final slug in slugs) {
      if (slug == chapter) return at;
      at++;
    }
  }
  // FNV-1a, обрезанная до положительного: нужен только разброс, не стойкость.
  var hash = 0x811c9dc5;
  for (final unit in chapter.codeUnits) {
    hash = ((hash ^ unit) * 0x01000193) & 0x3fffffff;
  }
  return hash;
}

class _WritingArtState extends State<WritingArt> with TickerProviderStateMixin {
  /// Вступление: небо чертит себя. `draw660` из макета — 3.2 с ease-in-out.
  late final AnimationController _intro = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 3200),
  );

  /// Перо: та же кривая «туда-обратно», `infinite alternate` макета. Дуга
  /// пишется и стирается — это и есть видимый признак того, что текст сейчас
  /// пишут, а не что экран завис.
  late final AnimationController _pen = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 3200),
  );

  /// Своя жизнь фигуры системы. Длительность круга тоже своя: одинаковый ритм
  /// у восьми ожиданий читается как одна и та же заставка.
  ///
  /// Глава добавляет к ритму системы свою долю — соседние главы дышат заметно
  /// по-разному, но ни одна не выпадает из спокойного диапазона 6…10 секунд:
  /// это фон ожидания, а не метроном.
  late final AnimationController _life = AnimationController(
    vsync: this,
    duration: Duration(
      milliseconds: 6200 + (widget.seed % 5) * 700 + (widget.grain % 7) * 320,
    ),
  );

  /// Небо поворачивается за 70 секунд — `spinSlow 70s linear infinite`. Это
  /// поворот слоя, а не перерисовка: композитору он стоит одной матрицы.
  late final AnimationController _spin = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 70),
  );

  /// Центральная звезда дышит: 2.6 с туда-обратно, значит 1.3 с в одну сторону.
  late final AnimationController _breath = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1300),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (still) {
        // Покой — это осевший рисунок, а не пустое место. Небо дочерчено,
        // фигура остановлена на середине своего круга: там их видно больше
        // всего, а не в нуле, где половина элементов ещё не появилась.
        _intro.value = 1;
        _pen.value = 0;
        _life.value = 0.5;
        return;
      }
      _life.repeat();
      _spin.repeat();
      _breath.repeat(reverse: true);
      // Перо подхватывает ровно там, где вступление его оставило: дуга дошла
      // до конца, и первый ход пера — обратный. Иначе на стыке она прыгала бы
      // с полной длины на нулевую.
      _intro.forward().whenComplete(() {
        if (mounted) _pen.repeat(reverse: true);
      });
    });
  }

  @override
  void dispose() {
    _intro.dispose();
    _pen.dispose();
    _life.dispose();
    _spin.dispose();
    _breath.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        // Размер — потолок, а не приказ: на узком телефоне поле уже рисунка,
        // и жёсткий квадрат вылезал бы за поля вместе с жёлтой полосой.
        builder: (context, box) => _art(box.maxWidth.isFinite
            ? math.min(widget.size, box.maxWidth)
            : widget.size),
      );

  Widget _art(double edge) {
    final side = Size.square(edge);
    return SizedBox(
      width: edge,
      height: edge,
      child: RotationTransition(
        turns: _spin,
        child: Stack(
          alignment: Alignment.center,
          children: [
            // Небо. `RepaintBoundary` здесь — не гигиена, а смысл: как только
            // вступление доиграно, часы останавливаются, слой остаётся в
            // кэше, и оставшиеся полторы минуты он не стоит ничего.
            RepaintBoundary(
              child: AnimatedBuilder(
                animation: _intro,
                builder: (context, _) => CustomPaint(
                  size: side,
                  painter: _SkyPainter(Curves.easeInOut.transform(_intro.value)),
                ),
              ),
            ),
            AnimatedBuilder(
              animation: Listenable.merge([_intro, _pen, _life, _breath]),
              builder: (context, _) => CustomPaint(
                size: side,
                painter: _PenPainter(
                  // Пока идёт вступление, дугу ведёт оно; дальше — перо.
                  arc: _intro.isCompleted
                      ? 1 - Curves.easeInOut.transform(_pen.value)
                      : phase(Curves.easeInOut.transform(_intro.value), 0.62, 1),
                  life: _life.value,
                  breath: Curves.easeInOut.transform(_breath.value),
                  // Фигура системы въезжает во вторую половину вступления:
                  // сначала небо, потом то, что в нём пишут.
                  reveal: phase(Curves.easeInOut.transform(_intro.value), 0.5, 1),
                  // Звезда центра зажигается на своём месте в порядке макета,
                  // а не горит с нулевого кадра: она — часть рисунка, а не
                  // индикатор занятости.
                  core: phase(Curves.easeInOut.transform(_intro.value), 0.62, 0.78),
                  seed: widget.seed,
                  grain: widget.grain,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Постоянная часть рисунка главы — та самая, что в макете нарисована в поле
/// 260×260. Все радиусы отсюда: `u` переводит макет в текущий размер, а вот
/// толщина линии не масштабируется никогда — волосяная линия остаётся
/// волосяной на любом размере, иначе на большом полотне она станет жирной.
class _SkyPainter extends CustomPainter {
  const _SkyPainter(this.t);

  /// Ход вступления после кривой, 0…1.
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    if (t <= 0) return;
    final c = Offset(size.width / 2, size.height / 2);
    final u = size.width / 260;

    // Пунктирная внешняя орбита: r104, штрих «2 7», золото 0.18.
    _dashedArc(canvas, c, 104 * u,
        dash: 2 * u,
        gap: 7 * u,
        t: phase(t, 0, 0.42),
        paint: _stroke(AlmaPalette.gold, 0.18));
    // Две наклонные: rx104 ry52 под −18° и rx86 ry38 под 26°.
    _ellipse(canvas, c, 104 * u, 52 * u, -18, phase(t, 0.10, 0.58),
        _stroke(AlmaPalette.gold, 0.32));
    _ellipse(canvas, c, 86 * u, 38 * u, 26, phase(t, 0.20, 0.68),
        _stroke(AlmaPalette.gold, 0.24));
    // Круг r64 и внутреннее кольцо r26.
    _arc(canvas, c, 64 * u, phase(t, 0.32, 0.74),
        _stroke(AlmaPalette.gold, 0.14));
    _arc(canvas, c, 26 * u, phase(t, 0.46, 0.82),
        _stroke(AlmaPalette.goldBright, 0.35));
    // Три звезды садятся последними, в порядке макета.
    _spark(canvas, c + Offset(96, -28) * u, 2.4 * u, phase(t, 0.70, 0.88), 0.85);
    _spark(canvas, c + Offset(-78, 34) * u, 2.0 * u, phase(t, 0.76, 0.94), 0.60);
    _spark(canvas, c + Offset(38, 98) * u, 1.8 * u, phase(t, 0.82, 1.00), 0.50);
  }

  @override
  bool shouldRepaint(covariant _SkyPainter old) => old.t != t;
}

/// Живая часть: золотая дуга пера, фигура системы и дышащая звезда центра.
class _PenPainter extends CustomPainter {
  const _PenPainter({
    required this.arc,
    required this.life,
    required this.breath,
    required this.reveal,
    required this.core,
    required this.seed,
    required this.grain,
  });

  final double arc;
  final double life;
  final double breath;
  final double reveal;
  final double core;
  final int seed;
  final int grain;

  /// Дуга макета `M130 26 A104 104 0 0 1 226 168`: от верха по часовой на
  /// 111.6°, то есть 1.948 радиана.
  static const _sweep = 1.948;

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2);
    final u = size.width / 260;

    if (arc > 0) {
      canvas.drawArc(
        Rect.fromCircle(center: c, radius: 104 * u),
        -math.pi / 2,
        _sweep * arc,
        false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2
          ..strokeCap = StrokeCap.round
          ..color = AlmaPalette.goldBright.withValues(alpha: 0.55),
      );
    }

    if (reveal > 0) {
      // **Форма у каждой системы своя, а не одна с другим сдвигом.** Владелец
      // прошёл все восемь и сказал прямо: «практически одна и та же». Здесь
      // восемь разных ожиданий; общий у них только материал — золото, тонкая
      // линия и звёздная точка — и небо вокруг.
      //
      // **А внутри системы своя у каждой главы.** Семейство остаётся семейством
      // — натальная карта всегда кольца, транзиты всегда лучи, — но число
      // элементов, наклон, плотность и ход берутся из [grain]. Узнаваемость
      // системы при этом не страдает: меняется экземпляр, не род.
      // Размах фигуры — тоже примета главы, и самая заметная издалека: две
      // одинаковые по устройству фигуры разного размаха различаются раньше,
      // чем человек начнёт считать кольца. Первый экземпляр остаётся ровно
      // того размера, что был, — экраны без главы ничего не заметят. Потолок
      // держит фигуру внутри круга r64 из макета, за которым начинается небо.
      final r = size.width * 0.225 * const [1.0, 0.86, 1.1, 0.94][grain % 4];
      switch (seed % 8) {
        case 0:
          _orbits(canvas, c, r);
        case 1:
          _spiral(canvas, c, r);
        case 2:
          _pulse(canvas, c, r);
        case 3:
          _rays(canvas, c, r);
        case 4:
          _wave(canvas, c, r);
        case 5:
          _lattice(canvas, c, r);
        case 6:
          _comet(canvas, c, r);
        default:
          _constellation(canvas, c, r);
      }
    }

    // Звезда центра: r3 макета, вдох 1.04 по размеру и 0.92…1 по свету.
    if (core > 0) {
      canvas.drawCircle(
        c,
        3 * u * core * (1 + 0.04 * breath),
        Paint()
          ..color = AlmaPalette.starFill
              .withValues(alpha: (0.92 + 0.08 * breath) * core),
      );
    }
  }

  Paint get _line => Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = 1
    ..color = AlmaPalette.gold.withValues(alpha: 0.45 * reveal);

  Paint get _star =>
      Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.9 * reveal);

  /// Кольца, замыкающиеся одно за другим и снова расходящиеся.
  ///
  /// Семейство натальной карты — и самое нагруженное: шестнадцать глав. Пара
  /// «сколько колец» × «как они лежат» разведена так, что на шестнадцати
  /// подряд идущих зёрнах не повторяется ни разу: `2 + grain % 4` колец на
  /// `grain ~/ 4` посадку. Остальное — плотность, ход и место звезды — уже
  /// добавка к различию, а не его основа.
  void _orbits(Canvas canvas, Offset c, double r) {
    final rings = 2 + grain % 4;
    final look = (grain ~/ 4) % 4;
    // Нулевая посадка — круги: с неё начинаются экраны без главы вовсе, и там
    // обещаны «две орбиты, которые ещё не встретились», а не косой эллипс.
    final tilt = const [0.0, 26.0, -38.0, 62.0][look];
    final squash = const [1.0, 0.62, 0.78, 0.5][look];
    // Куда уходит внутреннее кольцо: доля радиуса, а не шаг, — иначе пять
    // колец с крупным шагом сходились бы в точку и рисунок терял середину.
    final spread = const [0.46, 0.64, 0.82][grain % 3];
    final dir = grain.isOdd ? -1.0 : 1.0;

    canvas.save();
    canvas.translate(c.dx, c.dy);
    canvas.rotate(tilt * math.pi / 180);
    for (var i = 0; i < rings; i++) {
      final t = phase(life, i * 0.1, 0.6 + i * 0.1);
      if (t <= 0) continue;
      final rad = r * (1 - spread * i / (rings - 1));
      canvas.drawArc(
          Rect.fromCenter(
              center: Offset.zero, width: rad * 2, height: rad * 2 * squash),
          -math.pi / 2,
          dir * 2 * math.pi * t,
          false,
          _line);
    }
    // Звезда садится на внешнее кольцо — в своём месте по кругу, а не всегда
    // наверху: у соседних глав это заметнее, чем ещё один оттенок наклона.
    final seat = -math.pi / 2 + (grain % 5) * 2 * math.pi / 5;
    canvas.drawCircle(
        Offset(math.cos(seat) * r, math.sin(seat) * r * squash), 3.5, _star);
    canvas.restore();
  }

  /// Спираль, наматывающаяся к центру.
  void _spiral(Canvas canvas, Offset c, double r) {
    // Витки, направление закрутки и глубина — три вещи, которые видно на
    // застывшем кадре, а не только в движении.
    final turns = 2.5 + (grain % 5) * 0.6;
    final hand = grain.isOdd ? -1.0 : 1.0;
    final depth = 0.55 + (grain % 3) * 0.14;
    final path = Path();
    final steps = (200 * life).round();
    for (var i = 0; i <= steps; i++) {
      final t = i / 200;
      final a = hand * t * turns * 2 * math.pi - math.pi / 2;
      final rad = r * (1 - t * depth);
      final p = c + Offset(math.cos(a) * rad, math.sin(a) * rad);
      i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(path, _line);
  }

  /// Круги, расходящиеся от центра, как круги на воде.
  void _pulse(Canvas canvas, Offset c, double r) {
    final waves = 3 + grain % 3;
    final squash = const [1.0, 0.68, 0.86][grain % 3];
    // Нечётные главы сжимаются к центру, а не расходятся: то же движение,
    // прочитанное наоборот, — и на кадре видно по расстановке колец.
    final inward = grain.isOdd;
    for (var i = 0; i < waves; i++) {
      final t = (life + i / waves) % 1.0;
      final k = inward ? 1 - t : t;
      canvas.drawOval(
        Rect.fromCenter(
            center: c, width: 2 * r * k, height: 2 * r * k * squash),
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = AlmaPalette.gold.withValues(alpha: 0.5 * (1 - t) * reveal),
      );
    }
  }

  /// Лучи, зажигающиеся по кругу и гаснущие следом.
  void _rays(Canvas canvas, Offset c, double r) {
    final count = 8 + (grain % 4) * 4;
    final root = 0.25 + (grain % 3) * 0.14;
    final dir = grain.isOdd ? -1.0 : 1.0;
    // Сколько круга горит разом. Нижняя граница не случайна: при доле меньше
    // трети от восьми лучей горит один, и рисунок читается не как венец, а как
    // случайная чёрточка у центра — то есть как сбой.
    final lit = 0.42 + (grain % 3) * 0.2;
    for (var i = 0; i < count; i++) {
      final own = (dir * life * count - i) % count / count;
      final k = own > 0 && own < lit ? 1 - own / lit : (own == 0 ? 1.0 : 0.0);
      if (k <= 0) continue;
      final a = i * 2 * math.pi / count - math.pi / 2;
      canvas.drawLine(
        c + Offset(math.cos(a), math.sin(a)) * r * root,
        c + Offset(math.cos(a), math.sin(a)) * r,
        Paint()
          ..strokeWidth = 1.2
          ..color = AlmaPalette.gold.withValues(alpha: 0.55 * k * reveal),
      );
    }
  }

  /// Волна, бегущая слева направо, — для карты линий.
  void _wave(Canvas canvas, Offset c, double r) {
    final rows = 2 + grain % 3;
    final ripples = 2 + grain % 4;
    final amp = 0.12 + (grain % 3) * 0.06;
    final drift = grain.isOdd ? -1.0 : 1.0;
    for (var row = 0; row < rows; row++) {
      final path = Path();
      // Строки держатся середины поля: при чётном их числе центральной нет, и
      // рисунок иначе сползал бы вверх от центра неба.
      final y = c.dy + (row - (rows - 1) / 2) * r * 0.55;
      for (var x = -r; x <= r; x += 4) {
        final t = (x + r) / (2 * r);
        final dy = math.sin(
                (t * ripples + drift * life * 2 + row * 0.4) * math.pi * 2) *
            r *
            amp;
        x == -r ? path.moveTo(c.dx + x, y + dy) : path.lineTo(c.dx + x, y + dy);
      }
      canvas.drawPath(path, _line);
    }
  }

  /// Решётка, проявляющаяся клетками.
  void _lattice(Canvas canvas, Offset c, double r) {
    // Четыре главы совместимости — четыре разные решётки: своё число нитей и
    // свой поворот у каждой, чтобы соседние не читались как одна с опечаткой.
    final n = 3 + grain % 4;
    final tilt = const [0.0, 45.0, 20.0, -20.0][grain % 4];
    final step = grain.isOdd ? 0.12 : 0.06;
    canvas.save();
    canvas.translate(c.dx, c.dy);
    canvas.rotate(tilt * math.pi / 180);
    for (var i = 0; i <= n; i++) {
      final t = phase(life, i * step, 0.5 + i * step);
      if (t <= 0) continue;
      final o = (i / n - 0.5) * 2 * r;
      canvas.drawLine(
          Offset(o, -r), Offset(o, -r + 2 * r * t), _line);
      canvas.drawLine(
          Offset(-r, o), Offset(-r + 2 * r * t, o), _line);
    }
    canvas.restore();
  }

  /// Комета, обходящая круг.
  void _comet(Canvas canvas, Offset c, double r) {
    final tail = 10 + (grain % 4) * 6;
    final squash = const [1.0, 0.6, 0.8][grain % 3];
    final tilt = const [0.0, -22.0, 30.0][grain % 3];
    // Вторая комета идёт напротив первой: не «то же самое чуть быстрее», а
    // другой рисунок пути.
    final riders = 1 + grain % 2;
    canvas.save();
    canvas.translate(c.dx, c.dy);
    canvas.rotate(tilt * math.pi / 180);
    canvas.drawOval(
      Rect.fromCenter(center: Offset.zero, width: 2 * r, height: 2 * r * squash),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AlmaPalette.gold.withValues(alpha: 0.18 * reveal),
    );
    for (var rider = 0; rider < riders; rider++) {
      for (var i = 0; i < tail; i++) {
        final t = (life - i * 0.012 + rider / riders) % 1.0;
        final a = t * 2 * math.pi - math.pi / 2;
        canvas.drawCircle(
          Offset(math.cos(a) * r, math.sin(a) * r * squash),
          3.2 * (1 - i / tail),
          Paint()
            ..color = AlmaPalette.starFill
                .withValues(alpha: 0.9 * (1 - i / tail) * reveal),
        );
      }
    }
    canvas.restore();
  }

  /// Созвездие: точки садятся и связываются нитями.
  void _constellation(Canvas canvas, Offset c, double r) {
    final seats = 5 + grain % 4;
    final turn = (grain % 5) * 0.26;
    final dive = 0.5 + (grain % 3) * 0.14;
    Offset at(int i) {
      // Неравные промежутки — созвездие, а не циферблат; сдвиг зависит от
      // зерна, поэтому у соседних глав рисунок другой не только числом точек.
      final a = -math.pi / 2 +
          turn +
          (i + 0.18 * ((i * (grain + 1)) % 3)) * 2 * math.pi / seats;
      return c + Offset(math.cos(a), math.sin(a)) * (i.isEven ? r : r * dive);
    }

    for (var i = 0; i < seats; i++) {
      final lit = phase(life, i * 0.09, 0.4 + i * 0.09);
      if (lit <= 0) continue;
      if (i > 0) {
        final grown = phase(life, 0.05 + i * 0.09, 0.45 + i * 0.09);
        final a = at(i - 1);
        final b = at(i);
        canvas.drawLine(
            a,
            Offset(a.dx + (b.dx - a.dx) * grown, a.dy + (b.dy - a.dy) * grown),
            _line);
      }
      canvas.drawCircle(at(i), 4 * lit, _star);
    }
  }

  @override
  bool shouldRepaint(covariant _PenPainter old) =>
      old.arc != arc ||
      old.life != life ||
      old.breath != breath ||
      old.reveal != reveal ||
      old.core != core ||
      old.seed != seed ||
      old.grain != grain;
}

// ── s28 · заготовка колеса, пока считается система ──────────────────────────

/// Колесо, которое чертит себя, пока система ещё не пришла с сервера.
///
/// Экран s28 макета: пока грузится оглавление, на месте будущей диаграммы
/// стоит не пустота и не спиннер, а кольцо в масштабе настоящего колеса —
/// круг r140, дуга, которая пишется и стирается за 3.2 с, два пунктирных
/// кольца, идущих в разные стороны за 40 и 26 секунд, четыре засечки по
/// сторонам света и дышащая точка центра.
///
/// Оно намеренно не похоже на натальную карту в деталях: рисовать похожее на
/// карту, пока карты нет, значило бы показать выдуманные позиции.
class ChartPlaceholder extends StatefulWidget {
  const ChartPlaceholder({super.key, this.size = 300});

  final double size;

  @override
  State<ChartPlaceholder> createState() => _ChartPlaceholderState();
}

class _ChartPlaceholderState extends State<ChartPlaceholder>
    with TickerProviderStateMixin {
  /// `draw660 3.2s ease-in-out infinite alternate` — дуга пишется и стирается.
  late final AnimationController _trace = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 3200),
  );

  /// `spinSlow 40s` и `spinSlow 26s reverse`.
  late final AnimationController _outer =
      AnimationController(vsync: this, duration: const Duration(seconds: 40));
  late final AnimationController _inner =
      AnimationController(vsync: this, duration: const Duration(seconds: 26));

  /// `breathe 2.4s` — половина круга 1.2 с.
  late final AnimationController _breath = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (still) {
        // В покое кольцо остаётся дочерченным: половина дуги — это не «сломано»,
        // это ожидание, но замершее на нуле оно выглядело бы обрывом.
        _trace.value = 1;
        return;
      }
      _trace.repeat(reverse: true);
      _outer.repeat();
      _inner.repeat();
      _breath.repeat(reverse: true);
    });
  }

  @override
  void dispose() {
    _trace.dispose();
    _outer.dispose();
    _inner.dispose();
    _breath.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, box) => _wheel(box.maxWidth.isFinite
            ? math.min(widget.size, box.maxWidth)
            : widget.size),
      );

  Widget _wheel(double edge) {
    final side = Size.square(edge);
    // Макет нарисован в поле 300×300 — все радиусы отсюда.
    final u = edge / 300;
    return SizedBox(
      width: edge,
      height: edge,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Обод и засечки не меняются никогда — рисуются один раз в свой слой.
          RepaintBoundary(
            child: CustomPaint(size: side, painter: _RimPainter(u)),
          ),
          RotationTransition(
            turns: _outer,
            child: RepaintBoundary(
              child: CustomPaint(
                size: side,
                painter: _DashRingPainter(
                    radius: 112 * u, dash: 3 * u, gap: 9 * u, alpha: 0.22),
              ),
            ),
          ),
          RotationTransition(
            turns: ReverseAnimation(_inner),
            child: RepaintBoundary(
              child: CustomPaint(
                size: side,
                painter: _DashRingPainter(
                    radius: 58 * u, dash: 2 * u, gap: 8 * u, alpha: 0.18),
              ),
            ),
          ),
          AnimatedBuilder(
            animation: Listenable.merge([_trace, _breath]),
            builder: (context, _) => CustomPaint(
              size: side,
              painter: _TracePainter(
                t: Curves.easeInOut.transform(_trace.value),
                breath: Curves.easeInOut.transform(_breath.value),
                u: u,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Обод r140 и четыре засечки по сторонам света — статика макета.
class _RimPainter extends CustomPainter {
  const _RimPainter(this.u);

  final double u;

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2);
    canvas.drawCircle(c, 140 * u, _stroke(AlmaPalette.gold, 0.4));
    final tick = _stroke(AlmaPalette.gold, 0.16);
    for (var i = 0; i < 4; i++) {
      final a = i * math.pi / 2 - math.pi / 2;
      final d = Offset(math.cos(a), math.sin(a));
      canvas.drawLine(c + d * (136 * u), c + d * (128 * u), tick);
    }
  }

  @override
  bool shouldRepaint(covariant _RimPainter old) => old.u != u;
}

/// Пунктирное кольцо, которое крутится целиком.
class _DashRingPainter extends CustomPainter {
  const _DashRingPainter({
    required this.radius,
    required this.dash,
    required this.gap,
    required this.alpha,
  });

  final double radius;
  final double dash;
  final double gap;
  final double alpha;

  @override
  void paint(Canvas canvas, Size size) {
    _dashedArc(
      canvas,
      Offset(size.width / 2, size.height / 2),
      radius,
      dash: dash,
      gap: gap,
      t: 1,
      paint: _stroke(AlmaPalette.gold, alpha),
    );
  }

  @override
  bool shouldRepaint(covariant _DashRingPainter old) =>
      old.radius != radius ||
      old.dash != dash ||
      old.gap != gap ||
      old.alpha != alpha;
}

/// Дуга, которая пишет колесо, и звезда центра.
class _TracePainter extends CustomPainter {
  const _TracePainter({required this.t, required this.breath, required this.u});

  final double t;
  final double breath;
  final double u;

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2);
    if (t > 0) {
      canvas.drawArc(
        Rect.fromCircle(center: c, radius: 140 * u),
        -math.pi / 2,
        2 * math.pi * t,
        false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2
          ..strokeCap = StrokeCap.round
          ..color = AlmaPalette.goldBright.withValues(alpha: 0.65),
      );
    }
    canvas.drawCircle(
      c,
      2.6 * u * (1 + 0.04 * breath),
      Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.8 + 0.2 * breath),
    );
  }

  @override
  bool shouldRepaint(covariant _TracePainter old) =>
      old.t != t || old.breath != breath || old.u != u;
}

// ── s27 · точка присутствия и мерцающие полосы ──────────────────────────────

/// Тёплая точка света — присутствие Alma, у того размера, где кольцо снято.
///
/// Дышит по макету: `breathe 2.6s ease-in-out infinite`, масштаб 1…1.04,
/// свет 0.92…1. Неподвижная точка рядом со строкой «читаю твою карту» была
/// единственным, что человек видел, — и она не показывала, что что-то идёт.
class WaitingDot extends StatefulWidget {
  const WaitingDot({super.key, this.size = 24});

  final double size;

  @override
  State<WaitingDot> createState() => _WaitingDotState();
}

class _WaitingDotState extends State<WaitingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _clock = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1300),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (!still) _clock.repeat(reverse: true);
    });
  }

  @override
  void dispose() {
    _clock.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dot = Container(
      width: widget.size,
      height: widget.size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(colors: [
          AlmaPalette.starFill,
          AlmaPalette.gold.withValues(alpha: 0.5),
          AlmaPalette.gold.withValues(alpha: 0.0),
        ], stops: const [0.0, 0.45, 1.0]),
      ),
    );
    return AnimatedBuilder(
      animation: _clock,
      builder: (context, child) {
        final t = Curves.easeInOut.transform(_clock.value);
        return Transform.scale(
          scale: 1 + 0.04 * t,
          child: Opacity(opacity: 0.92 + 0.08 * t, child: child),
        );
      },
      child: dot,
    );
  }
}

/// Насколько густа полоса-заготовка. Числа — прозрачности из макета, по паре
/// на тон: покой и блик.
enum WaitingTone {
  /// Заголовок строки.
  strong(0.06, 0.14),

  /// Строка текста.
  text(0.05, 0.13),

  /// Подпись под строкой.
  faint(0.04, 0.10),

  /// Золотая метка: римская цифра главы, название области дня.
  gold(0.14, 0.30);

  const WaitingTone(this.base, this.glow);

  final double base;
  final double glow;
}

/// Полоса на месте будущей строки, по которой идёт блик.
///
/// `shimmer 1.9s linear infinite` из макета: полотно блика шириной 440 точек
/// проезжает от −220 до +220, светлая полоса занимает его середину (25…75 %).
/// Задержка сдвигает фазу — строки загораются не разом, а сверху вниз, как
/// читается настоящий абзац.
///
/// Это заготовка, а не данные: она не показывает ни длины будущего текста, ни
/// его наличия. Единственное, что она обещает, — что место под текст есть.
class WaitingBar extends StatefulWidget {
  const WaitingBar({
    super.key,
    required this.height,
    this.width,
    this.widthFactor,
    this.tone = WaitingTone.text,
    this.delay = Duration.zero,
  });

  final double height;

  /// Ширина в точках; `null` — во всю доступную.
  final double? width;

  /// Доля доступной ширины. Взаимоисключима с [width].
  final double? widthFactor;

  final WaitingTone tone;
  final Duration delay;

  @override
  State<WaitingBar> createState() => _WaitingBarState();
}

class _WaitingBarState extends State<WaitingBar>
    with SingleTickerProviderStateMixin {
  static const _period = Duration(milliseconds: 1900);

  late final AnimationController _clock =
      AnimationController(vsync: this, duration: _period);

  /// Задержку макета держим фазой, а не отложенным стартом: часы у всех полос
  /// одни и те же, и после первого круга ни одна не убежит от соседки.
  late final double _shift =
      -widget.delay.inMilliseconds / _period.inMilliseconds;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      // В покое блик стоит посреди полосы: полоса видна, движения нет.
      still ? _clock.value = 0.5 : _clock.repeat();
    });
  }

  @override
  void dispose() {
    _clock.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bar = SizedBox(
      height: widget.height,
      width: widget.width ?? double.infinity,
      child: LayoutBuilder(
        builder: (context, box) {
          final w = box.maxWidth.isFinite && box.maxWidth > 0 ? box.maxWidth : 320.0;
          return AnimatedBuilder(
            animation: _clock,
            builder: (context, _) => DecoratedBox(
              decoration: BoxDecoration(
                // Скругление макета: r8 при h15, r7 при h13/14, r6 при h11.
                borderRadius: BorderRadius.circular((widget.height + 1) / 2),
                gradient: _sweep(w, (_clock.value + _shift) % 1.0),
              ),
            ),
          );
        },
      ),
    );
    final factor = widget.widthFactor;
    if (factor == null) return bar;
    return FractionallySizedBox(
      alignment: Alignment.centerLeft,
      widthFactor: factor,
      child: bar,
    );
  }

  LinearGradient _sweep(double width, double t) {
    final base = AlmaPalette.body.withValues(alpha: widget.tone.base);
    final glow = AlmaPalette.body.withValues(alpha: widget.tone.glow);
    final gold = widget.tone == WaitingTone.gold;
    // Полотно 440 точек едет от −220 до +220 — координаты макета переводятся
    // в доли ширины полосы, потому что полосы у нас разной длины.
    final left = -220 + 440 * t;
    return LinearGradient(
      begin: Alignment(2 * left / width - 1, 0),
      end: Alignment(2 * (left + 440) / width - 1, 0),
      colors: gold
          ? [
              AlmaPalette.gold.withValues(alpha: widget.tone.base),
              AlmaPalette.gold.withValues(alpha: widget.tone.glow),
              AlmaPalette.gold.withValues(alpha: widget.tone.base),
            ]
          : [base, glow, base],
      stops: const [0.25, 0.5, 0.75],
    );
  }
}

// ── общая кисть ─────────────────────────────────────────────────────────────

/// Волосяная линия. Толщина не масштабируется вместе с полотном: волосяная
/// линия — решение дизайна, а не доля радиуса.
Paint _stroke(Color color, double alpha) => Paint()
  ..style = PaintingStyle.stroke
  ..strokeWidth = 1
  ..color = color.withValues(alpha: alpha);

/// Дуга окружности, чертящая себя от верхней точки по часовой.
void _arc(Canvas canvas, Offset c, double radius, double t, Paint paint) {
  if (t <= 0) return;
  canvas.drawArc(Rect.fromCircle(center: c, radius: radius), -math.pi / 2,
      2 * math.pi * t, false, paint);
}

/// То же для наклонного эллипса: наклон в градусах, как в макете.
void _ellipse(Canvas canvas, Offset c, double rx, double ry, double degrees,
    double t, Paint paint) {
  if (t <= 0) return;
  canvas.save();
  canvas.translate(c.dx, c.dy);
  canvas.rotate(degrees * math.pi / 180);
  canvas.drawArc(
      Rect.fromCenter(center: Offset.zero, width: rx * 2, height: ry * 2),
      -math.pi / 2,
      2 * math.pi * t,
      false,
      paint);
  canvas.restore();
}

/// Пунктирная дуга: штрихи `dash` через `gap`, разложенные по длине дуги.
void _dashedArc(
  Canvas canvas,
  Offset c,
  double radius, {
  required double dash,
  required double gap,
  required double t,
  required Paint paint,
}) {
  if (t <= 0 || radius <= 0) return;
  final rect = Rect.fromCircle(center: c, radius: radius);
  final drawn = 2 * math.pi * radius * t;
  final step = dash + gap;
  for (var s = 0.0; s < drawn; s += step) {
    final end = math.min(s + dash, drawn);
    canvas.drawArc(
        rect, s / radius - math.pi / 2, (end - s) / radius, false, paint);
  }
}

/// Звезда, которая зажигается: растёт от нуля до своего радиуса.
void _spark(Canvas canvas, Offset at, double radius, double t, double alpha) {
  if (t <= 0) return;
  canvas.drawCircle(at, radius * t,
      Paint()..color = AlmaPalette.starFill.withValues(alpha: alpha * t));
}
