import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../l10n/alma_l10n.dart';
import '../screens/all_alma_sheet.dart';
import 'gold_texture.dart';
import 'metrics.dart';
import 'palette.dart';
import 'typography.dart';

/// Пилюля «Вся Alma» — приглашение, которое приходит и уходит.
///
/// **Это событие, а не мебель, и вся сложность здесь ровно из этого.**
/// Постоянное приглашение перестаёт быть приглашением на второй минуте: глаз
/// научается его не видеть, а угол экрана оно закрывать не перестаёт. Место
/// постоянного зова занимает статичная строка «Всё открыто — каждый день →
/// Посмотреть планы» в залоченной секции «Сегодня»; она стоит всегда и никуда
/// отсюда не девается. Пилюля лишь изредка на неё указывает.
///
/// Отсюда три закона, каждый из которых стоит одной ошибки, уже сделанной
/// когда-то в этом продукте:
///
/// * **Она приходит на осевший экран, а не вместе с ним.** Приглашение,
///   появившееся одновременно с содержимым, спорит с ним за первый взгляд и
///   проигрывает — а проиграв, читается помехой. Шесть секунд без единого
///   касания и без движения списка — это и есть «человек прочитал и поднял
///   глаза».
/// * **Её нельзя показать четыре раза.** Три показа за сессию, полторы минуты
///   тишины между ними, счётчик сбрасывается раз в календарные сутки.
/// * **«Не сейчас» — это ответ, а не пауза.** Отказ в шите гасит поверхность на
///   неделю, три отказа подряд выключают пилюлю навсегда, любая покупка — тоже.
///   Всё это переживает перезапуск: приглашение, забывающее отказ, — это не
///   приглашение, а домогательство.
///
/// **Слой.** Пилюля живёт отдельной записью `Overlay` над содержимым вкладки, а
/// не внутри списка: положенная в прокрутку, она уезжала бы вместе с текстом и
/// исчезала бы, когда прокрутили далеко. И она **под** баром вкладок — бар
/// всегда главнее приглашения.

/// Где пилюлю вообще можно показать.
///
/// Список закрыт намеренно. Пергамент главы, церемония расчёта, анкета, любой
/// шит, пейволл и диалог, «Люди» и настройки — места, где продавать значит
/// перебить то, ради чего человек туда пришёл; на пергаменте вдобавок нечем
/// нарисовать золотую пилюлю, чтобы она не выглядела наклейкой на бумаге.
enum PillSurface {
  today('today'),
  systems('systems');

  const PillSurface(this.wire);

  /// Имя в ключах памяти и в отчёте.
  final String wire;
}

/// Куда уходят события пилюли.
///
/// **Не в воронку `/v1/events`, и это не забывчивость.** Имена ступеней там —
/// закрытый набор (`backend/alma/funnel.py`: «The stage names are a closed
/// set»), сервер отвечает 422 на всё, чего не знает, и `pill_shown` он не
/// знает. Отправлять их туда сейчас значит терять их молча и портить воронку
/// потом. Сток стоит здесь, названный теми именами, что в спеке; в день, когда
/// сервер выучит эти шесть слов, меняется одна строка — [sink].
class PillEvents {
  const PillEvents._();

  /// Куда писать. По умолчанию — в отладочный вывод.
  static void Function(String name, Map<String, Object?> meta) sink =
      (name, meta) => debugPrint('pill: $name $meta');

  static void shown(PillSurface surface, int count) =>
      sink('pill_shown', {'surface': surface.wire, 'session_count': count});

  static void expired() => sink('pill_expired', const {});

  static void tapped() => sink('pill_tapped', const {});

  static void sheetDismissed(String via) => sink('sheet_dismissed', {'via': via});

  static void sheetCtaTapped() => sink('sheet_cta_tapped', const {});

  static void retired(String reason) => sink('pill_retired', {'reason': reason});
}

/// Что пилюля помнит между запусками.
///
/// Ключи — из спеки, слово в слово: `pill.notNowUntil[surface]` уплощён в
/// `pill.notNowUntil.today`, потому что `SharedPreferences` не знает вложенных
/// ключей, а второй словарь в JSON под одним ключом — это лишний разбор ради
/// красоты имени.
///
/// **Счётчики показов здесь намеренно нет.** «Три показа за сессию» — это про
/// сессию, и записанный на диск он превратил бы первую же минуту второго дня в
/// продолжение вчерашнего вечера.
class PillMemory {
  PillMemory._(this._prefs);

