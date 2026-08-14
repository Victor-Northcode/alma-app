import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../systems/writing_art.dart';

/// Путешествие: шесть шагов от имени до церемонии.
///
/// Порт `mobile/ios/Alma/Screens/Journey/*`. Порядок шагов тот же — имя, о
/// себе, дата, время, место, церемония, — и обещание под первым вопросом то
/// же: «Пока ничего не сохраняется». Это правда буквально: профиль не
/// создаётся до нажатия «Построить моё небо», и человек, закрывший путешествие
/// на четвёртом шаге, не оставил на сервере ничего.
class JourneyScreen extends StatefulWidget {
  const JourneyScreen({super.key, required this.onDone});

  final VoidCallback onDone;

  @override
  State<JourneyScreen> createState() => _JourneyScreenState();
}

/// Шесть шагов, как на нативе. Церемония — не украшение и не заставка: это
/// единственный экран, где системы действительно считаются, и человек видит,
/// что за него взялись, вместо белого поля с крутилкой.
enum _Step { name, about, date, time, place, ceremony }

class _JourneyScreenState extends State<JourneyScreen> {
  /// С какого шага открыться. **Вход для проверки, как на нативе**
  /// (`JourneyModel.swift` читает `AlmaJourneyStep` из `UserDefaults`): экраны
  /// анкеты видны один раз в жизни установки, и снять их рядом с нативным
  /// кадром иначе нечем. В обычной сборке константа пуста и шаг первый.
  _Step _step = _Step.values.firstWhere(
    (step) => step.name == const String.fromEnvironment('ALMA_JOURNEY_STEP'),
    orElse: () => _Step.name,
  );

  final _name = TextEditingController();
  String? _gender;
  // **Ничего не предзаполнено.** Колесо, открывшееся на «1 января 2000»,
  // читается как ответ, который уже дан: человек прокручивает мимо и уезжает
  // с чужой датой. `null` значит «не трогали», и первое же движение
  // записывает — как на нативе, где биндинг колеса показывает первое значение
  // и не присваивает его.
  int? _day, _month, _year;
  int? _hour, _minute;
  bool _timeUnknown = false;
  final _placeQuery = TextEditingController();
  List<Place> _places = const [];
  Place? _place;
  bool _saving = false;
  String? _failure;

