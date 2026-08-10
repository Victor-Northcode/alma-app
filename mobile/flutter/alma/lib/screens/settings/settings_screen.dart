import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../state/session.dart';

/// Настройки.
///
/// Порт `mobile/ios/Alma/Screens/Settings/SettingsScreen.swift`, теперь по
/// кадрам нативного экрана, а не по памяти. Первый порт собрал те же данные
/// **не теми элементами** — пилюлями там, где у натива строки списка, — и
/// владелец назвал его кривым справедливо.
///
/// Порядок разделов нативный: аккаунт → данные рождения → каждое утро → язык →
/// план → данные и документы.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  Map<String, dynamic>? _daily;
  Map<String, dynamic>? _plan;
  bool _started = false;

  /// Адрес сайта для юридических документов.
  ///
  /// На нативных сборках он же; домен пока не резолвится, и это записано в
  /// docs/PARITY.md отдельной строкой — Play требует работающую ссылку на
  /// политику. Здесь он назван один раз, чтобы менять его в одном месте.
  static const _site = 'https://alma.pazl.ai';

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

  /// Выбор уходит на сервер, экран верит себе сразу — та же оптимистика, что у
  /// языка на iOS.
  Future<void> _setDaily({String? daily, int? hour}) async {
    final updated = Map<String, dynamic>.from(_daily ?? {});
    if (daily != null) updated['daily'] = daily;
    if (hour != null) updated['hour'] = hour;
    setState(() => _daily = updated);
    try {
      final server =
          await SessionScope.of(context).client.setDaily(daily: daily, hour: hour);
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
        _Section(label: l.cabAccountLabel, children: [
          const SizedBox(height: 14),
          Text(
            account?.displayName?.isNotEmpty == true
                ? account!.displayName!
                : l.cabGuest,
            style: AlmaType.headingM.copyWith(fontSize: 22),
          ),
          if (account?.email != null) ...[
            const SizedBox(height: 4),
            Text(account!.email!, style: AlmaType.meta),
          ],
          if (account?.isGuest ?? true) ...[
            const SizedBox(height: 14),
            // Честное состояние, а не упрёк: карта живёт на этом телефоне, вход
            // делает её долговечной.
            Text(l.cabGuestNoteApp, style: AlmaType.meta),
            const SizedBox(height: 16),
            // По содержимому и слева, как на нативе: кнопка во всю ширину
            // читается как главное действие экрана, а вход здесь — предложение.
            Align(
              alignment: Alignment.centerLeft,
              child: _OutlineButton(label: l.cabSignIn, onTap: () {}),
            ),
          ],
        ]),
        if (profile != null)
          _Section(label: l.cabBirthDataLabel, children: [
            _Row(label: l.cabSettingsDate, value: _civilDate(l.localeName, profile.birthDate)),
            _Row(
              label: l.cabSettingsTime,
              value: profile.birthTime == null
                  ? l.cabUnknownTime
                  : '${profile.birthTime} · ${profile.timezone}',
            ),
            if (profile.placeLabel != null)
              _Row(label: l.cabSettingsPlace, value: profile.placeLabel!),
            if (profile.name != null)
              _Row(label: l.cabSettingsFullName, value: profile.name!),
          ]),
        ..._everyMorning(l),
        _Section(label: l.cabSettingsLanguage, children: [
          // Строка-действие, а не переключатель: язык живёт в настройках
          // телефона, и приложение отправляет туда, а не заводит вторую ручку.
          _Row(
            label: _endonym(session.locale),
            value: l.cabSettingsInterfaceLanguageAction,
            arrow: true,
            onTap: () => launchUrl(Uri.parse('app-settings:'),
                mode: LaunchMode.externalApplication),
          ),
        ]),
        ..._planSection(l),
        _Section(label: l.cabDataAndLegal, children: [
          for (final (label, path) in [
            (l.cabLegalTerms, 'terms'),
            (l.cabLegalPrivacy, 'privacy'),
            (l.cabLegalRefunds, 'refunds'),
            (l.cabLegalSubscriptionTerms, 'subscription-terms'),
            (l.cabLegalImprint, 'imprint'),
          ])
            _Row(
              label: label,
              value: '',
              arrow: true,
              onTap: () => launchUrl(Uri.parse('$_site/$path'),
                  mode: LaunchMode.externalApplication),
            ),
        ]),
      ],
    );
  }

  /// «Каждое утро» — тремя строками списка с галочкой, как у натива, а не
  /// пилюлями. Под ними пояснение выбранного режима, строка часа, тихие часы,
  /// пояс устройства и счётчик точных дней.
  List<Widget> _everyMorning(L l) {
    final daily = _daily;
    if (daily == null) return const [];
    final mode = daily['daily'] as String? ?? 'off';
    final hour = (daily['hour'] as num?)?.toInt() ?? 10;
    final zone = daily['timezone'] as String?;
    final verified = (daily['verified_days'] as num?)?.toInt();

    return [
      _Section(label: l.dailySettingTitle, children: [
        for (final (value, label) in [
          ('off', l.dailySettingOff),
          ('occasional', l.dailySettingOccasionally),
          ('important', l.dailySettingOnlyWhatMatters),
        ])
          _Row(
            label: label,
            value: '',
            checked: mode == value,
            onTap: () => _setDaily(daily: value),
          ),
        if (mode != 'off') ...[
          const SizedBox(height: 14),
          Text(
            mode == 'occasional'
                ? l.dailySettingOccasionallyDetail
                : l.dailySettingOnlyMattersDetail,
            style: AlmaType.meta,
          ),
          const SizedBox(height: 14),
          // Час — одна строка со значением и шагом вверх-вниз, как на нативе.
          // Четырнадцать пилюль занимали пол-экрана ради одного числа.
          _HourRow(
            label: l.dailySettingHour,
            hour: hour,
            onChange: (value) => _setDaily(hour: value),
          ),
          const SizedBox(height: 12),
          Text(l.dailySettingQuiet, style: AlmaType.meta),
          const SizedBox(height: 6),
          if (zone != null)
            _Row(
              label: l.dailySettingTimezone,
              value: zone,
              caption: l.dailySettingTimezoneDevice,
            ),
          if (verified != null)
            _Row(label: l.dailyVerifiedLabel, value: '$verified'),
        ],
      ]),
    ];
  }

  List<Widget> _planSection(L l) {
    final plan = _plan;
    if (plan == null) return const [];
    final rows = (plan['entitlements'] as List? ?? const [])
        .whereType<Map>()
        .map((e) => e.cast<String, dynamic>())
        .toList();
    return [
      _Section(label: l.cabSettingsPlan, children: [
        if (rows.isEmpty) ...[
          _Row(label: l.cabPlanFreePlan, value: ''),
          const SizedBox(height: 12),
          Text(l.cabPlanFreeNote, style: AlmaType.meta),
        ] else
          for (final row in rows)
            _Row(
              label: row['system'] == 'all'
                  ? l.cabSettingsEverythingMonthly
                  : (row['system'] as String? ?? ''),
              value: row['expires_at'] is String
                  ? l.cabPlanRunsUntil(_civilDate(
                      l.localeName, (row['expires_at'] as String).split('T').first))
                  : '',
            ),
      ]),
    ];
  }

  /// Гражданская дата — не мгновение. «1992-05-11» без пояса; разбор её как
  /// времени в поясе устройства делал бы её десятым мая для всех западнее
  /// Лондона.
  String _civilDate(String locale, String civil) {
    final parts = civil.split('-');
    if (parts.length != 3) return civil;
    final date =
        DateTime.utc(int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
    return DateFormat.yMMMMd(locale).format(date);
  }
}

