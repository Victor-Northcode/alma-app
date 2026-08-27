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
///
/// **Это единственный источник языка, и сервер идёт за ним.** До 26 августа
/// выбор здесь только выключал синхронизацию с телефоном в
/// `AlmaSession._adoptLocaleFromDevice` — и больше ничего: серверный язык
/// оставался тем, что записал последний удачный PATCH. Вход в аккаунт подменял
/// аккаунт серверным с языком по умолчанию `en`, и владелец получил русский
/// интерфейс с английскими главами на английском телефоне. Теперь сессия
/// считает язык отсюда (`AlmaSession.locale`) и выталкивает его на сервер на
/// каждом старте.
class LocaleOverride {
  const LocaleOverride._();

  static const _key = 'alma.locale.override';

  /// Что выбрал человек. Слушает `MaterialApp` — смена перестраивает всё
  /// приложение сразу, без перезапуска.
  static final ValueNotifier<Locale?> value = ValueNotifier<Locale?>(null);

  /// Поднять сохранённый выбор с диска. Зовётся из `main()` без ожидания, как
  /// `PaywallGuard.restore`: первый кадр может выйти на языке телефона и тут же
  /// перестроиться — это дешевле, чем держать запуск на диске.
  ///
  /// Сессия ждёт этот же вызов перед тем, как сообщить серверу язык, — иначе
  /// старт, обогнавший диск, записал бы на сервер язык телефона поверх
  /// выбранного человеком. Диск читается на каждом вызове, а не однажды:
  /// запомненное будущее, созданное в зоне FakeAsync одного виджет-теста,
  /// второй тест того же файла ждал вечно — 35 таймаутов по десять минут
  /// (27.08.2026). Выбор, уже стоящий в памяти, диск не перебивает: память
  /// новее диска ровно в ту секунду, когда [set] ещё пишет.
  static Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    if (value.value != null) return;
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

  /// Выбранный язык кодом каталога сервера, или `null`, когда выбора нет.
  static String? get serverCode {
    final chosen = value.value;
    return chosen == null ? null : serverCodeOf(chosen);
  }

  /// Код ARB → код сервера. Единственное расхождение — португальский: у ARB
  /// он просто `pt`, у каталога сервера — `pt-BR`.
  static String serverCodeOf(Locale locale) =>
      locale.languageCode == 'pt' ? 'pt-BR' : locale.languageCode;

  /// Код сервера → локаль ARB, обратно к [serverCodeOf].
  static Locale localeOf(String code) =>
      code == 'pt-BR' ? const Locale('pt') : Locale(code);

  /// Забыть выбор между тестами.
  @visibleForTesting
  static void reset() => value.value = null;
}