  /// Начало анкеты сообщается один раз за приход, а не на каждый кадр.
  bool _announced = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_announced) return;
    _announced = true;
    SessionScope.of(context).client.track(FunnelStage.quizStart);
  }

  @override
  void dispose() {
    _name.dispose();
    _placeQuery.dispose();
    super.dispose();
  }

  static int get _thisYear => DateTime.now().year;

  /// Месяц словом, на языке интерфейса. Числом он читается как ещё одна
  /// колонка цифр, и «03» рядом с «03» днём — это две одинаковые колонки.
  static String _monthName(String locale, int month) =>
      DateFormat.MMMM(locale).format(DateTime.utc(2000, month));

  /// Все три колеса тронуты.
  bool get _dateComplete => _day != null && _month != null && _year != null;

  /// Такой даты не бывает. Проверяется тем же способом, что на нативе:
  /// собранная дата обязана вернуть те же день и месяц — 31 февраля молча
  /// становится 2 марта, и молчание здесь недопустимо.
  bool get _dateImpossible {
    if (!_dateComplete) return false;
    final made = DateTime.utc(_year!, _month!, _day!);
    return made.month != _month || made.day != _day;
  }

  /// Время введено наполовину. Пустое время пропускают — это и есть «не
  /// знаю»; половина времени — это опечатка, и с ней дальше не пускают.
  bool get _timeHalfGiven =>
      !_timeUnknown && (_hour == null) != (_minute == null);

  Future<void> _searchPlaces(String query) async {
    if (query.trim().length < 2) return;
    final session = SessionScope.of(context);
    try {
      final places = await session.client.searchPlaces(query.trim());
      if (mounted) setState(() => _places = places.take(5).toList());
    } on AlmaError {
      // Пустой список честнее сломанного экрана; строка «ничего не нашлось»
      // появится сама.
    }
  }

  Future<void> _build() async {
    final place = _place;
    if (place == null || _saving) return;
    final session = SessionScope.of(context);
    setState(() {
      _saving = true;
      _failure = null;
    });
    try {
      // **Анкета завершается здесь, а не на портрете.** К этой минуте отвечено
      // на каждый вопрос; портрет — награда, и путать «ответил на всё» с
      // «увидел результат» значит спрятать ровно тех людей, у кого сохранение
      // не прошло.
      await session.client.track(FunnelStage.quizComplete);
      await session.client.saveProfile(BirthInput(
        birthDate: '${_year!.toString().padLeft(4, '0')}-'
            '${_month!.toString().padLeft(2, '0')}-'
            '${_day!.toString().padLeft(2, '0')}',
        birthTime: _timeUnknown || _hour == null || _minute == null
            ? null
            : '${_hour!.toString().padLeft(2, '0')}:'
                '${_minute!.toString().padLeft(2, '0')}',
        latitude: place.latitude,
        longitude: place.longitude,
        timezone: place.timezone,
        placeLabel: place.label,
        placeId: place.id,
        name: _name.text.trim().isEmpty ? null : _name.text.trim(),
      ), gender: _gender);
      if (_name.text.trim().isNotEmpty) {
        await session.client.setDisplayName(_name.text.trim());
      }
      await session.start(force: true);
      if (!mounted) return;
      setState(() => _saving = false);
      // Кто пришёл вторым, тот и уводит.
      if (_ceremonyPlayed) widget.onDone();
    } on AlmaError catch (error) {
      if (mounted) {
        setState(() {
          _saving = false;
          _failure = error is ServerRefused && error.message.isNotEmpty
              ? error.message
              : L.of(context).stateUnavailable;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: NightSky(
        mood: SkyMood.ceremony,
        seed: 0x4A4F5552 + _step.index,
        child: SafeArea(
          child: _step == _Step.ceremony
              ? _Ceremony(
                  onDone: () {
                    // Церемония доиграла. Уходим, только когда и сохранение
                    // закончилось: сцена, ушедшая раньше ответа сервера,
                    // показала бы пустой кабинет.
                    if (mounted && !_saving) widget.onDone();
                    _ceremonyPlayed = true;
                  },
                )
              : Padding(
            padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const SizedBox(height: 12),
              Row(children: [
                // «I / V» — римскими, как на нативных экранах. Знаменатель
                // считается по самому перечислению: жёсткая «VI» обещала
                // шестой шаг, которого в порте нет — церемония ещё не
                // перенесена, — и последний экран анкеты объявлял себя «V / VI»,
                // то есть предпоследним.
                Text(
                  '${_roman(_step.index + 1)} / ${_roman(_Step.values.length)}',
                  style: AlmaType.numeral.copyWith(color: AlmaPalette.gold),
                ),
                const Spacer(),
                if (_step != _Step.name)
                  IconButton(
                    onPressed: () =>
                        setState(() => _step = _Step.values[_step.index - 1]),
                    icon: const Icon(Icons.arrow_back, color: AlmaPalette.gold),
                  ),
              ]),
              const Spacer(),
              ..._stepBody(l),
              const Spacer(),
              if (_failure != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Text(_failure!, style: AlmaType.meta),
                ),
              _cta(l),
              const SizedBox(height: 24),
            ]),
          ),
        ),
      ),
    );
  }

  /// Церемония доиграла до конца. Нужно, чтобы уйти в кабинет тому, у кого
  /// сохранение оказалось дольше девяти с половиной секунд.
  bool _ceremonyPlayed = false;

  static String _roman(int n) => const ['I', 'II', 'III', 'IV', 'V', 'VI'][n - 1];

  List<Widget> _stepBody(L l) => switch (_step) {
        _Step.name => [
            Text(l.journeyNameTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyNameSub, style: AlmaType.meta),
            const SizedBox(height: 24),
            // Плейсхолдера нет намеренно: «София» в поле имени читается как
            // чужая заполненная анкета, а не как подсказка.
            _field(_name, ''),
          ],
        _Step.about => [
            Text(l.journeyAboutTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyAboutSub, style: AlmaType.meta),
            const SizedBox(height: 24),
            for (final (value, label) in [
              ('female', l.journeyGenderFemale),
              ('male', l.journeyGenderMale),
              (null, l.journeyGenderSkip),
            ])
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _choice(label, selected: _gender == value, onTap: () {
                  setState(() => _gender = value);
                }),
              ),
          ],
        _Step.date => [
            Text(l.journeyDateTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyDateSub, style: AlmaType.meta),
            const SizedBox(height: 24),
            // **Три колеса, а не три поля.** Дату рождения набирают один раз
            // в жизни, и клавиатура здесь — это четыре тапа, проверка на
            // «31 февраля» и всплывающая цифровая панель поверх вопроса. Колесо
            // не даёт ввести невозможное число вовсе.
            Row(children: [
              Expanded(
                child: _Wheel(
                  label: l.journeyCaptureDay,
                  options: [for (var d = 1; d <= 31; d++) d],
                  selected: _day,
                  caption: (d) => '$d',
                  onChanged: (d) => setState(() => _day = d),
                ),
              ),
              // Месяц — словом, и только ему отдана лишняя ширина: «Сентябрь»
              // в колонку по числу цифр не помещается.
              Expanded(
                flex: 2,
                child: _Wheel(
                  label: l.journeyCaptureMonth,
                  options: [for (var m = 1; m <= 12; m++) m],
                  selected: _month,
                  caption: (m) => _monthName(l.localeName, m),
                  onChanged: (m) => setState(() => _month = m),
                ),
              ),
              Expanded(
                child: _Wheel(
                  label: l.journeyCaptureYear,
                  // Девяносто два года вниз от «десять лет назад»: продукт для
                  // взрослых, и год рождения младенца в списке — это строка,
                  // которую прокручивают мимо, а не выбирают.
                  options: [for (var i = 0; i < 92; i++) _thisYear - 10 - i],
                  selected: _year,
                  caption: (y) => '$y',
                  onChanged: (y) => setState(() => _year = y),
                ),
              ),
            ]),
            // Дата, которой не бывает, названа до нажатия «дальше», а не
            // отказом сервера после.
            if (_dateImpossible)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(l.journeyCaptureImpossibleDate,
                    style: AlmaType.meta.copyWith(color: AlmaPalette.goldBright)),
              ),
          ],
        _Step.time => [
            Text(l.journeyTimeTitle, style: AlmaType.displayL),
            const SizedBox(height: 24),
            // Колёса гаснут и перестают отвечать, когда объявлено незнание:
            // время, набранное под галочкой «не знаю», всё равно не поедет.
            AnimatedOpacity(
              opacity: _timeUnknown ? 0.4 : 1,
              duration: AlmaMotion.ui,
              child: IgnorePointer(
                ignoring: _timeUnknown,
                child: Row(children: [
                  Expanded(
                    child: _Wheel(
                      label: l.journeyHourLabel,
                      options: [for (var h = 0; h <= 23; h++) h],
                      selected: _hour,
                      caption: (h) => h.toString().padLeft(2, '0'),
                      onChanged: (h) => setState(() => _hour = h),
                    ),
                  ),
                  Expanded(
                    child: _Wheel(
                      label: l.journeyMinuteLabel,
                      options: [for (var m = 0; m <= 59; m++) m],
                      selected: _minute,
                      caption: (m) => m.toString().padLeft(2, '0'),
                      onChanged: (m) => setState(() => _minute = m),
                    ),
                  ),
                ]),
              ),
            ),
            const SizedBox(height: 18),
            _choice(
              l.journeyCaptureUnknownTime,
              selected: _timeUnknown,
              onTap: () => setState(() => _timeUnknown = !_timeUnknown),
            ),
            const SizedBox(height: 8),
            // Что закрывается без времени — сказано до, а не обнаружено после.
            Text(l.journeyLockedWithoutTime, style: AlmaType.meta),
          ],
        _Step.place => [
            Text(l.journeyPlaceTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyPlaceSub, style: AlmaType.meta),
            const SizedBox(height: 24),
            _field(_placeQuery, l.journeyCaptureSearchPlace,
                onChanged: _searchPlaces),
            const SizedBox(height: 8),
            for (final place in _places)
              _choice(place.label, selected: _place?.id == place.id, onTap: () {
                setState(() {
                  _place = place;
                  _placeQuery.text = place.label;
                  _places = const [];
                });
              }),
          ],
        // Церемония рисует себя целиком и не пользуется общей рамкой шага:
        // у неё нет ни заголовка, ни кнопки.
        _Step.ceremony => const [],
      };

  Widget _cta(L l) {
    final isLast = _step == _Step.place;
    final enabled = !_saving &&
        (!isLast || _place != null) &&
        !(_step == _Step.date && !_dateComplete) &&
        !(_step == _Step.date && _dateImpossible) &&
        !(_step == _Step.time && _timeHalfGiven);
    // **Выключенная кнопка обязана выглядеть выключенной.** Золотая заливка
    // рисовалась всегда, и на шаге даты человек видел горящую кнопку, которая
    // не отвечает на нажатие: это читается как поломка, а не как «сначала
    // выбери дату».
    return Opacity(
      opacity: enabled ? 1 : 0.45,
      child: SizedBox(
      width: double.infinity,
      height: AlmaMetrics.buttonHeight,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: AlmaGradient.goldButton,
          borderRadius: BorderRadius.circular(AlmaPalette.buttonRadius),
        ),
        child: TextButton(
          onPressed: enabled
              ? () {
                  if (isLast) {
                    // На церемонию уходят сразу, а сохранение стартует под
                    // ней: экран не ждёт сети, чтобы показать, что за человека
                    // взялись.
                    setState(() => _step = _Step.ceremony);
                    _build();
                  } else {
                    setState(() => _step = _Step.values[_step.index + 1]);
                  }
                }
              : null,
          child: Text(
            isLast ? l.journeyBuildMySky : l.journeyContinueCta,
            style: AlmaType.button,
          ),
        ),
      ),
      ),
    );
  }

  Widget _field(TextEditingController controller, String hint,
      {ValueChanged<String>? onChanged}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        border: Border.all(color: AlmaPalette.hairlineGold),
        borderRadius: BorderRadius.circular(AlmaMetrics.fieldHeight / 2),
      ),
      child: TextField(
        controller: controller,
        onChanged: onChanged,
        style: AlmaType.body,
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: AlmaType.meta,
          border: InputBorder.none,
        ),
      ),
    );
  }

  Widget _choice(String label,
      {required bool selected, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          border: Border.all(
              color: selected ? AlmaPalette.gold : AlmaPalette.hairline),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label,
            style: AlmaType.body.copyWith(
                color: selected ? AlmaPalette.goldBright : AlmaPalette.body)),
      ),
    );
  }
}

