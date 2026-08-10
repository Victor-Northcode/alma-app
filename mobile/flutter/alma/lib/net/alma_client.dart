import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

/// Что пошло не так, на языке, которым можно распорядиться.
///
/// Порт `mobile/ios/Alma/Networking/AlmaError.swift`. Три вида, и различие
/// нужно экрану: сеть — «попробуй ещё», отказ сервера — у него есть **своё
/// предложение на языке аккаунта**, и его надо показать как есть, а не
/// подменять своим; разбор — наша ошибка, и человеку про неё знать нечего.
sealed class AlmaError implements Exception {
  const AlmaError();
}

class NetworkDown extends AlmaError {
  const NetworkDown(this.detail);
  final String detail;
}

/// Сервер ответил и объяснил. `message` уже переведён — он приходит из
/// `alma/i18n/replies.py` на языке аккаунта, и показывать его надо дословно.
class ServerRefused extends AlmaError {
  const ServerRefused({required this.status, required this.message, this.code});
  final int status;
  final String message;
  final String? code;
}

class BadPayload extends AlmaError {
  const BadPayload(this.detail);
  final String detail;
}

/// Где живёт токен.
///
/// На iOS он лежит в связке ключей, и это правильно: связка переживает
/// переустановку. `shared_preferences` так не умеет, и разница записана здесь
/// честно, а не спрятана — вернуть поведение связки будет отдельной задачей с
/// нативным плагином. Пока токен живёт столько же, сколько установка, и
/// восстановление покупок опирается на вход в аккаунт, а не на связку.
class TokenStore {
  static const _key = 'alma.token';
  static const _anonKey = 'alma.anon';

  String? _cached;
  String? _anonCached;

  Future<String?> read() async {
    if (_cached != null) return _cached;
    final prefs = await SharedPreferences.getInstance();
    return _cached = prefs.getString(_key);
  }

  Future<void> write(String token) async {
    _cached = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, token);
  }

  Future<void> clear() async {
    _cached = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }

  /// Постоянный признак установки.
  ///
  /// Отправляется на каждом запросе и нужен ровно для одного: связать гостя,
  /// переустановившего приложение, с его же покупками. Это не идентификатор
  /// человека и он никуда, кроме нашего сервера, не уходит.
  Future<String> anonId() async {
    if (_anonCached != null) return _anonCached!;
    final prefs = await SharedPreferences.getInstance();
    var value = prefs.getString(_anonKey);
    if (value == null) {
      value = _randomId();
      await prefs.setString(_anonKey, value);
    }
    return _anonCached = value;
  }

  static String _randomId() {
    // Времени достаточно: значение обязано быть устойчивым на этой установке,
    // а не непредсказуемым — оно ничего не защищает.
    final now = DateTime.now().microsecondsSinceEpoch;
    return 'a$now${now.hashCode.abs()}';
  }
}

/// Единственный путь к серверу.
///
/// Порт `mobile/ios/Alma/Networking/AlmaClient.swift`.
class AlmaClient {
  AlmaClient({required this.baseUrl, TokenStore? tokens, http.Client? http})
      : _tokens = tokens ?? TokenStore(),
        _http = http ?? _defaultClient();

  final Uri baseUrl;
  final TokenStore _tokens;
  final http.Client _http;

  static http.Client _defaultClient() => http.Client();

  static const tokenHeader = 'X-Alma-Token';
  static const anonHeader = 'X-Alma-Anon';
  static const timezoneHeader = 'X-Alma-Timezone';

  /// **Сколько ждать, пока пишется глава.**
  ///
  /// Обычный таймаут меряет промежутки между байтами, а генерация молчит по
  /// сорок-шестьдесят секунд и ничего не шлёт. На iOS из-за этого глава падала
  /// с «Alma сейчас не отвечает» при живом сервере; 180 секунд — то же число,
  /// что стоит там и в Android после того случая.
  static const writingTimeout = Duration(seconds: 180);
  static const normalTimeout = Duration(seconds: 30);

  Future<bool> get hasAccount async => (await _tokens.read()) != null;

  /* ── кто это ─────────────────────────────────────────────────────────── */

  Future<AlmaSessionInfo> session() async =>
      AlmaSessionInfo.fromJson(await _get('/v1/auth/session'));

  Future<AlmaSessionInfo> refresh() async {
    final info = AlmaSessionInfo.fromJson(await _post('/v1/auth/refresh', const {}));
    await _tokens.write(info.token);
    return info;
  }

  Future<AlmaAccount> account() async =>
      AlmaAccount.fromJson(await _get('/v1/account'));

  Future<void> setLocale(String locale) async =>
      _patch('/v1/account', {'locale': locale});

  Future<void> setDisplayName(String name) async =>
      _patch('/v1/account', {'display_name': name});

  /* ── места ───────────────────────────────────────────────────────────── */

