import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../design/palette.dart';
import '../design/sky/night_sky.dart';
import '../design/typography.dart';
import '../l10n/alma_l10n.dart';

/// Первые секунды приложения — S12 «Launch» дизайн-проекта.
///
/// **Здесь нет ничего, кроме того, что есть в макете.** До этой правки экран
/// рисовал звёздный чертёж: девять узлов, три ветви линий и две кометы,
/// стягивавшиеся в знак. В S12 такого нет — там знак, слово, волосяная линия и
/// одна строка внизу. Чертёж был сочинён, а не портирован (в самом макете
/// разметка карты осталась, но погашена `display:none`), и владелец его снял.
///
/// Пять элементов S12, снятые с эталона на 402×874:
///
/// * ореол 130×130 с центром на знаке, `breathe` 4 с;
/// * знак 56×56 на `y=370`;
/// * «ALMA» 84×16.5 на `y=456`, разрядка 9;
/// * волосяная линия 84×1 на `y=503`: заполняется за 3,4 с (`fill84`), и по ней
///   бежит блик (`shimmerX`, 2,2 с);
/// * «Written in the sky before you asked.» на `y=789`, `textShimmer` 4,4 с.
///
/// Колонка из первых четырёх отцентрована по экрану (56 + 30 + 16.5 + 30 + 1 =
/// 133.5; на 874 это и даёт знак ровно на 370) — так экран переживёт телефон
/// другой высоты, чего абсолютные координаты не умеют.
///
/// **Заставка не разыгрывает спектакль прихода.** В макете все четыре движения
/// — бесконечные петли, идущие с первого кадра, а не каскад с фазами. Каскад
/// был частью того же сочинения.
///
/// **Уход требует двух условий сразу**: сессия готова И прошло положенное
/// время. На нативе первая версия читала «готово» из замыкания, захватившего
/// значение на момент создания задачи, — заставка не уходила вовсе. Здесь
/// решение принимается снаружи, в [_settle], на каждое изменение обоих.
class LaunchScreen extends StatefulWidget {
  const LaunchScreen({super.key, required this.ready, required this.onDone});

  /// Знает ли уже приложение, кто перед ним.
  final bool ready;

  final VoidCallback onDone;

  @override
  State<LaunchScreen> createState() => _LaunchScreenState();
}