  static const _retiredKey = 'pill.retired';
  static const _dismissalsKey = 'pill.dismissals';
  static String _untilKey(PillSurface surface) =>
      'pill.notNowUntil.${surface.wire}';

  final SharedPreferences _prefs;

  static Future<PillMemory> open() async =>
      PillMemory._(await SharedPreferences.getInstance());

  bool get retired => _prefs.getBool(_retiredKey) ?? false;

  int get dismissals => _prefs.getInt(_dismissalsKey) ?? 0;

  /// Молчит ли поверхность прямо сейчас.
  bool silent(PillSurface surface, DateTime now) {
    final until = _prefs.getInt(_untilKey(surface));
    if (until == null) return false;
    return now.millisecondsSinceEpoch < until;
  }

  Future<void> hush(PillSurface surface, DateTime now) => _prefs.setInt(
        _untilKey(surface),
        now.add(const Duration(days: 7)).millisecondsSinceEpoch,
      );

  Future<int> noteDismissal() async {
    final next = dismissals + 1;
    await _prefs.setInt(_dismissalsKey, next);
    return next;
  }

  Future<void> retire() => _prefs.setBool(_retiredKey, true);
}

/// Связь между поверхностью и пилюлей.
///
/// **Почему отдельная вещь, а не поля виджета.** Пилюля нарисована в записи
/// `Overlay`, а всё, что решает её судьбу, происходит в другом месте дерева:
/// вкладку меняет оболочка, палец кладут на экран вкладки, список едет внутри
/// экрана. Гонять это пропсами значит перестраивать содержимое вкладки на
/// каждое касание — то есть платить перестройкой всех четырёх страниц за то,
/// чтобы посчитать шесть секунд тишины.
class PillDirector extends ChangeNotifier {
  PillSurface? _surface;
  bool _scrolling = false;
  bool _bought = false;
  int _stir = 0;

  /// Где мы сейчас. `null` — место, где звать нельзя (или звать некого).
  PillSurface? get surface => _surface;

  set surface(PillSurface? value) {
    if (value == _surface) return;
    _surface = value;
    notifyListeners();
  }

  /// Едет ли список под пилюлей.
  bool get scrolling => _scrolling;

  set scrolling(bool value) {
    if (value == _scrolling) return;
    _scrolling = value;
    if (value) _stir++;
    notifyListeners();
  }

  /// Куплено ли хоть что-нибудь. Покупка выключает приглашение навсегда: звать
  /// заплатившего — не продажа, а сообщение о том, что мы не знаем, кто перед
  /// нами.
  bool get bought => _bought;

  set bought(bool value) {
    if (value == _bought) return;
    _bought = value;
    notifyListeners();
  }

  /// Сколько раз экрана коснулись. Само число не значит ничего — важно, что оно
  /// изменилось: значит, шесть секунд тишины начинаются заново.
  int get stir => _stir;

  /// Палец лёг на экран.
  void stirred() {
    _stir++;
    notifyListeners();
  }
}

/// Восьмиконечная звезда знака Alma — та же форма, что внутри ромба эмблемы, но
/// светом, а не чернилами: на тёмном золоте пилюли чернильная звезда читается
/// дырой.
class AlmaStarMark extends StatelessWidget {
  const AlmaStarMark({super.key, required this.size, this.colour = AlmaPalette.starFill});

  final double size;
  final Color colour;

  @override
  Widget build(BuildContext context) => SizedBox.square(
        dimension: size,
        child: CustomPaint(painter: _StarMarkPainter(colour)),
      );
}

class _StarMarkPainter extends CustomPainter {
  const _StarMarkPainter(this.colour);

  final Color colour;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    // Те же пропорции, что у звезды в ромбе: четыре длинных луча по осям и
    // четыре коротких между, короткий — 0.38 длинного.
    final long = size.width / 2;
    final short = long * 0.38;
    final path = Path();
    for (var i = 0; i < 16; i++) {
      final r = i.isEven ? long : short;
      final a = -math.pi / 2 + i * math.pi / 8;
      final p = Offset(c.dx + r * math.cos(a), c.dy + r * math.sin(a));
      i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
    }
    path.close();
    canvas.drawPath(path, Paint()..color = colour);
  }

  @override
  bool shouldRepaint(_StarMarkPainter old) => old.colour != colour;
}

