import 'dart:async';
import 'dart:convert';
import 'dart:io' show Link, Platform;

import 'package:flutter/foundation.dart' show kIsWeb, visibleForTesting;
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
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

/// 409 `ambiguous_birth_time` — **вопрос, а не поломка.**
///
/// Часы в ту ночь перевели назад, и названное время случилось дважды: оба раза
/// настоящие, оба дают разное небо. Сервер отказывается угадывать, и правильно
/// делает — монетка, брошенная здесь, ляжет в дома, в соляр и в карту, за
/// которые потом заплатят.
///
/// Отдельным типом, потому что экрану развилки нужно то, чего нет в общем
/// отказе: два варианта с именами, которые часы носили в ту ночь, и дата
/// перевода. Без типа это была бы строка сообщения, которую пришлось бы
/// разбирать обратно.
class AmbiguousBirthTime extends AlmaError {
  const AmbiguousBirthTime({
    required this.options,
    required this.timezone,
    required this.transitionLocalDate,
  });

  final List<BirthTimeOption> options;
  final String timezone;

  /// Дата перевода часов, `YYYY-MM-DD`. Пустая, если сервер её не назвал —
  /// экран тогда задаёт вопрос без неё, а не выдумывает.
  final String transitionLocalDate;

  BirthTimeOption? get earlier => _by('earlier');
  BirthTimeOption? get later => _by('later');

  BirthTimeOption? _by(String choice) {
    for (final option in options) {
      if (option.choice == choice) return option;
    }
    return null;
  }

  /// На сколько часов второй вариант отстоит от первого. Это и есть «часом
  /// позже» в подписи; переводы часов бывают и на полчаса, поэтому число, а не
  /// слово в коде.
  double? get gapHours {
    final a = earlier, b = later;
    if (a == null || b == null) return null;
    return a.offsetHours - b.offsetHours;
  }

  static AmbiguousBirthTime? from(Map<String, dynamic> detail) {
    final raw = detail['options'];
    if (raw is! List) return null;
    final options = <BirthTimeOption>[];
    for (final item in raw) {
      if (item is Map) options.add(BirthTimeOption.fromJson(item));
    }
    if (options.isEmpty) return null;
    return AmbiguousBirthTime(
      options: options,
      timezone: (detail['timezone'] ?? '').toString(),
      transitionLocalDate: (detail['transition_local_date'] ?? '').toString(),
    );
  }
}

/// Один из двух настоящих моментов, которыми обернулось названное время.
class BirthTimeOption {
  const BirthTimeOption({
    required this.choice,
    required this.utc,
    required this.abbreviation,
    required this.offsetHours,
  });

  /// `earlier` или `later` — уезжает обратно как `on_ambiguous`.
  final String choice;
  final DateTime? utc;

  /// Имя часов в ту ночь: CEST, CET, EDT. Единственное, чем два одинаковых
  /// времени на экране отличаются друг от друга.
  final String abbreviation;
  final double offsetHours;

  factory BirthTimeOption.fromJson(Map<dynamic, dynamic> json) =>
      BirthTimeOption(
        choice: (json['choice'] ?? '').toString(),
        utc: DateTime.tryParse((json['utc'] ?? '').toString()),
        abbreviation: (json['abbreviation'] ?? '').toString(),
        offsetHours: (json['offset_hours'] as num?)?.toDouble() ?? 0,
      );
}

/// Где живёт токен.
///
/// На iOS он лежит в связке ключей, и это правильно: связка переживает
/// переустановку. `shared_preferences` так не умеет, и разница записана здесь
/// честно, а не спрятана: на iOS связка переживает переустановку, на Android
/// ключ Keystore уничтожается вместе с приложением, а в вебе это шифрование в
/// том же браузере. Общее для всех трёх — «не переживает удаления
/// приложения», и именно так это сказано в юридическом тексте.
class TokenStore {
  static const _key = 'alma.token';
  static const _anonKey = 'alma.anon';
  //: Когда id отчеканен, epoch ms — рядом, а не внутри строки: id остаётся
  //: непрозрачным для сервера, а факт возраста читается отдельно (тот же
  //: расклад, что `alma.anon.minted` в вебе).
  static const _anonMintedKey = 'alma.anon.minted';

  /// **Связка ключей, а не настройки.**
  ///
  /// Токен — это и есть аккаунт: у безымянного гостя нет ни почты, ни имени, и
  /// сервер не имеет способа вернуть ему его покупки. Пока токен лежал в
  /// `shared_preferences`, он умирал вместе с установкой — вместе с картой и
  /// оплаченными главами.
  ///
  /// `first_unlock_this_device` выбран двумя отказами, как на нативе: не
  /// `unlocked` — фоновое обновление с телефоном в кармане обязано читать; и
  /// не переезжающий вариант — элемент, уехавший в зашифрованном бэкапе на
  /// новое устройство, дал бы один гостевой аккаунт из двух мест, а серверные
  /// лимиты под это не написаны.
  ///
  /// **Обещание платформенное.** На iOS связка переживает переустановку; на
  /// Android ключ Keystore уничтожается вместе с приложением, а в вебе это
  /// вообще не связка. Поэтому нигде — ни здесь, ни в юридическом тексте — не
  /// говорится «переживает переустановку»: сказано «не переживает удаления
  /// приложения», и это верно на всех трёх.
  static const _secure = FlutterSecureStorage(
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock_this_device),
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  /// Двойная необязательность нарочно: внешний `null` — «ещё не читали»,
  /// внутренний — «читали, токена нет». Без различия аккаунт без токена
  /// долбил бы хранилище на каждом запросе, а чтение связки заметно дороже
  /// чтения настроек.
  ({String? value})? _cached;
  String? _anonCached;

