import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../state/session.dart';

/// Настройки.
///
/// Порт `mobile/ios/Alma/Screens/Settings/SettingsScreen.swift` в его
/// структуре: аккаунт с честным состоянием гостя, данные рождения, язык.
/// Тариф, выгрузка, юридические документы и удаление аккаунта приедут вместе
/// с покупками — они опираются на биллинг, которого в порте ещё нет, и
/// рисовать их без действия значило бы обещать кнопкой то, что не работает.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  Map<String, dynamic>? _daily;
  Map<String, dynamic>? _plan;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      final client = SessionScope.of(context).client;
      client.dailySettings().then((d) {
        if (mounted) setState(() => _daily = d);
      }).catchError((Object _) {});
      client.entitlements().then((e) {
        if (mounted) setState(() => _plan = e);
      }).catchError((Object _) {});
    }
  }

  /// Частота утреннего письма: выбор уходит на сервер, экран верит себе сразу —
  /// та же оптимистика, что у языка на iOS.
  Future<void> _setDaily({String? daily, int? hour}) async {
    final updated = Map<String, dynamic>.from(_daily ?? {});
    if (daily != null) updated['daily'] = daily;
    if (hour != null) updated['hour'] = hour;
    setState(() => _daily = updated);
    try {
      final server = await SessionScope.of(context)
          .client
          .setDaily(daily: daily, hour: hour);
      if (mounted) setState(() => _daily = server);
    } on AlmaError {
      // Экран уже показывает выбор; сервер догонит при следующем открытии.
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final l = L.of(context);
    final account = session.account;
    final profile = session.profile;

    return ScreenScaffold(
      seed: 0x53455454,
      title: l.cabSettingsTitle,
      children: [
        const SizedBox(height: 6),
        _section(l.cabAccountLabel, [
          Padding(
            padding: const EdgeInsets.only(top: 14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(
                account?.displayName?.isNotEmpty == true
                    ? account!.displayName!
                    : l.cabGuest,
                style: AlmaType.headingM,
              ),
              if (account?.email != null) ...[
                const SizedBox(height: 3),
                Text(account!.email!, style: AlmaType.meta),
              ],
              if (account?.isGuest ?? true) ...[
                const SizedBox(height: 8),
                // Честное состояние, а не упрёк: карта живёт на этом
                // телефоне, вход делает её долговечной.
                Text(l.cabGuestNoteApp, style: AlmaType.meta),
              ],
            ]),
          ),
        ]),
        if (profile != null)
          _section(l.cabBirthDataLabel, [
            _row(l.cabSettingsDate, _civilDate(l.localeName, profile.birthDate)),
            _row(
              l.cabSettingsTime,
              profile.birthTime == null
                  ? l.cabUnknownTime
                  : '${profile.birthTime} · ${profile.timezone}',
            ),
            if (profile.placeLabel != null)
              _row(l.cabSettingsPlace, profile.placeLabel!),
            if (profile.name != null)
              _row(l.cabSettingsFullName, profile.name!),
          ]),
        ..._everyMorning(l),
        ..._planSection(l),
        // Язык — это язык телефона, и переключателя здесь нет намеренно:
        // финальный iOS показывает текущий эндоним и говорит «Я читаю и пишу
        // на языке твоего телефона. Поменяй его там — поменяюсь и я».
        // Переключатель-пилюли был андроидным обходом API 33 и ушёл вместе с
        // Android.
        _section(l.cabSettingsLanguage, [
          _row(l.cabSettingsLanguage, _endonym(session.locale)),
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(l.cabLanguageNote, style: AlmaType.meta),
          ),
        ]),
      ],
    );
  }

  /// «Каждое утро»: Выключено / Иногда / Только важное, час прихода и тихие
  /// часы. Структура нативного блока; сами пуши приедут с нативным плагином,
  /// а выбор уже настоящий — он хранится на сервере.
  List<Widget> _everyMorning(L l) {
    final daily = _daily;
    if (daily == null) return const [];
    final mode = daily['daily'] as String? ?? 'off';
    final hour = (daily['hour'] as num?)?.toInt() ?? 10;
    return [
      _section(l.dailySettingTitle, [
        Padding(
          padding: const EdgeInsets.only(top: 14),
          child: Wrap(spacing: 8, runSpacing: 8, children: [
            for (final (value, label) in [
              ('off', l.dailySettingOff),
              ('occasional', l.dailySettingOccasionally),
              ('important', l.dailySettingOnlyWhatMatters),
            ])
              _pill(label, selected: mode == value, onTap: () => _setDaily(daily: value)),
          ]),
        ),
        if (mode != 'off') ...[
          const SizedBox(height: 10),
          Text(
            mode == 'occasional'
                ? l.dailySettingOccasionallyDetail
                : l.dailySettingOnlyMattersDetail,
            style: AlmaType.meta,
          ),
          const SizedBox(height: 18),
          Text(l.dailySettingHour.toUpperCase(), style: AlmaType.overline),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (var h = 8; h <= 21; h++)
              _pill('${h.toString().padLeft(2, '0')}:00',
                  selected: hour == h, onTap: () => _setDaily(hour: h)),
          ]),
          const SizedBox(height: 10),
          Text(l.dailySettingQuiet, style: AlmaType.meta),
        ],
      ]),
    ];
  }

  /// План: что открыто и до какого числа — правда с сервера, не кнопка
  /// покупки. Дверь тарифа приедет с магазинами.
  List<Widget> _planSection(L l) {
    final plan = _plan;
    if (plan == null) return const [];
    final rows = (plan['entitlements'] as List? ?? const [])
        .whereType<Map>()
        .map((e) => e.cast<String, dynamic>())
        .toList();
    return [
      _section(l.cabSettingsPlan, [
        if (rows.isEmpty)
          _row(l.cabPlanFreePlan, '')
        else
          for (final row in rows)
            _row(
              row['system'] == 'all'
                  ? l.cabSettingsEverythingMonthly
                  : (row['system'] as String? ?? ''),
              row['expires_at'] is String
                  ? l.cabPlanRunsUntil(_civilDate(
                      l.localeName, (row['expires_at'] as String).split('T').first))
                  : '',
            ),
        if (rows.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(l.cabPlanFreeNote, style: AlmaType.meta),
          ),
      ]),
    ];
  }

  Widget _pill(String label, {required bool selected, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          border: Border.all(
              color: selected ? AlmaPalette.gold : AlmaPalette.hairline),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label,
            style: AlmaType.meta.copyWith(
                color: selected ? AlmaPalette.goldBright : AlmaPalette.muted)),
      ),
    );
  }

  /// Гражданская дата — не мгновение. «1992-05-11» без пояса; разбор её как
  /// времени в поясе устройства делал бы её десятым мая для всех западнее
  /// Лондона.
  String _civilDate(String locale, String civil) {
    final parts = civil.split('-');
    if (parts.length != 3) return civil;
    final date = DateTime.utc(
        int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
    return DateFormat.yMMMMd(locale).format(date);
  }

  Widget _section(String label, List<Widget> children) {
    return Padding(
      padding: const EdgeInsets.only(top: 26),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(label.toUpperCase(), style: AlmaType.overline),
          const SizedBox(width: 12),
          Expanded(
            child: Container(
              height: 1,
              decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
            ),
          ),
        ]),
        ...children,
      ]),
    );
  }

  Widget _row(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(children: [
        Text(label, style: AlmaType.meta),
        const Spacer(),
        Flexible(
          child: Text(value,
              style: AlmaType.numeral.copyWith(fontSize: 16),
              textAlign: TextAlign.end),
        ),
      ]),
    );
  }
}

/// Эндоним — имя языка на нём самом, и оно не переводится никогда.
String _endonym(String code) => switch (code) {
      'en' => 'English',
      'es' => 'Español',
      'de' => 'Deutsch',
      'it' => 'Italiano',
      'fr' => 'Français',
      'pt-BR' => 'Português',
      'ru' => 'Русский',
      _ => code,
    };
