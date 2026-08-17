import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

import 'alma_client.dart';
import 'models.dart';

/// Вход через Apple и Google — вся чужая обвязка в одном файле.
///
/// **Экран не должен знать двух чужих пакетов.** `sign_in_screen.dart` — это
/// вёрстка: поле почты, две кнопки, юридическая строка. Он умеет спрашивать
/// «войди» и показывать отказ; чем именно система спрашивает у человека
/// разрешение и в каком виде отдаёт токен — не его дело и никогда им не было.
class AlmaProviders {
  const AlmaProviders._();

  /// Показывать ли кнопку Apple на этой платформе **вообще**.
  ///
  /// Только там, где вход от Apple родной. На Android его нет как системной
  /// возможности: остаётся веб-поток через браузер с обратным адресом, то есть
  /// вторая обвязка, вторая заявка в консоли и худший из двух путей у человека,
  /// у которого Google уже в телефоне. Владелец сказал это первым: «ну у
  /// андроида не должно быть входа по apple логично».
  static bool get appleShows => !kIsWeb && Platform.isIOS;

  /// Спросить систему и войти. `null` — человек передумал.
  ///
  /// Отказ пользователя отличается от поломки и наверх не летит: закрыть
  /// системное окно — это не ошибка, и красная строка под кнопкой в ответ на
  /// «передумал» читается обвинением.
  static Future<AlmaSessionInfo?> apple(AlmaClient client) async {
    final AuthorizationCredentialAppleID credential;
    try {
      credential = await SignInWithApple.getAppleIDCredential(
        scopes: const [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
      );
    } on SignInWithAppleAuthorizationException catch (error) {
      if (error.code == AuthorizationErrorCode.canceled) return null;
      rethrow;
    }
    final token = credential.identityToken;
    if (token == null || token.isEmpty) {
      throw StateError('Apple вернула авторизацию без identity token');
    }
    // **Имя Apple отдаёт ровно один раз** — при самой первой авторизации и
    // никогда больше. Собираем его здесь, пока оно есть; сервер не перезапишет
    // им уже сохранённое, если во второй раз придёт пустота.
    final name = [credential.givenName, credential.familyName]
        .whereType<String>()
        .map((part) => part.trim())
        .where((part) => part.isNotEmpty)
        .join(' ');
    return client.signInWithApple(token, fullName: name.isEmpty ? null : name);
  }

  /// То же для Google. `null` — человек закрыл окно выбора аккаунта.
  static Future<AlmaSessionInfo?> google(AlmaClient client) async {
    final google = GoogleSignIn.instance;
    // Пакет 7.x требует инициализации до первого входа и берёт идентификатор
    // клиента из нативной конфигурации (`GoogleService-Info.plist`,
    // `google-services.json`). Здесь его не хардкодим: сервер проверяет токен
    // против своего `GOOGLE_CLIENT_ID`, и два места с одним значением, которые
    // никто не сверяет, однажды разойдутся.
    await google.initialize();
    final GoogleSignInAccount account;
    try {
      account = await google.authenticate();
    } on GoogleSignInException catch (error) {
      if (error.code == GoogleSignInExceptionCode.canceled) return null;
      rethrow;
    }
    final idToken = account.authentication.idToken;
    if (idToken == null || idToken.isEmpty) {
      throw StateError('Google вернул аккаунт без id token');
    }
    return client.signInWithGoogle(idToken);
  }
}