/// Общая метка перелёта звезды из пилюли в гнездо шита.
const String pillEmblemHeroTag = 'alma.pill.emblem';

/// Слой пилюли: одна запись `Overlay`, в которой живут и вид, и вся судьба.
class PillLayer extends StatefulWidget {
  const PillLayer({super.key, required this.director});

  final PillDirector director;

  @override
  State<PillLayer> createState() => _PillLayerState();
}

class _PillLayerState extends State<PillLayer> with TickerProviderStateMixin {
  /// Тишина, после которой экран считается осевшим.
  static const _settling = Duration(seconds: 6);

  /// Сколько пилюля живёт.
  static const _span = Duration(seconds: 11);

  /// Тишина между показами.
  static const _rest = Duration(seconds: 90);

  /// Показов за сессию.
  static const _times = 3;

  /// Кивки: на первой и на шестой секунде жизни.
  static const _firstNod = Duration(seconds: 1);
  static const _secondNod = Duration(seconds: 6);

  /// Приход и уход. Разные длительности в две стороны — это не украшение:
  /// приходит она заметно (380), уходит незаметно (260), потому что уход не
  /// должен тянуть на себя взгляд второй раз.
  ///
  /// **Все четыре часов заводятся в `initState`, а не по первому обращению.**
  /// Ленивым `late final` они создавались в момент первого использования — а у
  /// пилюли, которую на этой установке звать нельзя (подписчик, отказавшийся
  /// трижды, купивший главу), первым обращением оказывался `dispose`. Ticker,
  /// заведённый при снятии виджета с дерева, ищет `TickerMode` у мёртвого
  /// предка и падает. Найдено тестом «на чужой поверхности не приходит вовсе».
  late final AnimationController _life;
  late final AnimationController _nod;
  late final AnimationController _away;
  late final AnimationController _body;

  PillMemory? _memory;
  bool _retired = false;

  /// Счётчики сессии — в памяти, как велит спека.
  int _shown = 0;
  DateTime? _lastShown;
  DateTime _counting = DateTime.now();

  /// Нарисована ли она сейчас. `_life` сам по себе не ответ: у него ноль и на
  /// «ещё не пришла», и на «уже ушла».
  bool _here = false;

  /// Открыт ли шит. Пока он открыт, пилюля не живёт и не уходит: её время
  /// кончилось в момент нажатия.
  bool _morphing = false;

  Timer? _wait;
  Timer? _clock;
  Timer? _nod1;
  Timer? _nod2;

  int _seenStir = 0;
  PillSurface? _seenSurface;

