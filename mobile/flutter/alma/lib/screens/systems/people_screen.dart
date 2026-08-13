import 'package:flutter/material.dart';

import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/section_label.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';

/// Люди, с которыми сравнивают: список, добавление и удаление.
///
/// Порт `PeopleScreen.swift`. Без него совместимость недостижима в принципе —
/// сервер требует второго человека, а завести его было нечем: метод сохранения
/// с `isSelf: false` существовал в клиенте и не вызывался ниоткуда.
///
/// Форма нарочно короче анкеты: имя, дата, время (можно не знать) и место.
/// Пол здесь не спрашивают — он влияет на род в письме о *читателе*, а не о
/// том, с кем его сравнивают.
class PeopleScreen extends StatefulWidget {
  const PeopleScreen({super.key});

  @override
  State<PeopleScreen> createState() => _PeopleScreenState();
}

class _PeopleScreenState extends State<PeopleScreen> {
  final _name = TextEditingController();
  final _place = TextEditingController();
  int _day = 1, _month = 1, _year = 1990, _hour = 12, _minute = 0;
  bool _timeUnknown = false;
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
    final place = _chosen;
    if (place == null || _saving) return;
    final session = SessionScope.of(context);
    setState(() {
      _saving = true;
      _failure = null;
    });
    try {
      await session.client.saveProfile(
        BirthInput(
          birthDate: '${_year.toString().padLeft(4, '0')}-'
              '${_month.toString().padLeft(2, '0')}-'
              '${_day.toString().padLeft(2, '0')}',
          birthTime: _timeUnknown
              ? null
              : '${_hour.toString().padLeft(2, '0')}:${_minute.toString().padLeft(2, '0')}',
          latitude: place.latitude,
          longitude: place.longitude,
          timezone: place.timezone,
          placeLabel: place.label,
          placeId: place.id,
          name: _name.text.trim().isEmpty ? null : _name.text.trim(),
        ),
        // Ключевое слово всей этой страницы: это **не** владелец аккаунта.
        // `true` здесь стирает собственную карту человека вместе с главами.
        isSelf: false,
      );
      await session.start(force: true);
      if (mounted) {
        setState(() {
          _saving = false;
          _name.clear();
          _place.clear();
          _chosen = null;
          _found = const [];
        });
      }
    } on AlmaError catch (error) {
      if (mounted) {
        setState(() {
          _saving = false;
          _failure = error is ServerRefused && error.message.isNotEmpty
              ? error.message
              : null;
        });
      }
    }
  }

  Future<void> _remove(Profile person) async {
    final session = SessionScope.of(context);
    try {
      await session.client.deleteProfile(person.id);
      await session.start(force: true);
      if (mounted) setState(() {});
    } on AlmaError {
      if (mounted) setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final session = SessionScope.of(context);
    return ScreenScaffold(
      seed: 0x50454F50,
      title: l.cabPeopleTitle,
      children: [
        if (session.people.isNotEmpty) ...[
          SectionLabel(l.cabPeopleTitle, trailing: '${session.people.length}'),
          const SizedBox(height: 8),
          for (final person in session.people)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(children: [
                Expanded(
                  child: Text(
                    person.name?.isNotEmpty == true ? person.name! : person.birthDate,
                    style: AlmaType.body,
                  ),
                ),
                TextButton(
                  onPressed: () => _remove(person),
                  child: Text(l.cabPeopleRemove,
                      style: AlmaType.meta.copyWith(color: AlmaPalette.disagree)),
                ),
              ]),
            ),
          const SizedBox(height: AlmaMetrics.gapLarge),
        ],
        SectionLabel(l.cabPeopleAdd),
        const SizedBox(height: 12),
        _field(_name, l.journeyNamePlaceholder),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(child: _number(l.journeyCaptureDayShort, _day, 1, 31, (v) => setState(() => _day = v))),
          const SizedBox(width: 8),
          Expanded(child: _number(l.journeyCaptureMonthShort, _month, 1, 12, (v) => setState(() => _month = v))),
          const SizedBox(width: 8),
          Expanded(child: _number(l.journeyCaptureYearShort, _year, 1900, DateTime.now().year,
              (v) => setState(() => _year = v))),
        ]),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(child: _number(l.journeyHourLabel, _hour, 0, 23, (v) => setState(() => _hour = v))),
          const SizedBox(width: 8),
          Expanded(child: _number(l.journeyMinuteLabel, _minute, 0, 59, (v) => setState(() => _minute = v))),
        ]),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: _timeUnknown,
          activeThumbColor: AlmaPalette.gold,
          onChanged: (v) => setState(() => _timeUnknown = v),
          title: Text(l.cabUnknownTime, style: AlmaType.meta),
        ),
        _field(_place, l.journeyCaptureSearchPlace, onChanged: _search),
        for (final place in _found)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(place.label, style: AlmaType.meta),
            onTap: () => setState(() {
              _chosen = place;
              _place.text = place.label;
              _found = const [];
            }),
          ),
        if (_failure != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_failure!, style: AlmaType.meta),
          ),
        const SizedBox(height: 16),
        Opacity(
          opacity: _chosen == null || _saving ? 0.5 : 1,
          child: InkWell(
            onTap: _chosen == null || _saving ? null : _save,
            child: Container(
              height: 54,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: AlmaPalette.gold,
                borderRadius: BorderRadius.circular(28),
              ),
              child: Text(l.cabPeopleAdd,
                  style: AlmaType.button.copyWith(color: AlmaPalette.inkOnGold)),
            ),
          ),
        ),
      ],
    );
  }

  Widget _field(TextEditingController controller, String hint,
          {ValueChanged<String>? onChanged}) =>
      TextField(
        controller: controller,
        onChanged: onChanged,
        style: AlmaType.body,
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: AlmaType.meta,
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(28),
            borderSide: BorderSide(color: AlmaPalette.gold.withValues(alpha: 0.4)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(28),
            borderSide: BorderSide(color: AlmaPalette.gold.withValues(alpha: 0.8)),
          ),
        ),
      );

  /// Число крутится колесом платформы — тем же, что в анкете на Android.
  Widget _number(String label, int value, int min, int max, ValueChanged<int> onPick) =>
      InkWell(
        onTap: () async {
          final picked = await showModalBottomSheet<int>(
            context: context,
            backgroundColor: AlmaPalette.night700,
            builder: (context) => SizedBox(
              height: 240,
              child: ListView.builder(
                itemCount: max - min + 1,
                itemBuilder: (context, i) => ListTile(
                  title: Text('${min + i}',
                      textAlign: TextAlign.center, style: AlmaType.body),
                  onTap: () => Navigator.of(context).pop(min + i),
                ),
              ),
            ),
          );
          if (picked != null) onPick(picked);
        },
        child: Container(
          height: 54,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.4)),
            borderRadius: BorderRadius.circular(28),
          ),
          child: Text('$value', style: AlmaType.body),
        ),
      );
}