  Future<List<Place>> searchPlaces(String query) async {
    // /v1/places/search, как в AlmaClient.swift — третий выдуманный путь,
    // пойманный живым сервером (после хаба и формы профилей).
    final body =
        await _get('/v1/places/search?q=${Uri.encodeQueryComponent(query)}&limit=8');
    return _list(body, 'places')
        .map((e) => Place.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  /* ── профили ─────────────────────────────────────────────────────────── */

  /// **Сервер отдаёт голый список, не обёртку.** `GET /v1/profiles` отвечает
  /// `[{…}, …]`, и iOS декодирует его прямо в `[Profile]`. Первый порт читал
  /// `body['profiles']`, которого не существует, — и «Сегодня» молча решал,
  /// что рождения нет: имя на экране было, а гороскопа не было. Найдено в
  /// браузере на живом сервере; тест, который должен был это поймать, сам
  /// выдумал форму с обёрткой — теперь его транспорт отвечает как сервер.
  Future<List<Profile>> profiles() async {
    final body = await _get('/v1/profiles');
    return _list(body, 'profiles')
        .map((e) => Profile.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  /// Список из ответа, какой бы формой он ни пришёл: голым (`_send` кладёт его
  /// под 'value') или под собственным именем.
  static List<dynamic> _list(Map<String, dynamic> body, String key) =>
      (body['value'] as List?) ?? (body[key] as List?) ?? const [];

  Future<Profile> saveProfile(BirthInput birth, {bool isSelf = true, String? relation}) async {
    final body = await _post('/v1/profiles', {
      ...birth.toJson(),
      'is_self': isSelf,
      'relation': ?relation,
    });
    return Profile.fromJson(body);
  }

  /* ── расчёт ──────────────────────────────────────────────────────────── */

  Future<CalcResult> compute(
    SystemSlug system, {
    Map<String, dynamic> body = const {},
  }) async =>
      CalcResult.fromJson(await _post('/v1/systems/${system.path}', body));

  Future<Hub> hub() async => Hub.fromJson(await _get('/v1/systems/hub'));

  Future<ChapterList> chapters(SystemSlug system, {required String locale}) async =>
      ChapterList.fromJson(
        await _get('/v1/readings/${system.path}/chapters?locale=$locale'),
      );

  /// Глава. Несёт [writingTimeout]: если её ещё не писали, модель сейчас будет
  /// молча работать почти минуту.
  Future<ReadingResponse> reading({
    required SystemSlug system,
    required String chapter,
    required String locale,
  }) async =>
      ReadingResponse.fromJson(await _post(
        '/v1/readings',
        {'system': system.path, 'chapter': chapter, 'locale': locale},
        timeout: writingTimeout,
      ));

  /* ── беседа ──────────────────────────────────────────────────────────── */

  /// Вопрос Alma. Ответ — тоже генерация, короче главы, и несёт тот же
  /// таймаут письма.
  Future<ChatReply> ask(String message, {String? threadId, required String locale}) async =>
      ChatReply.fromJson(await _post(
        '/v1/chat',
        {
          'message': message,
          'thread_id': ?threadId,
          'locale': locale,
        },
        timeout: writingTimeout,
      ));

  /* ── внутреннее ──────────────────────────────────────────────────────── */

  Future<Map<String, dynamic>> _get(String path) =>
      _send('GET', path, null, normalTimeout);

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body, {
    Duration timeout = normalTimeout,
  }) =>
      _send('POST', path, body, timeout);

  Future<Map<String, dynamic>> _patch(String path, Map<String, dynamic> body) =>
      _send('PATCH', path, body, normalTimeout);

  Future<Map<String, dynamic>> _send(
    String method,
    String path,
    Map<String, dynamic>? body,
    Duration timeout,
  ) async {
    final uri = baseUrl.resolve(path);
    final request = http.Request(method, uri);
    request.headers.addAll({
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      anonHeader: await _tokens.anonId(),
      // Часовой пояс устройства. Сервер читает его в одном месте: в запросе,
      // который заводит гостя, — чтобы утреннее уведомление приходило утром, а
      // не в чужой полдень. Незнакомую зону он молча игнорирует.
      timezoneHeader: _deviceTimezone(),
    });
    final token = await _tokens.read();
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
      request.headers[tokenHeader] = token;
    }
    if (body != null) {
      request.body = jsonEncode(body);
    }

    http.StreamedResponse streamed;
    try {
      streamed = await _http.send(request).timeout(timeout);
    } on TimeoutException {
      throw NetworkDown('истекло время ожидания: $method $path');
    } catch (error) {
      throw NetworkDown(error.toString());
    }

    final text = await streamed.stream.bytesToString();
    if (streamed.statusCode >= 400) {
      // **Предложение сервера показывается как есть — когда оно для
      // читателя.** FastAPI кладёт тело отказа в `detail`, и наш сервер шлёт
      // там объект `{error, message}`. Первый разбор брал `detail` целиком и
      // печатал словарь фигурными скобками прямо на экране —
      // «{error: budget_exceeded, message: spent $0.1023…}» — найдено на
      // живом отказе в браузере.
      //
      // Сообщения 4xx приходят из `alma/i18n/replies.py` на языке аккаунта и
      // показываются дословно. Сообщения 5xx — внутренние английские строки
      // для оператора («spent $0.1023 against a $0.10 ceiling»), читателю
      // экран говорит свою переведённую фразу; так же поступает iOS, где
      // AlmaFailure рисует displayText, а не серверное нутро.
      String message = '';
      String? code;
      try {
        final parsed = jsonDecode(text);
        if (parsed is Map) {
          final detail = parsed['detail'];
          if (detail is Map) {
            message = (detail['message'] ?? '').toString();
            code = detail['error'] as String?;
          } else if (detail is String) {
            message = detail;
          } else {
            message = (parsed['message'] ?? '').toString();
            code = parsed['error'] as String? ?? parsed['code'] as String?;
          }
        }
      } catch (_) {}
      if (streamed.statusCode >= 500) message = '';
      throw ServerRefused(status: streamed.statusCode, message: message, code: code);
    }

    if (text.isEmpty) return const {};
    try {
      final parsed = jsonDecode(text);
      if (parsed is Map<String, dynamic>) return parsed;
      return {'value': parsed};
    } catch (error) {
      throw BadPayload(error.toString());
    }
  }

  static String _deviceTimezone() {
    if (kIsWeb) return 'UTC';
    try {
      return Platform.localeName.isEmpty ? 'UTC' : DateTime.now().timeZoneName;
    } catch (_) {
      return 'UTC';
    }
  }
}
