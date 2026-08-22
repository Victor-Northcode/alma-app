import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/alma_l10n.dart';
import 'metrics.dart';
import 'palette.dart';
import 'typography.dart';

/// Четыре вкладки кабинета.
enum CabinetTab {
  today,
  systems,
  alma,
  settings;

  String title(L l) => switch (this) {
        CabinetTab.today => l.tabToday,
        CabinetTab.systems => l.tabSystems,
        CabinetTab.alma => l.tabAlma,
        CabinetTab.settings => l.tabSettings,
      };
}

/// Нижний бар: плита ночи на 94% поверх размытия, одна золотая волосяная линия
/// сверху, погашенные глифы на 50%.
///
/// Порт `mobile/ios/Alma/Navigation/CabinetTabBar.swift`.
class CabinetTabBar extends StatelessWidget {
  const CabinetTabBar({
    super.key,
    required this.current,
    required this.onSelect,
  });

  final CabinetTab current;
  final ValueChanged<CabinetTab> onSelect;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    return ValueListenableBuilder<bool>(
      valueListenable: readingNow,
      // **Пергаментным бар бывает только над главой, и решает это вкладка.**
      //
      // Признак чтения поднимает страница главы в своём `build`. Глава живёт в
      // навигаторе своей вкладки и `PageView` её не выбрасывает — значит она
      // перерисовывается и поднимает флаг снова, уже когда человек ушёл на
      // «Сегодня». Бар оставался светлым поверх ночи: снято на устройстве.
      //
      // Ночной каркас гасил флаг сам, но только когда строился, а живая
      // страница при смене вкладки не строится. Здесь условие не зависит от
      // того, кто и когда перерисовался: глава есть только в «Моих системах».
      builder: (context, reading, _) => _bar(
          context, l, bottomInset, reading && current == CabinetTab.systems),
    );
  }

  Widget _bar(BuildContext context, L l, double bottomInset, bool reading) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: DecoratedBox(
          // **Бар не блок, а край страницы.**
          //
          // Плотная заливка с золотой чертой поверху делала из него отдельную
          // панель, приклеенную к низу каждого экрана — «как будто отделён, а
          // нужно лаконичнее». Заливка стала прозрачной к верху и уходит в
          // страницу, черты нет вовсе: размытие держит подписи читаемыми над
          // любым текстом, а край растворяется.
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: reading
                  ? [
                      AlmaPalette.parchmentB.withValues(alpha: 0),
                      AlmaPalette.parchmentB.withValues(alpha: 0.90),
                      AlmaPalette.parchmentB.withValues(alpha: 0.96),
                    ]
                  : [
                      AlmaPalette.night850.withValues(alpha: 0),
                      AlmaPalette.night850.withValues(alpha: 0.90),
                      AlmaPalette.night850.withValues(alpha: 0.96),
                    ],
              stops: const [0, 0.30, 1],
            ),
          ),
          // **Завеса выше самого бара, и это лечит «срезанную строку».**
          //
          // Градиент начинался прозрачным ровно по верхней кромке подписей и
          // за 55% высоты доходил до плотного: строка списка, попавшая в эти
          // полсотни точек, оказывалась разрезанной пополам — сверху видна,
          // снизу нет. Читалось поломкой, а не глубиной.
          //
          // Растворение осталось, но плотность набирается втрое быстрее: за
          // первые 30% высоты вместо 55%. Верхние двадцать точек — по-прежнему
          // мягкий переход, дальше подписи стоят на своей земле, и строка под
          // ними уходит в ночь целиком, а не пополам.
          child: Padding(
            padding: EdgeInsets.only(bottom: bottomInset),
            child: SizedBox(
              height: AlmaMetrics.tabBarHeight,
              child: Row(
                children: [
                  for (final tab in CabinetTab.values)
                    Expanded(
                      child: _TabButton(
                        tab: tab,
                        active: tab == current,
                        label: tab.title(l),
                        onTap: () => onSelect(tab),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Показан ли сейчас бар на вкладке Alma — и что его прогонит.
///
/// **Почему у Alma бара нет.** Решение владельца, а не забытая строка: беседа —
/// комната письма, внизу неё поле вопроса, и на этой одной вкладке композер
/// главнее переключения вкладок. На трёх остальных бар стоит всегда. Здесь он
/// приходит по зову и уходит сам.
///
/// **Почему это отдельная вещь, а не поле оболочки.** Позвать бар может только
/// [TabsGrabber] — он нарисован внизу экрана беседы; показывает бар оболочка.
/// Между ними `PageView` и несколько уровней дерева, и признак — вся связь
/// между ними. Здесь же и таймер: «уходит сам через три секунды» — свойство
/// самого состояния, а не чьей-то кнопки. Разложенный по обработчикам, он
/// однажды не завёлся бы в одном из них, и бар остался бы стоять поверх беседы
/// именно тем постоянным баром, ради ухода которого всё затеяно.
class TabsPeek extends ValueNotifier<bool> {
  TabsPeek() : super(false);

  /// Сколько бар ждёт, прежде чем уйти сам. Трёх секунд хватает прочесть
  /// четыре подписи и попасть пальцем в нужную; дольше — и он снова
  /// становится постоянным баром.
  static const idle = Duration(seconds: 3);

  /// Сколько нужно протянуть **сверх** порога распознавания, чтобы это
  /// считалось смахом. Восемь точек отделяют движение от дрожи пальца.
  ///
  /// **Почему расстояние, а не скорость на отпускании.** Первым и там и там
  /// стоял `onVerticalDragEnd` с `primaryVelocity`, и он молчал на всяком
  /// смахе, который не дотягивал до броска: Flutter считает жест броском
  /// только если последние двадцать замеров прошли больше 18 точек. Медленно
  /// и коротко поднятый палец — а именно так поднимают ручку, до которой
  /// сантиметр хода, — не вызывал ничего. Расстояние отвечает на любой смах и
  /// отвечает сразу, не дожидаясь, пока палец оторвут.
  ///
  /// Число одно на оба конца движения: зовут бар с грабера, прогоняют с
  /// самого бара, и разъехавшиеся пороги читались бы как «вниз он слушается
  /// хуже, чем вверх».
  static const pull = 8.0;

  Timer? _timer;

  void reveal() {
    value = true;
    _countdown();
  }

  void hide() {
    _timer?.cancel();
    _timer = null;
    value = false;
  }

  void toggle() => value ? hide() : reveal();

  /// Палец лёг на бар — отсчёт начинается заново. Уйти из-под руки — то же
  /// самое, что уйти не вовремя.
  void keepAwake() {
    if (value) _countdown();
  }

  void _countdown() {
    _timer?.cancel();
    _timer = Timer(idle, hide);
  }

  @override
  void dispose() {
    // Без этого таймер доживает до срабатывания и трогает `value` у мёртвого
    // уведомителя — падение в отладке через три секунды после ухода с экрана.
    _timer?.cancel();
    super.dispose();
  }
}

/// Ручка под композером: единственный способ позвать бар на вкладке Alma.
///
/// **Почему она живёт над домашним индикатором, а не у самой кромки.** Смах от
/// нижней кромки экрана принадлежит системе — это жест «домой», и ручка,
/// поставленная туда, спорила бы с ним за палец и проигрывала. Отступ на
/// индикатор экран беседы держит **под** грабером, а не под композером.
class TabsGrabber extends StatefulWidget {
  const TabsGrabber({super.key, required this.peek});

  final TabsPeek peek;

  @override
  State<TabsGrabber> createState() => _TabsGrabberState();
}

class _TabsGrabberState extends State<TabsGrabber> {
  /// Кегль подписи под ручкой — 9.5 по слову владельца.
  static const _captionSize = 9.5;

  /// Интерлиньяж подписи. Раньше на это число был отведён пустой `SizedBox` —
  /// резерв под ненаписанную строку; теперь высоту держит сама строка, и
  /// ручка стоит там же, где стояла.
  static const _captionHeight = 1.3;

  /// Сколько уже протянуто в текущем жесте; порог — [TabsPeek.pull].
  double _pulled = 0;

  @override
  Widget build(BuildContext context) {
    final caption = L.of(context).scrChatSwipeForTabs;

    return Semantics(
      button: true,
      // Подпись и голосовая метка — одна строка на двоих, и намеренно. Ручка
      // 30×3 не имеет ни формы, ни имени: VoiceOver называл её «кнопка», и
      // единственный способ позвать бар в чате был не найден на ощупь.
      label: caption,
      child: GestureDetector(
        // Вся полоса, а не одни три точки высоты: попасть пальцем в ручку
        // 30×3 невозможно, и незримое поле вокруг неё — это и есть кнопка.
        behavior: HitTestBehavior.opaque,
        onTap: () {
          HapticFeedback.selectionClick();
          widget.peek.toggle();
        },
        onVerticalDragStart: (_) => _pulled = 0,
        onVerticalDragUpdate: (details) {
          _pulled += details.primaryDelta ?? 0;
          if (_pulled <= -TabsPeek.pull && !widget.peek.value) {
            _pulled = 0;
            HapticFeedback.selectionClick();
            widget.peek.reveal();
          } else if (_pulled >= TabsPeek.pull && widget.peek.value) {
            _pulled = 0;
            widget.peek.hide();
          }
        },
        child: Padding(
          padding: const EdgeInsets.only(top: 8, bottom: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 30,
                height: 3,
                decoration: BoxDecoration(
                  // Тот же тон, что у погашенной подписи вкладки: грабер и
                  // есть бар в состоянии покоя, и говорить он должен тем же
                  // голосом, а не своей собственной прозрачностью.
                  color: AlmaPalette.muted3,
                  borderRadius: BorderRadius.circular(1.5),
                ),
              ),
              const SizedBox(height: 5),
              // Голосу эта строка уже отдана меткой выше, и второй раз читать
              // её вслух незачем: узел один, а текста в нём было бы два.
              ExcludeSemantics(
                child: Text(
                  caption,
                  // Одной строкой и с многоточием: подпись стоит между
                  // композером и домашним индикатором, и вторая строка здесь
                  // не помещается ни в один язык — она подняла бы ручку.
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  // Разрядка .6 и прозрачность .45 — с холста (S7): подпись
                  // тише погашенной ручки, потому что ручку ищут пальцем, а
                  // подпись читают один раз и запоминают жест.
                  style: AlmaType.meta.copyWith(
                    fontSize: _captionSize,
                    height: _captionHeight,
                    letterSpacing: 0.6,
                    color: AlmaPalette.body.withValues(alpha: 0.45),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.tab,
    required this.active,
    required this.label,
    required this.onTap,
  });

  final CabinetTab tab;
  final bool active;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    // На пергаменте золото читается, а бледно-серые подписи тонут: неактивные
    // становятся чернилами страницы.
    final reading = readingNow.value;
    final colour = active
        ? (reading ? AlmaPalette.goldDeep : AlmaPalette.gold)
        : (reading ? AlmaPalette.inkMuted : AlmaPalette.muted3);
    return Semantics(
      selected: active,
      button: true,
      label: label,
      child: InkResponse(
        onTap: onTap,
        highlightColor: Colors.transparent,
        splashColor: Colors.transparent,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SizedBox(
              width: 22,
              height: 22,
              child: CustomPaint(painter: _TabGlyph(tab: tab, active: active)),
            ),
            const SizedBox(height: 3),
            // Подпись обычного веса — активную выделяет золото, а не жир: крупная
            // жирная подпись делала бар тяжелее всего экрана. Размер поднят 10 → 11:
            // прежние 10pt равнялись на нативный бар, который эталоном больше не
            // считается (CLAUDE.md §2), и на телефоне читались мелко.
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 11, letterSpacing: 0.2, color: colour),
            ),
          ],
        ),
      ),
    );
  }
}

/// Четыре глифа, нарисованные путями.
///
/// **Не системные иконки.** Солнце, шестерёнка и сетка кругов — это иконки
/// любого приложения на телефоне, а солнце вдобавок сказало бы «погода». Это
/// глифы веб-приложения: маленькое солнце с четырьмя лучами для Сегодня, два
/// концентрических круга для восьми систем, собственная тёплая точка света для
/// Alma и знак настроек без шестерёнки — точка с шестью короткими штрихами.
class _TabGlyph extends CustomPainter {
  _TabGlyph({required this.tab, required this.active});

  final CabinetTab tab;
  final bool active;

  @override
  void paint(Canvas canvas, Size size) {
    final reading = readingNow.value;
    final colour = active
        ? (reading ? AlmaPalette.goldDeep : AlmaPalette.gold)
        : (reading ? AlmaPalette.inkMuted : AlmaPalette.body.withValues(alpha: 0.62));
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.25
      ..strokeCap = StrokeCap.round
      ..color = colour;
    final c = Offset(size.width / 2, size.height / 2);

    switch (tab) {
      case CabinetTab.alma:
        // Alma никогда не линия. Она — тёплая точка света, на том единственном
        // размере, где кольцо снимается.
        final glow = Paint()
          ..shader = RadialGradient(
            colors: [
              AlmaPalette.starFill.withValues(alpha: active ? 1.0 : 0.65),
              AlmaPalette.gold.withValues(alpha: active ? 0.5 : 0.3),
              const Color(0x00000000),
            ],
            stops: const [0.0, 0.45, 1.0],
          ).createShader(Rect.fromCircle(center: c, radius: size.width * 0.42));
        canvas.drawCircle(c, size.width * 0.42, glow);

      case CabinetTab.today:
        final r = size.width * 0.1667;
        canvas.drawCircle(c, r, stroke);
        for (var angle = 0.0; angle < 360; angle += 90) {
          final rad = angle * math.pi / 180;
          final inner = size.width * 0.34;
          final outer = size.width * 0.46;
          canvas.drawLine(
            c + Offset(math.cos(rad) * inner, math.sin(rad) * inner),
            c + Offset(math.cos(rad) * outer, math.sin(rad) * outer),
            stroke,
          );
        }

      case CabinetTab.systems:
        for (final r in [size.width * 0.375, size.width * 0.1333]) {
          canvas.drawCircle(c, r, stroke);
        }

      case CabinetTab.settings:
        canvas.drawCircle(c, size.width * 0.125, stroke);
        for (var angle = 30.0; angle < 360; angle += 60) {
          final rad = angle * math.pi / 180;
          final inner = size.width * 0.29;
          final outer = size.width * 0.42;
          canvas.drawLine(
            c + Offset(math.cos(rad) * inner, math.sin(rad) * inner),
            c + Offset(math.cos(rad) * outer, math.sin(rad) * outer),
            stroke,
          );
        }
    }
  }

  @override
  bool shouldRepaint(covariant _TabGlyph old) => old.active != active || old.tab != tab;
}