class _LaunchScreenState extends State<LaunchScreen>
    with SingleTickerProviderStateMixin {
  /// 3,4 секунды — число с натива, и оно выросло с 2,8 не ради скорости: там
  /// чинили плотность, а не длительность. Столько же длится `fill84`, поэтому
  /// линия успевает налиться ровно один раз — она и есть счётчик ожидания.
  static const _dwell = 3.4;

  /// Секунды с первого кадра — единственные часы экрана. Каждая петля берёт из
  /// них свою фазу остатком от своего периода: ровно так это устроено в CSS, и
  /// четыре независимых контроллера здесь были бы четырьмя способами разойтись.
  final _seconds = ValueNotifier<double>(0);

  /// Заводится в [initState], а не полем-`late`: поле, которого никто не
  /// читает в `build`, не создаётся вовсе — часы бы не пошли, а `dispose`
  /// создал бы их в момент сноса дерева.
  Ticker? _clock;

  bool _dwelt = false;
  bool _handedOver = false;

  @override
  void initState() {
    super.initState();
    _clock = createTicker(_tick)..start();
  }

  void _tick(Duration elapsed) {
    final t = elapsed.inMicroseconds / Duration.microsecondsPerSecond;
    _seconds.value = t;
    if (!_dwelt && t >= _dwell) {
      _dwelt = true;
      _settle();
    }
  }

  @override
  void didUpdateWidget(LaunchScreen old) {
    super.didUpdateWidget(old);
    if (widget.ready != old.ready) _settle();
  }

  @override
  void dispose() {
    _clock?.dispose();
    _seconds.dispose();
    super.dispose();
  }

  void _settle() {
    if (_handedOver || !_dwelt || !widget.ready) return;
    _handedOver = true;
    widget.onDone();
  }

  /// Фаза петли периода [period] секунд: 0 → 1 и снова 0, как `infinite` в CSS.
  double _loop(double t, double period) => (t % period) / period;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    // Сокращённое движение — не «пропустить заставку»: убрать её целиком
    // значило бы вернуть ту самую вспышку, ради которой она написана. Рисуется
    // тот же кадр, только петли стоят.
    final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    // **Своя material-поверхность.** Без неё Flutter рисует «ALMA» жёлтой с
    // двойным подчёркиванием — тот же артефакт, что был на витрине: экран
    // возвращается из `home` напрямую и `Scaffold` над собой не имеет.
    return Semantics(
      label: l.stateLoadingShort,
      child: Material(
        color: AlmaPalette.night,
        child: Stack(
          // Без `expand` стопка съёжилась бы по колонке в 84 точки шириной:
          // единственный неспозиционированный ребёнок здесь — содержимое, и
          // именно он задал бы размер и небу под собой.
          fit: StackFit.expand,
          children: [
            // Небо кабинета, а не церемонии: у церемонии есть комета, а в S12
            // через кадр летящего света нет — как нет и чертежа, который её
            // сюда когда-то привёл.
            const Positioned.fill(
              child: NightSky(
                mood: SkyMood.cabinet,
                seed: 0x414C4D41,
                child: SizedBox.expand(),
              ),
            ),
            AnimatedBuilder(
              animation: _seconds,
              builder: (context, _) {
                final t = _seconds.value;
                return Stack(
                  alignment: Alignment.center,
                  children: [
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _Sign(breathe: still ? 0 : _loop(t, 4.0)),
                        const SizedBox(height: 30),
                        // Поля слева здесь нет, хотя в макете стоит
                        // `padding-left:9px`: там оно гасит разрядку, которую
                        // CSS дописывает и после последней буквы. Flutter её не
                        // дописывает, и то же поле уводило слово вправо на 4,5
                        // точки — на снимке с симулятора «ALMA» стояла центром
                        // на 205,5 вместо 201.
                        Text(
                          'ALMA',
                          style: AlmaType.meta.copyWith(
                            fontSize: 14,
                            // 16.5 при кегле 14 — строка Golos Text при
                            // `line-height:normal`; от неё зависит высота всей
                            // колонки, то есть и место знака на экране.
                            height: 16.5 / 14,
                            letterSpacing: 9,
                            color: AlmaPalette.inkLight.withValues(alpha: 0.95),
                          ),
                        ),
                        const SizedBox(height: 30),
                        CustomPaint(
                          size: const Size(84, 1),
                          painter: _Hairline(
                            fill: still
                                ? 1
                                : Curves.easeOut.transform(_loop(t, _dwell)),
                            shimmer: _loop(t, 2.2),
                            still: still,
                          ),
                        ),
                      ],
                    ),
                    // **Обещание — внизу, и это единственная фраза заставки.**
                    //
                    // В эталоне оно на `y=789` из 874, то есть у самого низа, а
                    // не под знаком: знак называет продукт, эта строка объясняет,
                    // о чём он, и читается уже после.
                    Positioned(
                      left: 0,
                      right: 0,
                      bottom: 64,
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 30),
                        // `Center` нужен, чтобы блик бежал по ширине строки, а
                        // не по ширине экрана: в макете фон-градиент лежит на
                        // строчном `<span>`, обнимающем текст.
                        child: Center(
                          child: ShaderMask(
                            blendMode: BlendMode.srcIn,
                            shaderCallback: (bounds) =>
                                _taglineShader(bounds, still ? -1 : t),
                            child: Text(
                              l.splashTagline,
                              textAlign: TextAlign.center,
                              style: AlmaType.voice.copyWith(
                                fontSize: 15.5,
                                height: 21 / 15.5,
                                // Цвет съест маска; важна только непрозрачность.
                                color: const Color(0xFFFFFFFF),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  /// Блик, бегущий по строке. В макете это `background-size:220%` и позиция,
  /// едущая от 120 % до −120 % за 4,4 с; в долях ширины строки это значит, что
  /// картинка вдвое шире текста проезжает от −1.44 до +1.44 его ширины.
  ///
  /// [t] < 0 — «меньше движения»: блик стоит посреди строки.
  Shader _taglineShader(Rect bounds, double t) {
    final w = bounds.width;
    final dx = t < 0 ? -0.6 * w : -1.44 * w + 2.88 * w * _loop(t, 4.4);
    return LinearGradient(
      colors: [
        AlmaPalette.body.withValues(alpha: 0.35),
        AlmaPalette.starFill,
        AlmaPalette.body.withValues(alpha: 0.35),
      ],
    ).createShader(
      Rect.fromLTWH(bounds.left + dx, bounds.top, w * 2.2, bounds.height),
    );
  }
}

/// Знак Alma в дышащем ореоле — первые два элемента S12.
class _Sign extends StatelessWidget {
  const _Sign({required this.breathe});

  /// Фаза петли `breathe`, 0 → 1 за 4 секунды.
  final double breathe;

  @override
  Widget build(BuildContext context) {
    // 0%,100% → scale(1) opacity .92; 50% → scale(1.04) opacity 1. Между
    // кадрами CSS ведёт `ease-in-out`, поэтому треугольная волна не годится.
    final k = Curves.easeInOut
        .transform(breathe < 0.5 ? breathe * 2 : (1 - breathe) * 2);
    return SizedBox.square(
      dimension: 56,
      // Ореол вдвое шире знака и вылезает за коробку колонки — как
      // `position:absolute` в макете, где он тоже не занимает места.
      child: Stack(
        clipBehavior: Clip.none,
        alignment: Alignment.center,
        children: [
          Positioned(
            left: (56 - 130) / 2,
            top: (56 - 130) / 2,
            width: 130,
            height: 130,
            child: Opacity(
              opacity: 0.92 + 0.08 * k,
              child: Transform.scale(
                scale: 1 + 0.04 * k,
                child: const DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      // `radial-gradient(circle, …)` без указания края
                      // считает проценты от угла коробки, а не от её стороны:
                      // 100 % здесь — 65·√2, отсюда радиус 0.707, а не 0.5.
                      radius: 0.7071,
                      colors: [
                        Color(0x4DC9AE6B),
                        Color(0x14C9AE6B),
                        Color(0x00C9AE6B),
                      ],
                      stops: [0, 0.45, 0.70],
                    ),
                  ),
                ),
              ),
            ),
          ),
          const CustomPaint(size: Size(56, 56), painter: _Mark()),
        ],
      ),
    );
  }
}

/// Знак Alma — четырёхлучевая звезда, залитая золотым листом.
///
/// Ровно тот контур, что в макете (`viewBox 0 0 46 46`), а не «примерно такая
/// же звезда»: талия у нарисованной по памяти была 0.19 длинного луча вместо
/// 0.27, и знак выходил тоньше эталонного.
class _Mark extends CustomPainter {
  const _Mark();

  static const _side = 46.0;

  static final _path = Path()
    ..moveTo(46, 23)
    ..lineTo(27.4, 27.4)
    ..lineTo(23, 46)
    ..lineTo(18.6, 27.4)
    ..lineTo(0, 23)
    ..lineTo(18.6, 18.6)
    ..lineTo(23, 0)
    ..lineTo(27.4, 18.6)
    ..close();

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / _side, size.height / _side);
    canvas.drawPath(
      _path,
      Paint()
        ..shader = AlmaGradient.goldLeaf
            .createShader(const Rect.fromLTWH(0, 0, _side, _side)),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _Mark old) => false;
}

/// Волосяная линия: самая тихая полоса прогресса, какая бывает. Дорожка,
/// наливающаяся жила и блик, пробегающий поперёк.
class _Hairline extends CustomPainter {
  const _Hairline({
    required this.fill,
    required this.shimmer,
    required this.still,
  });

  /// Доля залитой дорожки, 0 → 1 за 3,4 с.
  final double fill;

  /// Фаза блика, 0 → 1 за 2,2 с.
  final double shimmer;

  final bool still;

  static const _track = 84.0;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(
      const Rect.fromLTWH(0, 0, _track, 1),
      Paint()..color = AlmaPalette.gold.withValues(alpha: 0.16),
    );
    canvas.drawRect(
      Rect.fromLTWH(0, 0, _track * fill, 1),
      Paint()..color = AlmaPalette.goldBright.withValues(alpha: 0.75),
    );
    if (still) return;
    // Блик шире линии на пиксель сверху и снизу и едет от −60 до 100 — то
    // есть входит и выходит за пределы дорожки, а не мигает на месте.
    // Отсечка держит его в границах, как это делает фон в макете.
    canvas.save();
    canvas.clipRect(const Rect.fromLTWH(0, -1, _track, 3));
    final band = Rect.fromLTWH(-60 + 160 * shimmer, -1, 56, 3);
    canvas.drawRect(
      band,
      Paint()
        ..shader = LinearGradient(
          colors: [
            AlmaPalette.starFill.withValues(alpha: 0),
            AlmaPalette.starFill.withValues(alpha: 0.8),
            AlmaPalette.starFill.withValues(alpha: 0),
          ],
        ).createShader(band),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _Hairline old) =>
      old.fill != fill || old.shimmer != shimmer || old.still != still;
}
