import 'dart:ui' show PlatformDispatcher;

import 'package:flutter/widgets.dart';
import '../design/plates.dart';

import '../net/alma_client.dart';
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

  /// Язык, на котором сервер пишет. Не язык интерфейса.
  ///
  /// Это разные настройки, и стоит сказать почему: интерфейс говорит на языке
  /// телефона, а этот — на языке, который человек выбрал для **чтения**. На iOS
  /// они сведены вместе: устройство побеждает, и расхождение отправляется на
  /// сервер при первом запуске, который его заметил.
  String get locale => _account?.locale ?? 'en';

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
      _adoptLocaleFromDevice();
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

  /// **Устройство побеждает.** Порт `adoptLocaleFromDevice` с iOS: язык — это
  /// язык телефона, и никакой второй ручки в приложении нет. Гостя сервер
  /// заводит по заголовку первого запроса, и тот бывает чужим — живой гость в
  /// браузере получил итальянский; человек, сменивший язык телефона после
  /// установки, писался бы по-старому вечно. Расхождение выталкивается на том
  /// запуске, который его заметил, и запись — предпочтение, не факт: не
  /// ушла сейчас — уйдёт при следующем запуске.
  void _adoptLocaleFromDevice() {
    // Человек выбрал язык сам — телефон больше не побеждает: иначе каждый
    // запуск затирал бы выбор из настроек языком устройства (ручка появилась
    // 22 авг, см. LocaleOverride).
    if (LocaleOverride.value.value != null) return;
    final device = _deviceLocale();
    final current = _account;
    if (current == null) return;
    if (current.locale != device) {
      _account = current.copyWith(locale: device);
      // Не await: язык уже принят, сервер догонит.
      client.setLocale(device).catchError((Object _) {});
    }
  }

  /// Язык устройства, сведённый к семи, которые продукт умеет. pt любого
  /// региона становится pt-BR — это код сервера; незнакомый язык падает в en.
  static String _deviceLocale() {
    final tag = PlatformDispatcher.instance.locale;
    final code = tag.languageCode.toLowerCase();
    const shipped = ['en', 'es', 'de', 'it', 'fr', 'ru'];
    if (shipped.contains(code)) return code;
    if (code == 'pt') return 'pt-BR';
    return 'en';
  }

  /// Оптимистично: человек выбрал язык, и интерфейс обязан подчиниться сразу.
  ///
  /// Серверная запись — это предпочтение, которое уйдёт при следующем удачном
  /// вызове. **На Android этого не было**, и переключатель молча не показывал,
  /// что сработал: PATCH проходил, аккаунт менялся, а золотое кольцо оставалось
  /// на прежней кнопке. Здесь порядок такой же, как на iOS.
  Future<void> setLocale(String value) async {
    final current = _account;
    if (current != null) {
      _account = current.copyWith(locale: value);
      notifyListeners();
    }
    try {
      await client.setLocale(value);
    } on AlmaError {
      // Молча: язык уже переключён, а сервер узнает при следующем вызове.
    }
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