  Future<String?> read() async {
    final cached = _cached;
    if (cached != null) return cached.value;
    var value = await _secure.read(key: _key);
    value ??= await _migrateFromPreferences();
    _cached = (value: value);
    return value;
  }

  /// Переезд старого токена из настроек в связку.
  ///
  /// **Порядок здесь — цена аккаунта.** Записать, перечитать, сравнить и лишь
  /// потом удалить из настроек: удаление раньше проверки — это потерянный
  /// аккаунт со всеми покупками, и восстановить его нечем. И это переезд, а не
  /// слепая перезапись: если в связке уже что-то есть, значение из настроек
  /// выбрасывается — иначе откат на предыдущую сборку и обратно затёр бы
  /// свежий токен старым.
  Future<String?> _migrateFromPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    final old = prefs.getString(_key);
    if (old == null) return null;
    try {
      await _secure.write(key: _key, value: old);
      if (await _secure.read(key: _key) == old) {
        await prefs.remove(_key);
      }
    } catch (_) {
      // Связка не ответила — токен остаётся в настройках и переедет в
      // следующий раз. Хуже потерянного аккаунта нет ничего.
    }
    return old;
  }

  Future<void> write(String token) async {
    // **Пустая запись — это запись.** Каждый ответ сервера несёт заголовок с
    // токеном, и без этой проверки прокручиваемый экран переписывал бы связку
    // десятки раз в минуту.
    if (_cached?.value == token) return;
    _cached = (value: token);
    await _secure.write(key: _key, value: token);
  }

  Future<void> clear() async {
    _cached = (value: null);
    await _secure.delete(key: _key);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }

  /// Сколько дней живёт признак установки, прежде чем чеканится заново.
  ///
  /// То же число, что `PURGE_AFTER_DAYS` в `alma/funnel.py` и
  /// `FUNNEL_RETENTION_DAYS` на сайте: страница приватности обещает, что и
  /// строки воронки, и сам идентификатор умирают через этот срок. Нативные
  /// клиенты это держали (`InstallationId.swift`, `Measurement.kt`); порт
  /// уронил — id жил вечно, и обещание держала только половина продукта.
  /// Стережёт `legal-truth.test.ts` на сайте: он читает этот файл.
  static const anonRetentionDays = 180;

  /// Признак установки — не постоянный, а со сроком жизни.
  ///
  /// Отправляется на каждом запросе и нужен ровно для одного: склеить шаги
  /// воронки до аккаунта с аккаунтом, когда тот появится (`funnel.claim` на
  /// сервере). Покупки он не связывает — их держит токен в связке ключей;
  /// комментарий, обещавший здесь «покупки после переустановки», был неправдой
  /// уже потому, что `shared_preferences` переустановку не переживают. Это не
  /// идентификатор человека и он никуда, кроме нашего сервера, не уходит.
  Future<String> anonId() async {
    if (_anonCached != null) return _anonCached!;
    final prefs = await SharedPreferences.getInstance();
    var value = prefs.getString(_anonKey);
    // Возраст без штампа — любой, и такой id считается истёкшим: перечеканка
    // стоит одного склеенного визита, вечный id стоит обещания на странице
    // приватности. Ровно то же правило, что `anonExpired` в вебе.
    final minted = prefs.getInt(_anonMintedKey);
    final now = DateTime.now().millisecondsSinceEpoch;
    final expired = minted == null ||
        now - minted >= anonRetentionDays * 24 * 60 * 60 * 1000;
    if (value == null || expired) {
      value = _randomId();
      await prefs.setString(_anonKey, value);
      await prefs.setInt(_anonMintedKey, now);
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

  /// Выйти на этом устройстве: забыть токен. Аккаунт с картой и покупками
  /// остаётся на сервере — вернуться можно любой из трёх дверей; следующий
  /// `session.start` заводит свежего гостя (владелец, 25.08.2026: «сделай
  /// чтоб можно было выйти с аккаунта»).
  Future<void> signOut() => _tokens.clear();

  /* ── кто это ─────────────────────────────────────────────────────────── */

  Future<AlmaSessionInfo> session() async =>
      AlmaSessionInfo.fromJson(await _get('/v1/auth/session'));

  Future<AlmaSessionInfo> refresh() async {
    final info = AlmaSessionInfo.fromJson(await _post('/v1/auth/refresh', const {}));
    await _tokens.write(info.token);
    return info;
  }

  /* ── вход ────────────────────────────────────────────────────────────── */

  /// Попросить письмо со ссылкой входа.
  ///
  /// **Ответ одинаков всегда** — сервер не сообщает, знает он этот адрес или
  /// нет, и это не забывчивость, а решение: ручка, отвечающая по-разному, —
  /// это способ проверить чужую почту на наличие аккаунта.
  ///
  /// `debug_token` приходит только когда почтовик не настроен и сборка не
  /// продакшн: без него локальный вход было бы нечем закончить.
  Future<MagicLinkSent> requestMagicLink(
    String email, {
    required String locale,
  }) async =>
      MagicLinkSent.fromJson(
        await _post('/v1/auth/magic-link', {'email': email, 'locale': locale}),
      );

  /// Обменять токен из письма на сессию. Ссылка одноразовая.
  Future<AlmaSessionInfo> consumeMagicLink(String token) async =>
      _adopt(await _post('/v1/auth/magic-link/consume', {'token': token}));

  /// Войти кодом из того же письма. Deep-link у приложения нет — ссылка
  /// открывает веб, а телефон вводит шесть цифр (владелец, 24.08.2026).
  /// Код одноразовый и живёт столько же, сколько ссылка.
  Future<AlmaSessionInfo> consumeEmailCode(String email, String code) async =>
      _adopt(await _post(
          '/v1/auth/email-code/consume', {'email': email, 'code': code}));

  /// Какие двери этот сервер умеет открывать: `google`, `apple`, `email`.
  ///
  /// **Спрашиваем, а не угадываем.** Обе ручки провайдеров отвечают 401 без
  /// своего идентификатора клиента — токен нечем проверить, значит нельзя ему
  /// верить, — и кнопка, нарисованная поверх такой ручки, отвечала бы ошибкой
  /// на каждое нажатие. Человек, увидевший её, решит не «сервер настроен
  /// наполовину», а «мой аккаунт сломан».
  ///
  /// Раньше это был флаг сборки, который надо было переключить руками в тот же
  /// час, когда ключи вписали в окружение сервера, — в двух местах, ничего друг
  /// о друге не знающих. Теперь кнопка появляется сама.
  Future<Map<String, bool>> authProviders() async {
    final body = await _get('/v1/auth/providers');
    return {
      for (final key in const ['google', 'apple', 'email'])
        key: body[key] == true,
    };
  }

  Future<AlmaSessionInfo> signInWithGoogle(String credential) async =>
      _adopt(await _post('/v1/auth/google', {'credential': credential}));

  /// Имя Apple отдаёт **ровно один раз** — при первой авторизации и никогда
  /// больше. Поэтому оно уезжает, когда есть, и не уезжает пустым: пустая
  /// строка поверх уже сохранённого имени превращает человека в безымянного
  /// при втором входе.
  Future<AlmaSessionInfo> signInWithApple(
    String identityToken, {
    String? fullName,
  }) async =>
      _adopt(await _post('/v1/auth/apple', {
        'identity_token': identityToken,
        if (fullName != null && fullName.isNotEmpty) 'full_name': fullName,
      }));

  /// Принять новую сессию: токен в связку до того, как о нём узнает экран.
  ///
  /// Иначе следующий же запрос уйдёт под гостевым токеном — вход состоялся бы
  /// на сервере и не состоялся на телефоне.
  Future<AlmaSessionInfo> _adopt(Map<String, dynamic> body) async {
    final info = AlmaSessionInfo.fromJson(body);
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

  Future<List<Place>> searchPlaces(String query, {String locale = 'en'}) async {
    // /v1/places/search, как в AlmaClient.swift — третий выдуманный путь,
    // пойманный живым сервером (после хаба и формы профилей).
    // `lang` локализует страну в подписи: «Москва, Россия», а не «, Russia»
    // (владелец, 25.08.2026). Подпись сохраняется в профиль как есть.
    final body = await _get(
        '/v1/places/search?q=${Uri.encodeQueryComponent(query)}&limit=8'
        '&lang=${Uri.encodeQueryComponent(locale)}');
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

  /// Сохранить рождение.
  ///
  /// [gender] — «female» или «male», и это грамматика, а не анкетный вопрос:
  /// русское письмо согласует род («ты родилась»), а без ответа переходит на
  /// безличные обороты. Анкета спрашивает об этом вторым шагом и до этой
  /// правки никуда не отправляла — человек отвечал, а письмо всё равно
  /// обходило его пол стороной.
  ///
  /// **[locale] — язык *отказа*, а не язык профиля**, и обязателен он поэтому.
  /// Единственный ответ, который эта ручка отдаёт словами читателю, — 402
  /// `partner_limit` («одно сохранённое сравнение — бесплатно»), и сервер берёт
  /// его язык отсюда (`api/schemas.py`, `ProfileInput.locale`). Без поля он
  /// откатывается на `user.locale`, а у свежего гостя там ещё стоит язык
  /// чеканки: наш `PATCH /v1/account` уходит без ожидания и приземляется когда
  /// успеет. То есть первому гостю — тому, кто добавляет второго человека в
  /// первые же минуты, — отказ приходил по-английски. Проверено на живом 8018:
  /// то же тело с `"locale":"ru"` и `"de"` отвечает по-русски и по-немецки.
  ///
  /// Поле стоит здесь, а не в [BirthInput], потому что и на сервере оно живёт
  /// на `ProfileInput`, а не на `BirthInput`: рождение — это дата и место, а не
  /// язык того, кто его вводит.
  Future<Profile> saveProfile(
    BirthInput birth, {
    required String locale,
    bool isSelf = true,
    String? relation,
    String? gender,
    String? interest,
    // Текущий город (29.08.2026): пересохранение самого себя ЗАМЕЩАЕТ строку
    // профиля, и клиент, не прокинувший сохранённый город при правке имени,
    // молча стёр бы его — поэтому настройки всегда шлют либо новый, либо
    // прежний из профиля (см. `_saveBirth`).
    double? currentLatitude,
    double? currentLongitude,
    String? currentPlaceLabel,
  }) async {
    final body = await _post('/v1/profiles', {
      ...birth.toJson(),
      'is_self': isSelf,
      'locale': locale,
      'relation': ?relation,
      'gender': ?gender,
      // Ответ квиза V0 «что сейчас важнее всего» — сигнал NBO. Сервер пишет
      // его только владельцу аккаунта и отвергает слова вне закрытого списка.
      'interest': ?interest,
      'current_latitude': ?currentLatitude,
      'current_longitude': ?currentLongitude,
      'current_place_label': ?currentPlaceLabel,
    });
    return Profile.fromJson(body);
  }

  /// Убрать человека. Своё рождение удалить нельзя — это делает удаление
  /// аккаунта; сервер отвечает 404 на чужой профиль.
  Future<void> deleteProfile(String id) => _send('DELETE', '/v1/profiles/$id', null, normalTimeout);

  /// Отметить, что человек дошёл до одной ступени воронки.
  ///
  /// **Маяк, а не запрос.** Отказ проглатывается молча и никогда не мешает
  /// тому, что человек делал: измерение, роняющее покупку, хуже отсутствующего.
  ///
  /// **Стадию привязывает не токен, а идентификатор установки.** Половина
  /// воронки происходит до того, как аккаунт появился, — это не недостаток, а
  /// продукт, у которого первая минута не требует регистрации. Сшивает всё
  /// заголовок `X-Alma-Anon`, который запросчик кладёт на каждый вызов, и
  /// именно поэтому идентификатор порождается там, а не здесь: клиент, меняющий
  /// его между маяками, ломает не свою сессию, а отчёт — первая конверсия
  /// читается как ноль на данных, которые выглядят здоровыми.
  Future<void> track(FunnelStage stage, {Map<String, dynamic>? meta}) async {
    try {
      await _post('/v1/events', {
        'stage': stage.wire,
        if (meta != null && meta.isNotEmpty) 'meta': meta,
      });
    } on AlmaError {
      // Молча.
    }
  }

  /// Всё, что мы держим об этом аккаунте, одним документом.
  Future<Map<String, dynamic>> exportAccount() => _get('/v1/account/export');

  /// Стереть аккаунт и всё, что в нём.
  ///
  /// `confirm` обязан совпасть с тем, чем аккаунт подтверждает себя: почтой у
  /// вошедшего, собственным идентификатором у гостя. Маршрут уничтожает
  /// оплаченные чтения, которые нельзя переписать слово в слово, и случайное
  /// нажатие до него доходить не должно.
  Future<Map<String, dynamic>> deleteAccount(String confirm) =>
      _post('/v1/account/delete', {'confirm': confirm});

  /* ── расчёт ──────────────────────────────────────────────────────────── */

  Future<CalcResult> compute(
    SystemSlug system, {
    Map<String, dynamic> body = const {},
  }) async =>
      CalcResult.fromJson(await _post('/v1/systems/${system.path}', body));

  Future<Hub> hub() async => Hub.fromJson(await _get('/v1/systems/hub'));

  Future<ChapterList> chapters(SystemSlug system, {required String locale}) async {
    final list = ChapterList.fromJson(
      await _get('/v1/readings/${system.path}/chapters?locale=$locale'),
    );
    _knownChapters['${system.path}:$locale'] = list;
    return list;
  }

  /// Последнее оглавление этой системы, если его уже привозили.
  ///
  /// **Существует ради одного кадра.** В главу заходят с экрана системы,
  /// который только что показал это самое оглавление, — значит, ответ на
  /// вопрос «открыта ли эта глава» уже в памяти, и экран главы обязан
  /// ответить им *синхронно*, до первого кадра. Иначе закрытая глава сперва
  /// показывает ожидание, и кнопка «Разблокировать» появляется после ответа
  /// сервера — ровно то, что владелец снял: «кнопка на первом скрине должна
  /// быть сразу как ты заходишь на не открытую страницу».
  ///
  /// Память, а не диск: право меняется покупкой, и оглавление, пережившее
  /// запуск, показывало бы стену тому, кто уже заплатил.
  ChapterList? knownChapters(SystemSlug system, {required String locale}) =>
      _knownChapters['${system.path}:$locale'];

  final Map<String, ChapterList> _knownChapters = {};

  /// Глава. Несёт [writingTimeout]: если её ещё не писали, модель сейчас будет
  /// молча работать почти минуту.
  ///
  /// **[partnerProfileId] — кого с кем читать, и без него глава совместимости
  /// ломается ровно там, где человек сделал всё правильно.** Сервер умеет
  /// подставить второго сам, но только пока сохранённый человек **ровно один**
  /// (`readings.py`, `_partner`); при двух и более он отвечает 422
  /// `partner_required`, и экран рисует «добавьте человека» тому, у кого их уже
  /// двое. Имя поля снято с `ReadingRequest.partner_profile_id` и проверено на
  /// живом 8018: выдуманный идентификатор отвечает 404 «no such profile» — то
  /// есть поле читается, — а запрос без него на аккаунте без пары даёт 422 с
  /// переведённой фразой.
  ///
  /// Остальным системам поле не нужно, и слать его им незачем: сервер его там
  /// игнорирует, но запрос, несущий лишнее, врёт о том, что ему важно.
  Future<ReadingResponse> reading({
    required SystemSlug system,
    required String chapter,
    required String locale,
    String? partnerProfileId,
  }) async =>
      ReadingResponse.fromJson(await _post(
        '/v1/readings',
        {
          'system': system.path,
          'chapter': chapter,
          'locale': locale,
          'partner_profile_id': ?partnerProfileId,
        },
        timeout: writingTimeout,
      ));

  /* ── утро и план ─────────────────────────────────────────────────────── */

  Future<Map<String, dynamic>> dailySettings() async => _get('/v1/notifications');

  Future<Map<String, dynamic>> setDaily({String? daily, int? hour}) async =>
      _patch('/v1/notifications', {
        'daily': ?daily,
        'hour': ?hour,
      });

  /// Полка: что вообще продаётся и почём. Цена приходит с сервера — здесь
  /// её не считают и не переводят в валюту, иначе на витрине и в чеке
  /// оказались бы два разных числа.
  ///
  /// Отдаёт полку целиком, а не один список строк: у той же ручки лежит
  /// `manage_url` — адрес, по которому останавливают магазинную подписку, — и
  /// настройки читают его отсюда. Пока метод возвращал только `items`, это поле
  /// не читалось нигде, и кнопка «управлять подпиской» вела в App Store с
  /// любого телефона.
  Future<Catalogue> catalogue({required String locale}) async =>
      Catalogue.fromJson(await _get('/v1/billing/catalogue?locale=$locale'));

  Future<Map<String, dynamic>> entitlements() async =>
      _get('/v1/billing/entitlements');

  /// Оплаченные отчёты по парам, свежие сверху.
  ///
  /// Сервер отвечает голым списком, как `/v1/profiles`, — и по той же причине
  /// здесь `_list`, а не `body['pairs']`: `_send` кладёт голый массив под
  /// `value`, и выдуманная обёртка молча превращала бы список в пустоту.
  Future<List<PairReportRef>> pairs() async {
    final body = await _get('/v1/pairs');
    return _list(body, 'pairs')
        .map((e) => PairReportRef.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  /// Кредит проверок пары в текущем периоде подписки.
  ///
  /// Форма ответа — `{"pair": {...}}` (`billing.py:/credits`): сервер оставил
  /// себе место под другие кредиты, и клиент разворачивает ровно свой ключ.
  Future<PairCredit> pairCredits() async {
    final body = await _get('/v1/billing/credits');
    return PairCredit.fromJson(
        (body['pair'] as Map?)?.cast<String, dynamic>() ?? const {});
  }

  /// Остановить следующее списание — и не тронуть ничего оплаченного.
  ///
  /// **Отмена — это не возврат, и в этом весь маршрут.** Сервер снимает только
  /// обещание списать (`renews_at`) и оставляет как есть срок уже оплаченного
  /// периода (`expires_at`), возвращая его в `access_until`. Это и есть та
  /// дата, которую экран обязан уметь назвать вслух: «твой план открыт до 4
  /// марта». Тот, кто отменил год на втором месяце, оплатил ещё десять и
  /// оставляет их себе.
  ///
  /// **Тела нет, и это нарочно.** Идентификатор подписки в теле был бы IDOR
  /// против платёжной системы: аккаунт и есть идентификатор, чужого номера
  /// ручка не принимает.
  ///
  /// **Три ответа, и путать их нельзя.** 200 — остановлено; 409
  /// `cancel_at_store` — подписку продал магазин, ни Apple, ни Google не дают
  /// серверу её отменить, и на нашей стороне **ничего не записано**; 502 —
  /// платёжная система не ответила, и тоже ничего не записано. Разница видна
  /// экрану по `ServerRefused.status`, и стоит она дорого: «отменено»,
  /// сказанное подписке, которая продолжает списываться, человек прочитает в
  /// выписке, а не у нас.
  ///
  /// Купленную в магазине подписку сюда вести незачем — её отменяет Apple, и
  /// экран показывает ссылку в App Store, а не эту кнопку. 409 остаётся
  /// подстраховкой на случай права без `source` от бэкенда старше сборки.
  Future<Map<String, dynamic>> cancelSubscription() =>
      _post('/v1/billing/subscription/cancel', const {});

  /// Отдать серверу подписанную магазином покупку.
  ///
  /// **Чек в руке — это не право.** Он уходит сюда, сервер проверяет подпись
  /// магазина и отвечает тем, что открылось; открывает главу ответ сервера, а
  /// не решение клиента. Всё, что клиент может решить, клиента можно заставить
  /// решить — телефон с подменённым StoreKit самое дешёвое место в мире, где
  /// это делают.
  ///
  /// `product` — **слаг каталога**, а не идентификатор товара в магазине:
  /// сервер ищет его в своём прайсе. Берётся из подписанного магазином
  /// идентификатора, а не из нажатой кнопки, — тогда расхождение между «что
  /// нажали» и «что подписали» невозможно по построению.
  ///
  /// **Повтор — это успех.** Магазин переотдаёт незавершённые покупки при
  /// каждом запуске, а восстановление проигрывает всё, что когда-либо
  /// покупалось этим Apple ID; сервер отвечает `already_claimed`, ничего не
  /// пишет и возвращает правдивый `unlocked`.
  Future<Map<String, dynamic>> verifyPurchase({
    required String platform,
    required String product,
    required String transaction,
    String? intentId,
  }) =>
      _post('/v1/billing/iap/verify', {
        'platform': platform,
        'product': product,
        'transaction': transaction,
        // Какой intent клиент считает своим — **только для сверки** на той
        // стороне. Партнёра сервер берёт из токена, который подписал магазин;
        // это поле лишь позволяет ему записать в лог расхождение.
        'intent_id': ?intentId,
      });

  /* ── покупка пары: про кого будет платёж ─────────────────────────────── */

  /// Сказать серверу, **про кого** открывается покупка проверки пары, и
  /// получить токен для магазинного листа.
  ///
  /// Токен кладётся в `appAccountToken` (iOS) / `obfuscatedProfileId`
  /// (Android) и возвращается серверу **внутри подписанного магазином
  /// пейлоада** — единственная связь «этот платёж — про этого человека»,
  /// которой можно верить. `profile_id` в теле `/verify` не годится ни при
  /// каких обстоятельствах: его пишет приложение, а приложение пересобирается.
  Future<PairIntentTicket> openPairIntent(String profileId) async =>
      PairIntentTicket.fromJson(
          await _post('/v1/billing/pair/intent', {'profile_id': profileId}));

  /// Аварийная привязка оплаченной проверки пары к партнёру.
  ///
  /// Для покупки, пришедшей без токена: сервер записал деньги, ответил
  /// `unbound`, и этот вызов закрывает долг. Повтор с тем же партнёром
  /// идемпотентен (`already_bound`); с другим — 409, одна покупка открывает
  /// один отчёт.
  Future<Map<String, dynamic>> bindPairPurchase({
    required String transaction,
    required String profileId,
  }) =>
      _post('/v1/billing/pair/bind', {
        'transaction': transaction,
        'profile_id': profileId,
      });

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

  /// Тот же вопрос, но сервер рассказывает по дороге, что он делает.
  ///
  /// `POST /v1/chat/stream` — SSE: события `stage` со стадией настоящей
  /// работы, затем ровно один `done` с тем же JSON, что отдаёт `/v1/chat`,
  /// либо `error` с телом обычного отказа. Разбор строчный и свой: формат —
  /// «event: имя», «data: json», пустая строка, — и тянуть под три строки
  /// парсера зависимость не за что.
  ///
  /// Ошибки — те же типы, что у [ask], и по тем же правилам: HTTP-статус до
  /// начала потока (квота отвечает обычным 429), `error` внутри потока и
  /// оборванная сеть — всё выходит наружу [AlmaError], так что экран
  /// обрабатывает стрим и одиночный ответ одним `catch`.
  Stream<ChatEvent> askStream(
    String message, {
    String? threadId,
    required String locale,
  }) async* {
    final request = http.Request('POST', baseUrl.resolve('/v1/chat/stream'));
    request.headers.addAll({
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      ..._commonHeaders(await _tokens.anonId()),
    });
    final token = await _tokens.read();
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
      request.headers[tokenHeader] = token;
    }
    request.body = jsonEncode({
      'message': message,
      'thread_id': ?threadId,
      'locale': locale,
    });

    http.StreamedResponse streamed;
    try {
      // Тот же таймаут, что у [ask], и меряет он то же самое: ожидание
      // заголовков. Тело у обоих читается без часов — у `_send` их нет на
      // `bytesToString`, и стрим не заводит себе строже: `Stream.timeout`
      // на теле к тому же не отдаёт закрытие потока под фальшивыми часами
      // виджет-тестов, то есть его цена — подвисший `finally` у экрана.
      streamed = await _http.send(request).timeout(writingTimeout);
    } on TimeoutException {
      throw const NetworkDown('истекло время ожидания: POST /v1/chat/stream');
    } catch (error) {
      throw NetworkDown(error.toString());
    }

    // Те же обязанности, что у `_send`: свежий токен из заголовка — в связку,
    // 410 — чистка. Стрим не освобождает от договора о токенах.
    final minted = streamed.headers[tokenHeader.toLowerCase()];
    if (minted != null && minted.isNotEmpty) {
      await _tokens.write(minted);
    }
    if (streamed.statusCode == 410) {
      await _tokens.clear();
    }
    if (streamed.statusCode >= 400) {
      // Отказ до первого байта — обычный JSON, не поток: квота, стена,
      // развилка часов. Разбирается тем же кодом, что и у одиночного ответа.
      throw _refusal(streamed.statusCode, await streamed.stream.bytesToString());
    }

    // **Поток дочитывается до естественного конца, а не бросается на
    // `done`.** Сервер закрывает его сразу за последним событием, так что
    // дочитать — бесплатно; а ранний выход из `await for` — это отмена
    // подписки, и под фальшивыми часами виджет-тестов отмена цепочки
    // `ByteStream → utf8 → LineSplitter` не завершается никогда: `finally`
    // у экрана не наступал, и думание оставалось висеть поверх ответа.
    // Поэтому стадии выходят наружу по дороге, а `done` и ошибка — после
    // конца потока.
    var event = '';
    final data = StringBuffer();
    ChatReply? finished;
    AlmaError? refused;
    try {
      final lines = streamed.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter());
      await for (final line in lines) {
        // Ответ уже есть — остаток дочитывается молча.
        if (finished != null || refused != null) continue;
        if (line.isNotEmpty) {
          if (line.startsWith('event:')) {
            event = line.substring('event:'.length).trim();
          } else if (line.startsWith('data:')) {
            // Многострочный data склеивается как есть; «:keepalive» и прочие
            // служебные строки SSE молча пропускаются.
            data.write(line.substring('data:'.length).trimLeft());
          }
          continue;
        }
        // Пустая строка — конец события.
        final name = event;
        final payload = data.toString();
        event = '';
        data.clear();
        if (name.isEmpty || payload.isEmpty) continue;
        switch (name) {
          case 'stage':
            // Стадия — украшение дороги, а не груз: непонятная не роняет
            // вопрос, она просто не рисуется.
            try {
              final parsed = jsonDecode(payload);
              if (parsed is Map) {
                final stage = (parsed['stage'] ?? '').toString();
                final label = (parsed['name'] ?? '').toString();
                if (stage.isNotEmpty && label.isNotEmpty) {
                  yield ChatStage(stage: stage, name: label);
                }
              }
            } catch (_) {}
          case 'done':
            final parsed = jsonDecode(payload);
            if (parsed is Map) {
              finished = ChatReply.fromJson(parsed.cast<String, dynamic>());
            } else {
              refused = BadPayload('done не объект: $payload');
            }
          case 'error':
            // Сервер упал уже после старта потока и сказал об этом словами
            // обычного отказа: `{status, detail}` разбирается тем же кодом,
            // что и тело HTTP-ошибки.
            int status = 500;
            Object detail = const <String, dynamic>{};
            try {
              final parsed = jsonDecode(payload);
              if (parsed is Map) {
                status = (parsed['status'] as num?)?.toInt() ?? 500;
                detail = parsed['detail'] ?? detail;
              }
            } catch (_) {}
            refused = _refusal(status, jsonEncode({'detail': detail}));
          default:
            // Событие с сервера свежее сборки — не ошибка, просто не наше.
            break;
        }
      }
    } on AlmaError {
      rethrow;
    } catch (error) {
      // Оборванный сокет, битая кодировка — всё это сеть, и экран отвечает
      // на неё как на сеть: вопрос возвращается в поле, а не пропадает.
      throw NetworkDown(error.toString());
    }
    if (refused != null) throw refused;
    if (finished != null) {
      yield ChatDone(finished);
      return;
    }
    // Сервер закрыл поток, не сказав ни `done`, ни `error`, — это обрыв, а
    // не тихий успех: без ответа вопрос не считается отправленным.
    throw const NetworkDown('стрим оборвался до ответа: POST /v1/chat/stream');
  }

  /// Отказ сервера, собранный из статуса и тела, — общий для `_send` и
  /// [askStream], потому что язык отказов один на все ручки.
  ///
  /// **Предложение сервера показывается как есть — когда оно для читателя.**
  /// FastAPI кладёт тело отказа в `detail`, и наш сервер шлёт там объект
  /// `{error, message}`. Первый разбор брал `detail` целиком и печатал
  /// словарь фигурными скобками прямо на экране — «{error: budget_exceeded,
  /// message: spent $0.1023…}» — найдено на живом отказе в браузере.
  ///
  /// Сообщения 4xx приходят из `alma/i18n/replies.py` на языке аккаунта и
  /// показываются дословно. Сообщения 5xx — внутренние английские строки
  /// для оператора («spent $0.1023 against a $0.10 ceiling»), читателю
  /// экран говорит свою переведённую фразу; так же поступает iOS, где
  /// AlmaFailure рисует displayText, а не серверное нутро.
  static AlmaError _refusal(int statusCode, String text) {
    String message = '';
    String? code;
    AmbiguousBirthTime? fork;
    try {
      final parsed = jsonDecode(text);
      if (parsed is Map) {
        final detail = parsed['detail'];
        if (detail is Map) {
          message = (detail['message'] ?? '').toString();
          code = detail['error'] as String?;
          // Развилка перевода часов уходит своим типом: это единственный
          // отказ, на который у экрана есть ответ, а не только сожаление.
          //
          // Собирается здесь, а возвращается **ниже**: этот разбор обёрнут в
          // `catch (_) {}`, который проглотил бы бросок вместе с опечаткой в
          // JSON, и развилка молча превратилась бы в общий отказ.
          if (code == 'ambiguous_birth_time') {
            fork = AmbiguousBirthTime.from(detail.cast<String, dynamic>());
          }
        } else if (detail is String) {
          message = detail;
        } else {
          message = (parsed['message'] ?? '').toString();
          code = parsed['error'] as String? ?? parsed['code'] as String?;
        }
      }
    } catch (_) {}
    if (fork != null) return fork;
    // **Кроме тех кодов, у которых фраза заведомо переведена.**
    //
    // `alma/i18n/replies.py` — единственный источник этих сообщений, и они
    // приходят на языке аккаунта независимо от статуса. Отказ по потолку
    // отвечает 503, и правило выше стирало готовую человеческую фразу,
    // подменяя её общим «что-то не работает» — то есть теряло единственное
    // объяснение, которое у читателя было.
    const translated = {
      'budget_exceeded',
      'month_budget',
      'question_limit.day',
      'question_limit.month',
      'partner_limit',
      'answer_refused',
    };
    if (statusCode >= 500 && !translated.contains(code)) message = '';
    return ServerRefused(status: statusCode, message: message, code: code);
  }

  /// Беседы этого человека, свежая первой. Форма снята с сервера, а не
  /// придумана: `{"threads": [{id, title, updated_at}]}` —
  /// `readings.py:/chat/threads`.
  ///
  /// [locale] — язык приложения: с ним сервер отдаёт заголовки переведёнными
  /// (дешёвой моделью, с вечным кешем). Без него — как записаны.
  Future<List<ChatThreadRef>> threads({String? locale}) async {
    final query = locale == null ? '' : '?locale=${Uri.encodeComponent(locale)}';
    final body = await _get('/v1/chat/threads$query');
    final rows = (body['threads'] as List?) ?? const [];
    return rows
        .map((row) => ChatThreadRef.fromJson((row as Map).cast<String, dynamic>()))
        .toList();
  }

  /// Одна беседа целиком, реплика за репликой.
  ///
  /// [locale] — язык приложения: сервер переводит реплики, написанные на
  /// другом языке, и кеширует перевод навсегда. Правило владельца от
  /// 28.08.2026: после смены языка на экране не остаётся ни строки на старом,
  /// включая архив беседы.
  Future<List<ChatTurn>> thread(String id, {String? locale}) async {
    final query = locale == null ? '' : '?locale=${Uri.encodeComponent(locale)}';
    final body = await _get('/v1/chat/threads/$id$query');
    final rows = (body['messages'] as List?) ?? const [];
    return rows
        .map((row) => ChatTurn.fromJson((row as Map).cast<String, dynamic>()))
        .toList();
  }

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
      ..._commonHeaders(await _tokens.anonId()),
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

    // **Токен приходит заголовком, а не только телом.**
    //
    // Сервер чеканит гостя в зависимости запроса и кладёт свежий токен в
    // `X-Alma-Token` любого ответа (`api/deps.py`). Порт этот заголовок не
    // читал вовсе и жил на токене из тела `/v1/auth/refresh` — то есть на том
    // единственном, который успел получить. Пока хранилище умирало вместе с
    // установкой, это было незаметно; с долговечным хранилищем незамеченный
    // здесь токен становится долговечно неправильным.
    final minted = streamed.headers[tokenHeader.toLowerCase()];
    if (minted != null && minted.isNotEmpty) {
      await _tokens.write(minted);
    }

    // **410 значит «этого аккаунта больше нет» — и хранилище чистится.**
    //
    // Токен, переживший удаление аккаунта, запирает человека навсегда: каждый
    // запрос отвечает 410, приложение не заводит нового гостя, и выхода нет.
    // На нативе это `AlmaClient.classify`, и там же сказано, почему чистится
    // и идентификатор установки: аккаунта нет, привязывать не к чему.
    if (streamed.statusCode == 410) {
      await _tokens.clear();
    }

    if (streamed.statusCode >= 400) {
      throw _refusal(streamed.statusCode, text);
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

  /// Зона устройства **именем IANA**, или `null` — «не знаем».
  ///
  /// `DateTime.now().timeZoneName` отдаёт короткое имя — «MSK», «CET», «+03» —
  /// и сервер такую зону молча игнорирует, ровно как обещает комментарий у
  /// заголовка. Тихо: единственное, что от неё зависит, — час утреннего
  /// уведомления, и промах виден не в приложении, а тем, что письмо приходит
  /// не утром. `DateTime.now().timeZoneName` заменён на имя из окружения,
  /// которое Dart отдаёт в форме IANA.
  ///
  /// **`null`, а не «UTC», и это не мелочь.** Здесь стояло `return 'UTC'` на
  /// всех трёх ветках неудачи — на вебе, без `TZ` и без `/etc/localtime`, то
  /// есть **на всяком Android**, где такого файла нет вовсе. Сервер
  /// (`notify/rules.zone_for`) выбросил у себя ступень UTC ровно затем, чтобы
  /// не будить человека посреди ночи, и написал это прямо: «UTC — законная
  /// зона для того, кто в ней живёт, и незаконная догадка». Клиент эту защиту
  /// обходил: `is_known_timezone('UTC')` — правда, зона садилась на строку
  /// устройства и побеждала зону рождения, и подписчик в Окленде получал
  /// утренний пуш в 20:00. Незнание называется незнанием: поля нет —
  /// `tokens.register` оставляет прежнее известное значение, а ступень зоны
  /// падает на рождение, что хотя бы не выдумано.
  ///
  /// Публичная, потому что зовущих двое: заголовок [timezoneHeader] здесь и
  /// тело `PushDevice` в `notify/push_devices.dart`. Там лежала своя копия,
  /// и она — как всякая копия — разошлась с этой; правило «зону, которой не
  /// знаем, не называем» обязано жить в одном месте, иначе следующая правка
  /// починит одну половину.
  static String? deviceTimezone() {
    if (kIsWeb) return null;
    try {
      // iOS и Android отдают IANA через локальную зону как символическую
      // ссылку /etc/localtime → /var/db/timezone/zoneinfo/Europe/Moscow.
      final link = Link('/etc/localtime');
      return ianaTimezone(
        envTz: Platform.environment['TZ'],
        localtimeTarget: link.existsSync() ? link.targetSync() : null,
      );
    } catch (_) {
      return null;
    }
  }

  /// Разбор того, что отдала платформа, — без самой платформы.
  ///
  /// Отдельной функцией, потому что это единственная часть [deviceTimezone],
  /// которую можно проверить: `/etc/localtime` на машине, где идут тесты, есть
  /// или нет по причинам, к продукту отношения не имеющим.
  @visibleForTesting
  static String? ianaTimezone({String? envTz, String? localtimeTarget}) {
    // Косая черта — весь критерий «это имя IANA»: «MSK» и «+03» её не имеют, и
    // сервер их всё равно не знает. Она же не даёт вернуть голое «UTC».
    if (envTz != null && envTz.contains('/')) return envTz;
    if (localtimeTarget != null) {
      final parts = localtimeTarget.split('zoneinfo/');
      if (parts.length == 2 && parts[1].contains('/')) return parts[1];
    }
    return null;
  }

  /// Заголовки, одинаковые у всех запросов, включая **необязательный** пояс.
  ///
  /// Одним местом, а не двумя списками в `_send` и `askStream`: правило «зону,
  /// которой не знаем, не называем» обязано быть одно, иначе второй вызов
  /// однажды снова напишет 'UTC' руками.
  static Map<String, String> _commonHeaders(String anonId) => {
        anonHeader: anonId,
        // Часовой пояс устройства. Сервер читает его в одном месте: в запросе,
        // который заводит гостя, — чтобы утреннее уведомление приходило утром,
        // а не в чужой полдень. Незнакомую зону он молча игнорирует, а
        // **неизвестную нам мы не шлём вовсе**: см. [deviceTimezone].
        timezoneHeader: ?deviceTimezone(),
      };
}
