import 'dart:async' show unawaited;

import 'package:flutter/widgets.dart';
import '../design/plates.dart';

import '../net/alma_client.dart';
import '../notify/push_devices.dart';
import '../net/models.dart';
import 'locale_override.dart';

/// Что приложение знает о том, кто его открыл.
///
/// Порт `mobile/ios/Alma/State/AlmaSessionModel.swift`.
///
/// **Аккаунт настоящий с первого запроса.** Гость — это не «ещё не
/// зарегистрировался», а полноправная строка на сервере, у которой есть карта и
/// могут быть покупки. Вход добавляет к ней имя и делает её долговечной, а не
/// создаёт заново — поэтому здесь нет состояния «не вошёл, значит ничего нет».
class AlmaSession extends ChangeNotifier {
  AlmaSession(this.client)
      : plates = PlateStore(baseUrl: client.baseUrl);

  final AlmaClient client;

  /// Склад вклеек глав.
  ///
  /// **Живёт на сессии, а не на экране главы.** Диск-кэш имеет смысл ровно
  /// потому, что переживает уход с экрана: картина в 620×780 скачивается один
  /// раз за установку, а глава открывается и закрывается десятки раз. Store,
  /// созданный экраном, качал бы её заново на каждый вход.
  final PlateStore plates;

  AlmaAccount? _account;
  Profile? _profile;

  /// Что аккаунт держит: открытые системы и сами права.
  ///
  /// Нужно ровно для того, чтобы не звать покупать того, кто уже заплатил —
  /// приглашение подписчику это не продажа, а неловкость, — и чтобы лестница
  /// не показывала ступень, которая ничего не добавит.
  Entitlements _rights = const Entitlements.none();
  List<Profile> _people = const [];
  Hub? _hub;
  bool _ready = false;
  AlmaError? _failure;

  AlmaAccount? get account => _account;
  Profile? get profile => _profile;
  Entitlements get entitlements => _rights;
  bool get isSubscriber => _rights.hasPlan;
  List<Profile> get people => _people;
  Hub? get hub => _hub;
  bool get ready => _ready;
  AlmaError? get failure => _failure;

  bool get hasBirthData => _profile != null;

  /// Язык приложения — один на интерфейс и на всё, что пишет Alma.
  ///
  /// Выбранный в настройках (`LocaleOverride`), иначе язык телефона. **Не
  /// `account.locale`**: серверная запись — это копия, которую сессия
  /// поддерживает ([_adoptLocale]), а не источник. Пока источником был
  /// аккаунт, вход подменял его серверным с языком по умолчанию `en`, и
  /// владелец получил русский интерфейс с английскими главами (26.08.2026).
  /// Запросы несут этот язык явно, так что даже неудавшийся PATCH не
  /// переведёт главы на чужой язык.
  String get locale => LocaleOverride.appLanguage();

  /// Ждёт, пока сессия узнает, кто перед ней.
  ///
  /// **Нужно ровно одному месту — магазину.** StoreKit переотдаёт незавершённые
  /// покупки в первые же миллисекунды запуска, а `start()` в этот момент ещё
  /// летит: покупка ушла бы на сервер без токена, сервер завёл бы под неё
  /// нового гостя, и оплаченная глава открылась бы у аккаунта, которого человек
  /// никогда не увидит. Дважды выданной она уже не будет — `already_claimed`.
  Future<void> whenReady() async {
    if (_ready) return;
    final running = _starting ??= start().whenComplete(() => _starting = null);
    await running;
  }

  Future<void>? _starting;

  Future<void> start({bool force = false}) async {
    if (_ready && !force) return;
    _failure = null;
    try {
      // Сессия сама создаёт гостя, если его ещё нет: до этой строки у человека
      // не было аккаунта, после — есть, и он ничего для этого не делал.
      if (!await client.hasAccount) await client.refresh();
      _account = await client.account();
      // Диск с выбранным языком читается один раз и обычно давно прочитан —
      // но старт, обогнавший его, записал бы на сервер язык телефона поверх
      // выбранного человеком.
      await LocaleOverride.restore();
      // Старт сервера не ждёт: язык уже принят.
      unawaited(_adoptLocale());
      final all = await client.profiles();
      _profile = all.where((p) => p.isSelf).firstOrNull;
      _people = all.where((p) => !p.isSelf).toList();
      // Хаб — первой странице систем, одним запросом; без рождения его нет,
      // и это состояние, а не ошибка.
      _hub = _profile == null ? null : await client.hub();
      // Права — отдельным тихим запросом: витрина не должна падать оттого,
      // что кошелёк не ответил.
      await refreshRights();
      _ready = true;
    } on AlmaError catch (error) {
      _failure = error;
      _ready = true;
    } catch (error) {
      // Не только AlmaError: PlatformException из хранилища токенов или
      // ошибка разбора модели вышли бы мимо ветки выше — `_ready` не
      // выставлен, `notifyListeners` не позван, и приложение стояло бы на
      // заставке вечно, без ошибки и без кнопки повтора (ревью 27.08.2026).
      // Экрану отдаётся тот же типизированный отказ, что и сети: у него уже
      // есть и текст, и «попробовать ещё раз».
      _failure = NetworkDown(error.toString());
      _ready = true;
    }
    notifyListeners();
  }