  @override
  void initState() {
    super.initState();
    _life = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 380),
      reverseDuration: const Duration(milliseconds: 260),
    );
    _nod = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 600));
    _away = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 200));
    _body = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 150));
    _seenStir = widget.director.stir;
    _seenSurface = widget.director.surface;
    widget.director.addListener(_directed);
    PillMemory.open().then((memory) {
      if (!mounted) return;
      _memory = memory;
      _retired = memory.retired;
      _reconsider();
    });
  }

  @override
  void dispose() {
    widget.director.removeListener(_directed);
    _stopClocks();
    _life.dispose();
    _nod.dispose();
    _away.dispose();
    _body.dispose();
    super.dispose();
  }

  void _stopClocks() {
    _wait?.cancel();
    _clock?.cancel();
    _nod1?.cancel();
    _nod2?.cancel();
    _wait = _clock = _nod1 = _nod2 = null;
  }

  bool get _still => MediaQuery.maybeDisableAnimationsOf(context) ?? false;

  /* ── что говорит оболочка ─────────────────────────────────────────────── */

  void _directed() {
    final director = widget.director;
    // Пока открыт шит и пока пилюля из-под него уходит, оболочка ей не указ:
    // маршрут поверх кабинета обнуляет поверхность, и послушавшись, пилюля
    // сняла бы себя вместе со звездой, которая в эту секунду летит обратно.
    if (_morphing) {
      _seenSurface = director.surface;
      _seenStir = director.stir;
      return;
    }
    if (director.bought && !_retired) {
      _retire('purchase');
      return;
    }
    if (director.surface != _seenSurface) {
      _seenSurface = director.surface;
      // Показ не переносится на другую поверхность: это другой момент и другой
      // экран, и досчитывать чужие секунды на нём было бы враньём.
      _stopClocks();
      _leave(now: true);
      _reconsider();
      return;
    }
    if (director.stir != _seenStir) {
      _seenStir = director.stir;
      // Экран ещё живой под пальцем — шесть секунд тишины начинаются заново.
      // Уже пришедшую пилюлю касание не гонит: она немодальна.
      if (!_here) _reconsider();
    }
    if (_here && !_morphing) {
      director.scrolling ? _away.forward() : _away.reverse();
    }
  }

  /* ── расписание ───────────────────────────────────────────────────────── */

  /// Когда имеет смысл попробовать снова.
  void _reconsider() {
    _wait?.cancel();
    _wait = null;
    if (_here || _morphing) return;
    final memory = _memory;
    final surface = widget.director.surface;
    if (memory == null || surface == null || _retired) return;
    if (memory.silent(surface, DateTime.now())) return;
    if (_shownOut) return;
    _wait = Timer(_delay, _tryAppear);
  }

  /// Шесть секунд тишины, но не раньше, чем полторы минуты с прошлого показа.
  Duration get _delay {
    final last = _lastShown;
    if (last == null) return _settling;
    final since = DateTime.now().difference(last);
    final left = _rest - since;
    return left > _settling ? left : _settling;
  }

  /// Исчерпан ли счёт показов. Сутки считаются календарные и местные: смена
  /// даты — это новый день человека, а не двадцать четыре часа от запуска.
  bool get _shownOut {
    final now = DateTime.now();
    if (now.year != _counting.year ||
        now.month != _counting.month ||
        now.day != _counting.day) {
      _counting = now;
      _shown = 0;
      _lastShown = null;
    }
    return _shown >= _times;
  }

  void _tryAppear() {
    if (!mounted || _here || _morphing) return;
    final memory = _memory;
    final surface = widget.director.surface;
    if (memory == null || surface == null || _retired) return;
    if (memory.silent(surface, DateTime.now())) return;
    if (_shownOut) return;
    // Клавиатура открыта — человек пишет, и это худшая секунда из возможных.
    // Список ещё едет — экран не осел. И то и другое не отменяет показ, а
    // отодвигает его: считаем тишину заново.
    if (MediaQuery.viewInsetsOf(context).bottom > 0 ||
        widget.director.scrolling) {
      _wait = Timer(_settling, _tryAppear);
      return;
    }
    _appear(surface);
  }

  void _appear(PillSurface surface) {
    _shown += 1;
    _lastShown = DateTime.now();
    PillEvents.shown(surface, _shown);
    setState(() => _here = true);
    _life.forward(from: 0);
    _clock = Timer(_span, _expire);
    if (!_still) {
      _nod1 = Timer(_firstNod, _wobble);
      _nod2 = Timer(_secondNod, _wobble);
    }
  }

  void _wobble() {
    if (mounted && _here && !_morphing) _nod.forward(from: 0);
  }

  /// Одиннадцать секунд вышли.
  ///
  /// Уход **дожидается** конца — и это не педантизм: `_reconsider`, позванный
  /// до того, как пилюля сошла с экрана, видит её живой и молча не назначает
  /// следующий показ. Второго приглашения не было бы никогда.
  Future<void> _expire() async {
    if (!mounted || !_here) return;
    PillEvents.expired();
    await _leave();
    if (!mounted) return;
    _reconsider();
  }

  /// Уход. `now` — снять без движения: поверхность сменилась, и провожать
  /// пилюлю на экране, которого уже нет, некому.
  Future<void> _leave({bool now = false}) async {
    _stopClocks();
    _nod.stop();
    _away.value = 0;
    if (!_here) return;
    if (now) {
      _life.value = 0;
      _lastShown = DateTime.now();
      setState(() => _here = false);
      return;
    }
    await _life.reverse();
    if (!mounted) return;
    // Полторы минуты тишины считаются **от ухода**, а не от прихода: иначе из
    // девяноста секунд одиннадцать съедала бы сама пилюля, и тишины между
    // показами было бы семьдесят девять.
    _lastShown = DateTime.now();
    setState(() => _here = false);
  }

  Future<void> _retire(String reason) async {
    _retired = true;
    PillEvents.retired(reason);
    _stopClocks();
    _leave(now: true);
    await _memory?.retire();
  }

  /* ── нажатие ──────────────────────────────────────────────────────────── */

  Future<void> _tap() async {
    if (_morphing) return;
    HapticFeedback.lightImpact();
    PillEvents.tapped();
    // Жизнь пилюли на этом кончилась — она считается показанной, и таймер по
    // возвращении из шита не продолжается.
    _stopClocks();
    _nod.stop();
    setState(() => _morphing = true);
    // Тело растворяется на месте; летит только звезда.
    _body.forward(from: 0);
    final surface = widget.director.surface;
    // Пустой ответ — это тап по скриму: маршрут возвращает его только оттуда,
    // системной кнопки «назад» на iOS нет, а все три осмысленных выхода
    // называют себя сами.
    final exit = await Navigator.of(context).push(AllAlmaSheetRoute()) ??
        AllAlmaExit.scrim;
    if (!mounted) return;
    _body.reverse();
    switch (exit) {
      case AllAlmaExit.plans:
        PillEvents.sheetCtaTapped();
      case AllAlmaExit.notNow:
        PillEvents.sheetDismissed(exit.wire);
        // Отказ гасит **эту** поверхность на неделю, а не приложение целиком:
        // «не сейчас» на «Сегодня» ничего не говорит о «Моих системах».
        if (surface != null) await _memory?.hush(surface, DateTime.now());
        final count = await _memory?.noteDismissal() ?? 0;
        // Третий отказ подряд — это ответ, а не совпадение.
        if (count >= 3) await _retire('three_dismissals');
      case AllAlmaExit.swipe:
      case AllAlmaExit.scrim:
        PillEvents.sheetDismissed(exit.wire);
    }
    if (!mounted) return;
    // Лестница открывается после того, как шит ушёл: два листа, приезжающих
    // друг на друга, читаются как сбой, а не как переход.
    if (exit == AllAlmaExit.plans) unawaited(openAlmaPlans(context));
    // Жизнь пилюли кончилась в момент нажатия. Уходит она обычным уходом —
    // 260 мс, — и только когда ушла совсем, снимается признак морфа: до тех
    // пор оболочка не вправе снять её рывком из-под летящей звезды.
    await _leave();
    if (!mounted) return;
    setState(() => _morphing = false);
    _seenSurface = widget.director.surface;
    _seenStir = widget.director.stir;
    _reconsider();
  }

  /* ── вид ──────────────────────────────────────────────────────────────── */

  @override
  Widget build(BuildContext context) {
    if (!_here) return const SizedBox.shrink();
    final l = L.of(context);
    // Считаем от окна, а не от окружения: `Scaffold(extendBody: true)` кладёт в
    // `MediaQuery` тела высоту бара вместе с индикатором, и взятый оттуда
    // отступ поднял бы пилюлю на высоту бара дважды. То же решение и по той же
    // причине, что в `screen_scaffold.dart`.
    final window = MediaQueryData.fromView(View.of(context)).padding.bottom;
    return Positioned(
      right: 16,
      // Подъём над баром 16 (было 12) — вместе с укрупнением: чип в 44
      // точки на прежней отбивке садился на кромку бара.
      bottom: AlmaMetrics.tabBarHeight + window + 16,
      child: AnimatedBuilder(
        animation: Listenable.merge([_life, _nod, _away, _body]),
        builder: (context, child) {
          final t = Curves.easeOutCubic.transform(_life.value.clamp(0, 1));
          // «Меньше движения» снимает и подъём, и кивок — остаётся чистое
          // проявление. Не половина движения, а его отсутствие: половина
          // читается как подтормаживание.
          final rise = _still ? 0.0 : 8 * (1 - t);
          final nod = _still ? 0.0 : _nodAngle;
          // Увод за списком — трансформацией, а не прозрачностью: гаснущая
          // пилюля читается как ещё одно событие, а уезжающая — как то же
          // самое, что уезжает под пальцем.
          final away = Curves.easeOutCubic.transform(_away.value) * 64;
          return Opacity(
            opacity: t,
            child: Transform.translate(
              offset: Offset(0, rise + away),
              child: Transform.rotate(angle: nod, child: child),
            ),
          );
        },
        child: _Pill(
          label: l.cabAllAlmaPill,
          // Тело растворяется, звезда остаётся: она улетает в гнездо шита сама.
          bodyOpacity: 1 - _body.value,
          onTap: _tap,
        ),
      ),
    );
  }

  /// Затухающее покачивание ±4°: две с половиной волны, амплитуда тает к концу.
  /// Не тряска — кивок. Трясущееся всегда читается как ошибка отрисовки.
  double get _nodAngle {
    if (!_nod.isAnimating && _nod.value == 0) return 0;
    final t = _nod.value;
    final decay = (1 - t) * (1 - t);
    // 4° в радианах — 0.0698.
    return math.sin(t * math.pi * 5) * 0.0698 * decay;
  }
}

