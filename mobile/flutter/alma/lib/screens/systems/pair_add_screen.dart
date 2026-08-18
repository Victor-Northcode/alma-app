import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../design/buttons.dart';
import '../../design/emblem.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import 'birth_form_parts.dart';

/// W2 · ввод партнёра прямо в совместимости.
///
/// Кадр `W2 Add partner` холста монетизации v3 (`SCREENS-V3.md` §W2): анкетный
/// экран с двумя распорками, как V0, — шапка с оверлайном, заголовок, три
/// пилюльных поля и анкетная кнопка радиусом 15 («ключ, которым продвигаются
/// вперёд, не должен выглядеть как кнопка, которой покупают»).
///
/// **Цены на экране нет ни одной, и это инвариант шага** (`locked-chapter-spec`
/// §1): расчёт бесплатен, платен только текст, и платить предлагают после
/// первой главы, не до. Ни `$`, ни слова «подписка» сюда не завозить.
///
/// **Экран кончается человеком.** Сохранил — вернул `Profile` тому, кто звал
/// (`Navigator.pop(saved)`): маршрут в главу I знает вызывающий
/// (`main.dart::_openPairChapter`), потому что слаг первой главы — знание
/// сервера, и второй копии этого знания здесь не будет.
///
/// **Четвёртое поле — место — холст не нарисовал, а сервер требует**
/// (`BirthInput.latitude/longitude/timezone` обязательны: без точки на земле
/// нет ни домов, ни часового пояса). Выдумать координаты нельзя — это была бы
/// ошибка до 180°, напечатанная уверенным тоном. Поле стоит той же пилюлей;
/// расхождение с холстом записано в спеке как вопрос владельцу.
class PairAddScreen extends StatefulWidget {
  const PairAddScreen({super.key});

  @override
  State<PairAddScreen> createState() => _PairAddScreenState();
}

class _PairAddScreenState extends State<PairAddScreen> {
  final _name = TextEditingController();
  final _place = TextEditingController();

  /// Дата не выбрана, пока человек её не назвал. Умолчания «1 января 1990»
  /// в пилюле нет намеренно: предзаполненная дата — это дата, которую никто
  /// не называл, готовая уехать на сервер (см. довод у колеса анкеты).
  int? _day, _month, _year;

  /// Время — необязательное, и «не выбрано» здесь законное конечное
  /// состояние, а не недозаполненность: помета `optional` стоит на самом поле.
  int? _hour, _minute;

  Place? _chosen;
  List<Place> _found = const [];
  bool _saving = false;
  String? _failure;

  @override
  void dispose() {
    _name.dispose();
    _place.dispose();
    super.dispose();
  }

  bool get _ready => _day != null && _chosen != null && !_saving;

  Future<void> _search(String query) async {
    if (query.trim().length < 2) return;
    try {
      final found = await SessionScope.of(context).client.searchPlaces(query);
      if (mounted) setState(() => _found = found.take(5).toList());
    } on AlmaError {
      // Молча: место можно поискать ещё раз.
    }
  }