/// Раздел: золотая подпись, гаснущая линейка и строки под ней.
class _Section extends StatelessWidget {
  const _Section({required this.label, required this.children});

  final String label;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 30),
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
}

/// Одна строка: подпись слева, значение справа, волосяная линия снизу.
///
/// Умеет четыре вида, все четыре есть у натива: значение, значение с подписью
/// под ним, галочка выбора и стрелка действия.
class _Row extends StatelessWidget {
  const _Row({
    required this.label,
    required this.value,
    this.caption,
    this.checked = false,
    this.arrow = false,
    this.onTap,
  });

  final String label;
  final String value;
  final String? caption;
  final bool checked;
  final bool arrow;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final row = Container(
      padding: const EdgeInsets.symmetric(vertical: 15),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
        Expanded(
          child: Text(
            label,
            style: checked || onTap != null && value.isEmpty
                ? AlmaType.body.copyWith(color: AlmaPalette.inkLight, fontSize: 17)
                : AlmaType.meta.copyWith(fontSize: 15),
          ),
        ),
        const SizedBox(width: 16),
        if (value.isNotEmpty)
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Значение — светлым текстовым, а не золотым засечным.
                // Засечное золото на этом экране принадлежит числам карты
                // (градусы, римские цифры), а дата рождения и город — обычные
                // факты, и натив набирает их так же, как подписи.
                Text(value,
                    style: arrow
                        ? AlmaType.meta.copyWith(color: AlmaPalette.gold, fontSize: 15)
                        : AlmaType.body
                            .copyWith(color: AlmaPalette.inkLight, fontSize: 17),
                    textAlign: TextAlign.end),
                if (caption != null)
                  Text(caption!,
                      style: AlmaType.meta.copyWith(fontSize: 12),
                      textAlign: TextAlign.end),
              ],
            ),
          ),
        if (checked) ...[
          const SizedBox(width: 10),
          const Text('✓', style: TextStyle(color: AlmaPalette.gold, fontSize: 17)),
        ],
        if (arrow) ...[
          const SizedBox(width: 8),
          const Text('↗', style: TextStyle(color: AlmaPalette.gold, fontSize: 15)),
        ],
      ]),
    );
    if (onTap == null) return row;
    return InkWell(onTap: onTap, child: row);
  }
}