/// Сама пилюля: тёмное текстурное золото главной кнопки, звезда и два слова.
class _Pill extends StatelessWidget {
  const _Pill({
    required this.label,
    required this.bodyOpacity,
    required this.onTap,
  });

  final String label;

  /// Прозрачность **тела**. Звезда живёт отдельно: в морфе она — общий элемент
  /// и должна остаться видимой, когда всё вокруг неё уже растаяло.
  final double bodyOpacity;

  final VoidCallback onTap;

  static final _radius = BorderRadius.circular(999);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      // **Цель нажатия — само золото, а не прямоугольник вокруг него.**
      //
      // `HitTestBehavior.opaque` ловил весь габарит записи `Overlay`, включая
      // углы за скруглением и пустоту, оставшуюся от ленты 121×14. При высоте
      // 44 пилюля наконец сама себе цель: палец в 44 точки попадает по золоту,
      // а прозрачное поле рядом с ним перестаёт воровать нажатия у экрана под
      // пилюлей. Решение владельца, вместе с укрупнением.
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: _radius,
          // **Одна тень, без золотого ореола.**
          //
          // Ореол был в спеке, но не в макете, и на кадре давал вокруг чипа
          // свечение, которого в дизайне нет: решение владельца — прав эталон.
          // Сама тень чуть глубже макетной `0 5 14`, потому что там пилюля
          // нарисована в потоке, а у нас она плавающая и обязана отделяться от
          // содержимого под собой.
          boxShadow: const [
            BoxShadow(
              color: Color(0x73000000),
              blurRadius: 20,
              offset: Offset(0, 8),
            ),
          ],
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Opacity(
              opacity: bodyOpacity,
              child: GoldSurface(
                radius: _radius,
                child: Padding(
                  // **Размер даёт содержимое, а не коробка.**
                  //
                  // Здесь стояла `SizedBox(height: 38)` поверх этой же стопки —
                  // и не работала: стопка раздаёт детям свободные границы, так
                  // что золото под текстом вырастало только до его строки. На
                  // симуляторе пилюля выходила 121×14 — лента, а не чип, и
                  // владелец увидел ровно это. Высоту теперь задают поля.
                  //
                  // **Укрупнена по решению владельца: 44 вместо 35.**
                  //
                  // По числам спеки прежний чип был верен, и на кадре всё равно
                  // читался мелким — «размер дал заметность, крик не нужен».
                  // Поля 13×18, кегль 14, звезда 15, подъём над баром 16; вес
                  // остаётся 400. Высота складывается ровно: 13 + 18 + 13 = 44,
                  // где 18 — строка подписи (см. `height` ниже), а звезда в 15
                  // в неё умещается и высоту не держит.
                  padding: const EdgeInsets.symmetric(
                    vertical: 13,
                    horizontal: 18,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Место под звезду: она нарисована слоем выше, чтобы
                      // растворение тела её не уносило.
                      const SizedBox(width: 15),
                      const SizedBox(width: 7),
                      Text(
                        label,
                        style: AlmaType.button.copyWith(
                          fontSize: 14,
                          // **Обычное начертание, не полужирное.** Пилюля —
                          // тихое событие; кричат только кнопки действия.
                          // Золотую искру даёт эмблема, а не жирность букв.
                          fontWeight: FontWeight.w400,
                          fontVariations: const [FontVariation('wght', 400)],
                          // 18 при кегле 14 — это она, а не звезда в 15,
                          // держит высоту чипа: 13 + 18 + 13 = 44. Строка
                          // задана числом, а не `line-height:normal`, ровно
                          // потому, что высота здесь — договорённость с
                          // макетом, а не то, что решит шрифт.
                          height: 18 / 14,
                          color: AlmaPalette.inkLight,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              // Ровно горизонтальное поле: звезда стоит там, где кончается
              // отбивка, и `SizedBox(width: 15)` в строке держит под неё место.
              left: 18,
              child: Hero(
                tag: pillEmblemHeroTag,
                child: const AlmaStarMark(size: 15),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