  /// Перечитать права.
  ///
  /// Отдельным методом, потому что после покупки это первое, что обязано
  /// произойти: сервер записал право, и до тех пор, пока клиент его не
  /// перечитал, купленная глава остаётся закрытой на экране у того, кто за неё
  /// заплатил. Молча при отказе — витрина не должна падать оттого, что кошелёк
  /// не ответил, а старые права всё ещё вернее пустых.
  Future<void> refreshRights() async {
    try {
      _rights = Entitlements.fromJson(await client.entitlements());
      notifyListeners();
    } on AlmaError {
      // Молча: что было известно, то и остаётся известным.
    }
  }

  /// **Приложение побеждает, сервер догоняет.** Порт `adoptLocaleFromDevice`
  /// с iOS, где язык — это язык телефона. Гостя сервер заводит по заголовку
  /// первого запроса, и тот бывает чужим — живой гость в браузере получил
  /// итальянский; человек, сменивший язык телефона после установки, писался бы
  /// по-старому вечно. А вход выдаёт аккаунт, заведённый сервером с его
  /// умолчанием `en`, — так главы и уехали на английский при русском
  /// интерфейсе (26.08.2026). Расхождение выталкивается на том запуске, который
  /// его заметил; запись — предпочтение, не факт: не ушла сейчас — уйдёт при
  /// следующем запуске. Серверная копия нужна не экрану, а утренней записи:
  /// её язык сервер берёт из аккаунта.
  Future<void> _adoptLocale() async {
    final current = _account;
    if (current == null) return;
    final wanted = locale;
    if (current.locale == wanted) return;
    _account = current.copyWith(locale: wanted);
    try {
      await client.setLocale(wanted);
    } catch (_) {
      // Молча — и не только AlmaError: вызов живёт в `unawaited(...)`, и
      // обрыв сети посреди чтения тела (`ClientException`) улетел бы
      // необработанной ошибкой зоны. Язык уже принят, сервер догонит на
      // следующем старте.
    }
  }

  /// Язык телефона — правило целиком в [LocaleOverride.deviceLanguage]:
  /// по всему списку предпочтений, незнакомый целиком список — английский.
  static String deviceLocale() => LocaleOverride.deviceLanguage();

  /// Телефон сменил язык на живом приложении — сервер узнаёт сразу.
  ///
  /// Интерфейсу ничего не нужно: `MaterialApp` без переопределения следует за
  /// системой сам, а `locale` читает телефон на каждом обращении. Отставала
  /// только серверная копия — до следующего запуска, то есть утренняя запись
  /// на Android приходила бы на прежнем языке (на iOS смена языка системы
  /// перезапускает приложение, и там это закрывал старт).
  void deviceLocaleChanged() {
    unawaited(_adoptLocale());
    // Экраны, читающие `locale`, обязаны перечитать содержимое.
    notifyListeners();
  }

  /// Человек выбрал язык в настройках: интерфейс подчиняется сразу, сервер
  /// узнаёт следом.
  ///
  /// **Язык телефона снимает переопределение.** Отдельной строки «как в
  /// телефоне» в списке нет, и не нужно: совпадение с телефоном и есть «как в
  /// телефоне». Иначе человек, однажды тронувший список, не вернул бы
  /// интерфейс за телефоном никогда — а владелец ждёт именно этого: «нужно
  /// подтягивать язык из системных настроек устройства» (26.08.2026).
  Future<void> chooseLanguage(String code) async {
    final own = code == deviceLocale() ? null : LocaleOverride.localeOf(code);
    await LocaleOverride.set(own);
    await _adoptLocale();
    // Пуш-регистрация несёт язык приложения — строка устройства на сервере
    // бьёт язык аккаунта при выборе языка пуша (`notify/daily.py`,
    // `notify/pair.py`), и без пересинхронизации пуши приходили бы на
    // прежнем языке до следующего запуска (ревью 27.08.2026).
    unawaited(AlmaPush.instance.sync(client));
    // Экраны, читающие `locale`, обязаны перечитать: главы, «Сегодня»,
    // галочка в списке.
    notifyListeners();
  }
}

/// Доступ к сессии из дерева.
class SessionScope extends InheritedNotifier<AlmaSession> {
  const SessionScope({super.key, required AlmaSession session, required super.child})
      : super(notifier: session);

  static AlmaSession of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<SessionScope>();
    assert(scope != null, 'SessionScope не найден выше по дереву');
    return scope!.notifier!;
  }
}

extension _FirstOrNull<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
