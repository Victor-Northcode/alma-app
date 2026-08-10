import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../state/session.dart';

/// Настройки.
///
/// Порт `mobile/ios/Alma/Screens/Settings/SettingsScreen.swift` в его
/// структуре: аккаунт с честным состоянием гостя, данные рождения, язык.
/// Тариф, выгрузка, юридические документы и удаление аккаунта приедут вместе
/// с покупками — они опираются на биллинг, которого в порте ещё нет, и
/// рисовать их без действия значило бы обещать кнопкой то, что не работает.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

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