/// «Приходит в 10:00 ⌃⌄» — час с шагом вверх и вниз, в границах тихих часов.
class _HourRow extends StatelessWidget {
  const _HourRow(
      {required this.label, required this.hour, required this.onChange});

  final String label;
  final int hour;
  final ValueChanged<int> onChange;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 15),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(children: [
        Expanded(child: Text(label, style: AlmaType.meta)),
        Text('${hour.toString().padLeft(2, '0')}:00',
            style: AlmaType.numeral.copyWith(fontSize: 18)),
        const SizedBox(width: 8),
        Column(mainAxisSize: MainAxisSize.min, children: [
          // Никогда ночью: восемь утра и девять вечера — границы, за которые
          // шаг не выпускает. Тот же договор, что печатает строка тихих часов.
          _Step(glyph: '⌃', onTap: hour < 21 ? () => onChange(hour + 1) : null),
          _Step(glyph: '⌄', onTap: hour > 8 ? () => onChange(hour - 1) : null),
        ]),
      ]),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.glyph, this.onTap});

  final String glyph;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkResponse(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        child: Text(
          glyph,
          style: TextStyle(
            fontSize: 13,
            color: onTap == null
                ? AlmaPalette.muted3.withValues(alpha: 0.4)
                : AlmaPalette.gold,
          ),
        ),
      ),
    );
  }
}

/// Обведённая кнопка — «Войти». Тот же вид, что на нативном экране: золотой
/// контур на ночи, без заливки.
class _OutlineButton extends StatelessWidget {
  const _OutlineButton({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(28),
      // Без `alignment`: Container с выравниванием раздувается до максимума
      // доступной ширины, и кнопка растягивалась во весь экран, хотя на нативе
      // она по содержимому. Размер задаёт padding.
      child: Container(
        height: 54,
        padding: const EdgeInsets.symmetric(horizontal: 34),
        decoration: BoxDecoration(
          border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.55)),
          borderRadius: BorderRadius.circular(28),
        ),
        child: Center(
          widthFactor: 1,
          child: Text(label,
              style: AlmaType.button.copyWith(color: AlmaPalette.goldBright)),
        ),
      ),
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