/// Одно колесо анкеты.
///
/// Порт `JourneyWheel` из `JourneyControls.swift`, и главное здесь —
/// **биндинг**: пока ничего не выбрано, в окне видно первое значение, но
/// записанным оно не считается. Иначе колесо, открывшееся на «1», отдало бы
/// единицу тому, кто до него не дотронулся, и дата рождения половины людей
/// начиналась бы с первого числа.
class _Wheel extends StatefulWidget {
  const _Wheel({
    required this.label,
    required this.options,
    required this.selected,
    required this.caption,
    required this.onChanged,
  });

  final String label;
  final List<int> options;
  final int? selected;
  final String Function(int) caption;
  final ValueChanged<int> onChanged;

  @override
  State<_Wheel> createState() => _WheelState();
}

class _WheelState extends State<_Wheel> {
  late final FixedExtentScrollController _controller = FixedExtentScrollController(
    initialItem: widget.selected == null
        ? 0
        : widget.options.indexOf(widget.selected!).clamp(0, widget.options.length - 1),
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: widget.label,
      value: widget.selected == null ? '' : widget.caption(widget.selected!),
      child: SizedBox(
        height: 148,
        child: Stack(alignment: Alignment.center, children: [
          // Полоса выбора: две волосяные линии в 34 точках друг от друга —
          // ровно высота строки. Без неё колесо не показывает, какое из
          // значений выбрано, и центральная строка ничем не отличается от
          // соседних.
          Container(
            height: 34,
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(color: AlmaPalette.hairlineGold),
                bottom: BorderSide(color: AlmaPalette.hairlineGold),
              ),
            ),
          ),
          ListWheelScrollView.useDelegate(
          controller: _controller,
          // 34 — высота строки, при которой в окно 148 точек попадает
          // четыре с половиной значения: столько же, сколько в нативном
          // колесе, и достаточно, чтобы соседние читались, а не угадывались.
          itemExtent: 34,
          diameterRatio: 1.6,
          perspective: 0.004,
          physics: const FixedExtentScrollPhysics(),
          onSelectedItemChanged: (index) {
            HapticFeedback.selectionClick();
            widget.onChanged(widget.options[index]);
          },
          childDelegate: ListWheelChildBuilderDelegate(
            childCount: widget.options.length,
            builder: (context, index) {
              final value = widget.options[index];
              final chosen = widget.selected == value;
              return Center(
                child: Text(
                  widget.caption(value),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AlmaType.displayL.copyWith(
                    fontSize: 19,
                    // Невыбранное — тише, но читаемо: колесо, у которого
                    // видно только центральную строку, перестаёт быть колесом.
                    color: chosen ? AlmaPalette.inkLight : AlmaPalette.muted3,
                  ),
                ),
              );
            },
          ),
          ),
        ]),
      ),
    );
  }
}

