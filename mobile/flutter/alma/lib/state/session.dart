import 'package:flutter/widgets.dart';

import '../net/alma_client.dart';
import '../net/models.dart';

/// Что приложение знает о том, кто его открыл.
///
/// Порт `mobile/ios/Alma/State/AlmaSessionModel.swift`.
///
/// **Аккаунт настоящий с первого запроса.** Гость — это не «ещё не
/// зарегистрировался», а полноправная строка на сервере, у которой есть карта и
/// могут быть покупки. Вход добавляет к ней имя и делает её долговечной, а не
/// создаёт заново — поэтому здесь нет состояния «не вошёл, значит ничего нет».
class AlmaSession extends ChangeNotifier {
  AlmaSession(this.client);

  final AlmaClient client;

  AlmaAccount? _account;
  Profile? _profile;
  List<Profile> _people = const [];
  bool _ready = false;
  AlmaError? _failure;

  AlmaAccount? get account => _account;
  Profile? get profile => _profile;
  List<Profile> get people => _people;
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

  Future<void> start({bool force = false}) async {
    if (_ready && !force) return;
    _failure = null;
    try {
      // Сессия сама создаёт гостя, если его ещё нет: до этой строки у человека
      // не было аккаунта, после — есть, и он ничего для этого не делал.
      if (!await client.hasAccount) await client.refresh();
      _account = await client.account();
      final all = await client.profiles();
      _profile = all.where((p) => p.isSelf).firstOrNull;
      _people = all.where((p) => !p.isSelf).toList();
      _ready = true;
    } on AlmaError catch (error) {
      _failure = error;
      _ready = true;
    }
    notifyListeners();
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