  Future<void> _save() async {
    if (!_ready) return;
    final l = L.of(context);
    final session = SessionScope.of(context);
    setState(() {
      _saving = true;
      _failure = null;
    });
    try {
      final saved = await savePartner(
        session,
        birthDate: '${_year.toString().padLeft(4, '0')}-'
            '${_month.toString().padLeft(2, '0')}-'
            '${_day.toString().padLeft(2, '0')}',
        birthTime: _hour == null
            ? null
            : '${_hour.toString().padLeft(2, '0')}:'
                '${(_minute ?? 0).toString().padLeft(2, '0')}',
        place: _chosen!,
        name: _name.text,
      );
      if (!mounted) return;
      Navigator.of(context).pop(saved);
    } on AlmaError catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        // 402 `partner_limit` приходит на языке аккаунта и показывается
        // дословно; всему остальному — общая строка, а не голое молчание:
        // кнопка, не ответившая ничем, читается как сломанная.
        _failure = error is ServerRefused && error.message.isNotEmpty
            ? error.message
            : l.stateUnavailable;
      });
    }
  }

  /* ── пилюли даты и времени ────────────────────────────────────────────── */

  /// Дата — один лист с тремя барабанами, а не три пилюли, как на экране
  /// людей: холст рисует **одно** поле «Date of birth», и разбивать его на
  /// три значило бы перерисовать кадр. Барабаны — те же колёса платформы.
  Future<void> _pickDate() async {
    var day = _day ?? 1, month = _month ?? 1, year = _year ?? 1990;
    final done = await _sheet<bool>(
      builder: (context, refresh) {
        // Дней в месяце — сколько есть на самом деле: 30 февраля, уехавшее
        // на сервер, вернулось бы отказом на языке валидатора, а не формы.
        final days = DateUtils.getDaysInMonth(year, month);
        if (day > days) day = days;
        return [
          Row(children: [
            _wheel(L.of(context).journeyCaptureDayShort, day, 1, days,
                (v) => refresh(() => day = v)),
            _wheel(L.of(context).journeyCaptureMonthShort, month, 1, 12,
                (v) => refresh(() => month = v)),
            _wheel(L.of(context).journeyCaptureYearShort, year, 1900,
                DateTime.now().year, (v) => refresh(() => year = v)),
          ]),
          const SizedBox(height: 14),
          AlmaButton(
            kind: AlmaButtonKind.outline,
            label: L.of(context).scrDone,
            onTap: () => Navigator.of(context).pop(true),
          ),
        ];
      },
    );
    if (done == true && mounted) {
      setState(() {
        _day = day;
        _month = month;
        _year = year;
      });
    }
  }

  Future<void> _pickTime() async {
    var hour = _hour ?? 12, minute = _minute ?? 0;
    final answer = await _sheet<String>(
      builder: (context, refresh) => [
        Row(children: [
          _wheel(L.of(context).journeyHourLabel, hour, 0, 23,
              (v) => refresh(() => hour = v)),
          _wheel(L.of(context).journeyMinuteLabel, minute, 0, 59,
              (v) => refresh(() => minute = v)),
        ]),
        const SizedBox(height: 14),
        AlmaButton(
          kind: AlmaButtonKind.outline,
          label: L.of(context).scrDone,
          onTap: () => Navigator.of(context).pop('set'),
        ),
        const SizedBox(height: 8),
        // Обратная дорога: время выбрали, а потом вспомнили, что не знают.
        // Без неё поле `optional` становилось бы необратимым — единственный
        // способ снять значение был бы «выйти и ввести всё заново».
        AlmaButton(
          kind: AlmaButtonKind.veil,
          label: L.of(context).cabUnknownTime,
          onTap: () => Navigator.of(context).pop('clear'),
        ),
      ],
    );
    if (!mounted || answer == null) return;
    setState(() {
      if (answer == 'clear') {
        _hour = null;
        _minute = null;
      } else {
        _hour = hour;
        _minute = minute;
      }
    });
  }

  /// Ночной лист с золотым кантом — та же плашка, что у находок города.
  Future<T?> _sheet<T>(
      {required List<Widget> Function(
              BuildContext context, void Function(VoidCallback) refresh)
          builder}) {
    return showModalBottomSheet<T>(
      context: context,
      backgroundColor: AlmaPalette.night700,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      builder: (context) => SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 18, 22, 14),
          child: StatefulBuilder(
            builder: (context, setSheet) => Column(
              mainAxisSize: MainAxisSize.min,
              children: builder(context, setSheet),
            ),
          ),
        ),
      ),
    );
  }

  /// Один барабан листа, обёрнутый распоркой колонки.
  Widget _wheel(String label, int value, int min, int max,
      ValueChanged<int> onChanged) {
    return Expanded(
      child: _SheetWheel(
        label: label,
        min: min,
        max: max,
        value: value,
        onChanged: onChanged,
      ),
    );
  }

  /// Пилюля выбора — то же очертание, что у `CeremonialField`: высота 54,
  /// радиус в половину, в покое тёмная плашка с бледным кантом. Выбранное
  /// значение печатается телом, пустое — плейсхолдером на 0.45, как на холсте.
  Widget _pill({
    required String hint,
    String? value,
    String? trailing,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        height: AlmaMetrics.fieldHeight,
        padding: const EdgeInsets.symmetric(horizontal: 18),
        decoration: BoxDecoration(
          color: const Color(0xD90D101C),
          borderRadius: BorderRadius.circular(AlmaMetrics.fieldHeight / 2),
          border: Border.all(color: const Color(0x1FEDE7DA)),
        ),
        child: Row(children: [
          Expanded(
            child: Text(
              value ?? hint,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AlmaType.body.copyWith(
                fontSize: 15.5,
                color: value == null
                    ? AlmaPalette.body.withValues(alpha: 0.45)
                    : AlmaPalette.inkLight,
              ),
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 12),
            // `optional` — Golos 12.5, золото на 0.8: снято с кадра.
            Text(trailing,
                style: AlmaType.meta.copyWith(
                    fontSize: 12.5,
                    color: AlmaPalette.gold.withValues(alpha: 0.8))),
          ],
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final date = _day == null
        ? null
        : DateFormat.yMMMMd(l.localeName)
            .format(DateTime.utc(_year!, _month!, _day!));
    final time = _hour == null
        ? null
        : '${_hour.toString().padLeft(2, '0')}:'
            '${(_minute ?? 0).toString().padLeft(2, '0')}';
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      // Небо экран рисует себе сам: каркас кабинета — прокручиваемая колонка
      // с заголовком, а здесь анкета с распорками и донной кнопкой.
      body: NightSky(
        seed: 0x57325041,
        child: SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
            child: Column(children: [
              const SizedBox(height: 12),
              // Шапка кадра: «←», оверлайн по центру, распорка той же ширины —
              // центр обязан быть настоящим центром строки.
              Row(children: [
                GestureDetector(
                  onTap: () => Navigator.of(context).maybePop(),
                  behavior: HitTestBehavior.opaque,
                  child: SizedBox(
                    width: 44,
                    height: 44,
                    child: Center(
                      child: Text('←',
                          style: AlmaType.body.copyWith(
                              fontSize: 18,
                              color:
                                  AlmaPalette.body.withValues(alpha: 0.7))),
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    l.scrPeopleEyebrow.toUpperCase(),
                    textAlign: TextAlign.center,
                    style:
                        AlmaType.readerHead.copyWith(color: AlmaPalette.gold),
                  ),
                ),
                const SizedBox(width: 44),
              ]),
              Expanded(
                // Колонка с двумя распорками, но готовая к клавиатуре: без
                // прокрутки поле места ныряло бы под неё вместе с находками.
                child: LayoutBuilder(
                  builder: (context, box) => SingleChildScrollView(
                    child: ConstrainedBox(
                      constraints: BoxConstraints(minHeight: box.maxHeight),
                      child: IntrinsicHeight(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Spacer(),
                            Text(l.paywallV3PairInputTitle,
                                style: AlmaType.displayL),
                            const SizedBox(height: 10),
                            Text(l.pairInputNote,
                                style: AlmaType.meta.copyWith(height: 1.5)),
                            const SizedBox(height: 24),
                            // Порядок «имя → дата → время» разговорный, а не
                            // машинный: сначала о ком, потом когда. Имя
                            // необязательно; обязательны дата и место.
                            CeremonialField(
                              controller: _name,
                              hint: l.paywallV3PairInputName,
                            ),
                            const SizedBox(height: 11),
                            _pill(
                              hint: l.paywallV3PairInputDate,
                              value: date,
                              onTap: _pickDate,
                            ),
                            const SizedBox(height: 11),
                            _pill(
                              hint: l.pairInputTime,
                              value: time,
                              trailing: time == null ? l.pairInputOptional : null,
                              onTap: _pickTime,
                            ),
                            const SizedBox(height: 11),
                            CeremonialField(
                              controller: _place,
                              hint: l.pairInputPlace,
                              onChanged: _search,
                            ),
                            PlaceSuggestions(
                              found: _found,
                              onPick: (place) => setState(() {
                                _chosen = place;
                                _place.text = place.label;
                                _found = const [];
                              }),
                            ),
                            const SizedBox(height: 18),
                            // ✦-сноска кадра: расчёт бесплатен, первая глава
                            // читается до любых решений. Фраза холста написана
                            // про «его» карту, а род партнёра здесь не
                            // спрашивают — в каталоге она родо-нейтральна.
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Padding(
                                  padding: const EdgeInsets.only(top: 1),
                                  child: Text('✦',
                                      style: AlmaType.numeral
                                          .copyWith(fontSize: 12)),
                                ),
                                const SizedBox(width: 9),
                                Expanded(
                                  child: Text(
                                    l.pairInputFreeNote,
                                    style: AlmaType.meta.copyWith(
                                        fontSize: 12.5,
                                        height: 1.5,
                                        color: AlmaPalette.body
                                            .withValues(alpha: 0.7)),
                                  ),
                                ),
                              ],
                            ),
                            const Spacer(),
                            // **Отказ стоит у кнопки и отличается от пояснения
                            // цветом.**
                            //
                            // Он стоял выше, сразу за ✦-сноской, и тем же серым
                            // мета-стилем. На проверке предел свободного тарифа
                            // («один сохранённый человек») вернулся ровно так и
                            // прочитался вторым абзацем подсказки: нажатие
                            // выглядело не отказом, а полным отсутствием
                            // ответа. Отказ — ответ на нажатие, и стоять ему
                            // рядом с тем, что нажали, тем же цветом, каким во
                            // всём продукте говорят «не вышло».
                            if (_failure != null) ...[
                              Text(_failure!,
                                  style: AlmaType.meta.copyWith(
                                      color: AlmaPalette.disagree,
                                      height: 1.5)),
                              const SizedBox(height: 12),
                            ] else
                              const SizedBox(height: 16),
                            AlmaButton(
                              // Радиус 15 — анкетная форма, как на V0.
                              radius: 15,
                              label:
                                  _saving ? l.scrAddPersonSaving : l.pairInputCta,
                              onTap: _ready ? _save : null,
                            ),
                            // Под кнопкой ничего не стоит, и это осознанно.
                            //
                            // Здесь была фраза «The bought pair report — four
                            // chapters, zero commerce inside». На холсте это
                            // **подпись кадра W3** — пометка дизайнера о том,
                            // что внутри купленного отчёта нет торговли. В
                            // приложении она превращалась в текст о продукте от
                            // третьего лица, который читает человек, набирающий
                            // чужую дату рождения. Обещание этого экрана уже
                            // сказано выше, у ✦: расчёт бесплатный, первую
                            // главу читают до решения.
                            //
                            // Донная распорка кадра — 44 плюс кромка жеста.
                            SizedBox(
                                height: 44 +
                                    MediaQuery.paddingOf(context).bottom),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

/// Барабан листа выбора. Плоский, как колесо анкеты: перспектива на узкой
/// колонке читается сбоем вёрстки, а не объёмом.
///
/// **Контроллер живёт в состоянии, а не в build.** Лист перестраивается на
/// каждый поворот любого барабана (значение месяца меняет число дней), и
/// контроллер, созданный в build, возвращал бы все три колонки на исходную
/// строку при каждом движении пальца.
class _SheetWheel extends StatefulWidget {
  const _SheetWheel({
    required this.label,
    required this.min,
    required this.max,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final int min;
  final int max;
  final int value;
  final ValueChanged<int> onChanged;

  @override
  State<_SheetWheel> createState() => _SheetWheelState();
}

class _SheetWheelState extends State<_SheetWheel> {
  late final FixedExtentScrollController _controller =
      FixedExtentScrollController(initialItem: widget.value - widget.min);

  @override
  void didUpdateWidget(_SheetWheel old) {
    super.didUpdateWidget(old);
    // Февраль после января: выбранный 31-й день перестал существовать, и
    // барабан обязан доехать до последнего настоящего, а не стоять за краем
    // укоротившегося списка. Сверяется положение самого барабана — значение
    // родитель уже подрезал, и по нему обрыв не виден.
    if (widget.max < old.max) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!_controller.hasClients) return;
        final last = widget.max - widget.min;
        if (_controller.selectedItem > last) _controller.jumpToItem(last);
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Text(widget.label.toUpperCase(),
          style: AlmaType.tag.copyWith(color: AlmaPalette.muted3)),
      const SizedBox(height: 6),
      SizedBox(
        height: 170,
        child: ListWheelScrollView.useDelegate(
          controller: _controller,
          itemExtent: 34,
          diameterRatio: 2.4,
          perspective: 0.002,
          physics: const FixedExtentScrollPhysics(),
          onSelectedItemChanged: (index) =>
              widget.onChanged(widget.min + index),
          childDelegate: ListWheelChildBuilderDelegate(
            childCount: widget.max - widget.min + 1,
            builder: (context, index) => Center(
              child: Text(
                '${widget.min + index}',
                style: AlmaType.body.copyWith(
                  fontSize: 16,
                  color: widget.min + index == widget.value
                      ? AlmaPalette.inkLight
                      : AlmaPalette.body.withValues(alpha: 0.45),
                ),
              ),
            ),
          ),
        ),
      ),
    ]);
  }
}