/// Шестой шаг: восемь ударов, за которые считаются восемь систем.
///
/// Порт `JourneyCeremonyStep.swift`. Числа оттуда же и не округлены: удар
/// первый показывается сразу, каждый следующий через 1150 мс, после восьмого
/// ещё 1400 мс — итого 9,45 секунды. Семь мягких тиков на ударах со второго по
/// восьмой (на первом тика нет: он уже на экране, когда сцена появилась) и
/// один тяжёлый в конце.
///
/// **Кнопки «пропустить» нет, и это решение.** Пропуск прыгал через
/// единственный экран, где системы действительно считаются, — и оставлял
/// человека перед пустым кабинетом, который ещё не успел ничего получить.
class _Ceremony extends StatefulWidget {
  const _Ceremony({required this.onDone});

  final VoidCallback onDone;

  @override
  State<_Ceremony> createState() => _CeremonyState();
}

class _CeremonyState extends State<_Ceremony> {
  int _beat = 1;
  bool _stopped = false;

  @override
  void initState() {
    super.initState();
    _play();
  }

  @override
  void dispose() {
    _stopped = true;
    super.dispose();
  }

  Future<void> _play() async {
    for (var next = 2; next <= 8; next++) {
      await Future<void>.delayed(const Duration(milliseconds: 1150));
      if (_stopped || !mounted) return;
      setState(() => _beat = next);
      HapticFeedback.selectionClick();
    }
    await Future<void>.delayed(const Duration(milliseconds: 1400));
    if (_stopped || !mounted) return;
    HapticFeedback.heavyImpact();
    widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(
          AlmaMetrics.pad, 0, AlmaMetrics.pad, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: 360,
            width: double.infinity,
            // Рисунок один на всю церемонию и не меняется с ударом: восемь
            // разных картинок за девять секунд читались бы как мигание.
            child: Center(child: WritingArt(size: 300, seed: 7)),
          ),
          // Резерв под самую длинную из восьми строк: без него рисунок
          // прыгал бы вверх на каждой, что переносится на третью строку.
          ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 116),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_label(l, _beat).toUpperCase(), style: AlmaType.overline),
                const SizedBox(height: 14),
                Text(
                  _line(l, _beat),
                  style: AlmaType.displayL.copyWith(
                      fontSize: 22, fontStyle: FontStyle.italic, height: 1.32),
                ),
              ],
            ),
          ),
          const Spacer(),
          // Восемь полосок: сколько прошло и сколько осталось, без процентов
          // и без вращающегося круга.
          Row(children: [
            for (var i = 1; i <= 8; i++) ...[
              Expanded(
                child: AnimatedContainer(
                  duration: AlmaMotion.ui,
                  height: 2,
                  color: i <= _beat
                      ? AlmaPalette.gold
                      : AlmaPalette.body.withValues(alpha: 0.16),
                ),
              ),
              if (i < 8) const SizedBox(width: 5),
            ],
          ]),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  static String _label(L l, int beat) => switch (beat) {
        1 => l.journeyCeremony1Label,
        2 => l.journeyCeremony2Label,
        3 => l.journeyCeremony3Label,
        4 => l.journeyCeremony4Label,
        5 => l.journeyCeremony5Label,
        6 => l.journeyCeremony6Label,
        7 => l.journeyCeremony7Label,
        _ => l.journeyCeremony8Label,
      };

  static String _line(L l, int beat) => switch (beat) {
        1 => l.journeyCeremony1Line,
        2 => l.journeyCeremony2Line,
        3 => l.journeyCeremony3Line,
        4 => l.journeyCeremony4Line,
        5 => l.journeyCeremony5Line,
        6 => l.journeyCeremony6Line,
        7 => l.journeyCeremony7Line,
        _ => l.journeyCeremony8Line,
      };
}
