import 'package:flutter/material.dart';

import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';

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

enum _Step { name, about, date, time, place }

class _JourneyScreenState extends State<JourneyScreen> {
  _Step _step = _Step.name;

  final _name = TextEditingController();
  String? _gender;
  int _day = 1, _month = 1, _year = 2000;
  int _hour = 12, _minute = 0;
  bool _timeUnknown = false;
  final _placeQuery = TextEditingController();
  List<Place> _places = const [];
  Place? _place;
  bool _saving = false;
  String? _failure;

  @override
  void dispose() {
    _name.dispose();
    _placeQuery.dispose();
    super.dispose();
  }

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
      await session.client.saveProfile(BirthInput(
        birthDate:
            '${_year.toString().padLeft(4, '0')}-${_month.toString().padLeft(2, '0')}-${_day.toString().padLeft(2, '0')}',
        birthTime: _timeUnknown
            ? null
            : '${_hour.toString().padLeft(2, '0')}:${_minute.toString().padLeft(2, '0')}',
        latitude: place.latitude,
        longitude: place.longitude,
        timezone: place.timezone,
        placeLabel: place.label,
        placeId: place.id,
        name: _name.text.trim().isEmpty ? null : _name.text.trim(),
      ));
      if (_name.text.trim().isNotEmpty) {
        await session.client.setDisplayName(_name.text.trim());
      }
      await session.start(force: true);
      if (mounted) widget.onDone();
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
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const SizedBox(height: 12),
              Row(children: [
                // «I / VI» — римскими, как на нативных экранах.
                Text(
                  '${_roman(_step.index + 1)} / VI',
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

  static String _roman(int n) => const ['I', 'II', 'III', 'IV', 'V', 'VI'][n - 1];

  List<Widget> _stepBody(L l) => switch (_step) {
        _Step.name => [
            Text(l.journeyNameTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyNameSub, style: AlmaType.meta),
            const SizedBox(height: 24),
            _field(_name, l.journeyNamePlaceholder),
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
            Row(children: [
              _numberField(l.journeyCaptureDayShort, _day, 1, 31,
                  (v) => setState(() => _day = v)),
              const SizedBox(width: 10),
              _numberField(l.journeyCaptureMonthShort, _month, 1, 12,
                  (v) => setState(() => _month = v)),
              const SizedBox(width: 10),
              _numberField(l.journeyCaptureYearShort, _year, 1900, 2026,
                  (v) => setState(() => _year = v)),
            ]),
          ],
        _Step.time => [
            Text(l.journeyTimeTitle, style: AlmaType.displayL),
            const SizedBox(height: 24),
            if (!_timeUnknown)
              Row(children: [
                _numberField(l.journeyHourLabel, _hour, 0, 23,
                    (v) => setState(() => _hour = v)),
                const SizedBox(width: 10),
                _numberField(l.journeyMinuteLabel, _minute, 0, 59,
                    (v) => setState(() => _minute = v)),
              ]),
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
      };

  Widget _cta(L l) {
    final isLast = _step == _Step.place;
    final enabled = !_saving && (!isLast || _place != null);
    return SizedBox(
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

  Widget _numberField(
      String label, int value, int min, int max, ValueChanged<int> onChanged) {
    final controller = TextEditingController(text: value.toString());
    return Expanded(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: AlmaType.meta),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            border: Border.all(color: AlmaPalette.hairlineGold),
            borderRadius: BorderRadius.circular(12),
          ),
          child: TextField(
            controller: controller,
            keyboardType: TextInputType.number,
            style: AlmaType.numeral.copyWith(fontSize: 18),
            decoration: const InputDecoration(border: InputBorder.none),
            onChanged: (text) {
              final parsed = int.tryParse(text);
              if (parsed != null && parsed >= min && parsed <= max) {
                onChanged(parsed);
              }
            },
          ),
        ),
      ]),
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
