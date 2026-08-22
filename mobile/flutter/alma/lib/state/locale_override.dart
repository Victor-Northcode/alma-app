import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Язык, который человек выбрал сам, — поверх языка телефона.
///
/// До 22 августа второй ручки не было принципиально: язык — это язык телефона,
/// строка в настройках вела в системные настройки. Владелец решил иначе: «хочу
/// чтоб язык можно было поменять самому, выбрать в выпадающей фигне». Ручка
/// одна на приложение и живёт здесь, а не в сессии: сессия — про сервер, эта
/// вещь — про `MaterialApp.locale`.
///
/// `null` — переопределения нет, интерфейс следует за телефоном, как раньше.
/// Пока переопределение стоит, `AlmaSession._adoptLocaleFromDevice` молчит —
/// иначе каждый запуск затирал бы выбор человека языком устройства.
class LocaleOverride {
  const LocaleOverride._();

  static const _key = 'alma.locale.override';

  /// Что выбрал человек. Слушает `MaterialApp` — смена перестраивает всё
  /// приложение сразу, без перезапуска.
  static final ValueNotifier<Locale?> value = ValueNotifier<Locale?>(null);

  /// Поднять сохранённый выбор с диска. Зовётся из `main()` без ожидания, как
  /// `PaywallGuard.restore`: первый кадр может выйти на языке телефона и тут же
  /// перестроиться — это дешевле, чем держать запуск на диске.
  static Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    final tag = prefs.getString(_key);
    if (tag == null || tag.isEmpty) return;
    final parts = tag.split('-');
    value.value = parts.length > 1
        ? Locale(parts.first, parts.last)
        : Locale(parts.first);
  }

  /// Записать выбор. `null` возвращает интерфейс за телефоном.
  static Future<void> set(Locale? locale) async {
    value.value = locale;
    final prefs = await SharedPreferences.getInstance();
    if (locale == null) {
      await prefs.remove(_key);
    } else {
      await prefs.setString(_key, locale.toLanguageTag());
    }
  }
}
