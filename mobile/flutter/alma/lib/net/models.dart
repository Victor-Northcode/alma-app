/// Всё, что приходит и уходит по сети, как типы.
///
/// Порт `mobile/ios/Alma/Networking/APIModels.swift`. Имена полей и их
/// необязательность перенесены буква в букву: отсутствующее время рождения —
/// это `null`, а не пустая строка, не «unknown» и не полдень, и так же на всех
/// трёх сторонах.
///
/// **Чего здесь нет по сравнению с iOS — типа `JSONValue`.** Он существовал
/// затем, чтобы Swift мог держать произвольный JSON, не описывая его: восемь
/// систем возвращают восемь разных форм, общего честного типа у них нет. В Dart
/// произвольный JSON — это `Map<String, dynamic>`, и отдельный тип для него не
/// нужен. Один файл на 118 строк, которого просто не будет.
library;

/// Восемь систем.
enum SystemSlug {
  natal('natal'),
  numerology('numerology'),
  birthCard('birth-card'),
  transits('transits'),
  solarReturn('solar-return'),
  compatibility('compatibility'),
  astrocartography('astrocartography'),
  synthesis('synthesis');

  const SystemSlug(this.slug);
  final String slug;

  static SystemSlug? from(String? raw) {
    for (final value in SystemSlug.values) {
      if (value.slug == raw) return value;
    }
    return null;
  }

  /// Сколько у системы глав. Из `alma/ai/chapters.py`; всего сорок одна —
  /// именно это и значит «архив».
  int get chapterCount => switch (this) {
        SystemSlug.natal => 16,
        SystemSlug.numerology => 5,
        SystemSlug.birthCard ||
        SystemSlug.transits ||
        SystemSlug.solarReturn ||
        SystemSlug.astrocartography =>
          3,
        SystemSlug.compatibility || SystemSlug.synthesis => 4,
      };

  /// Меняется ли система со временем, и вправе ли подписка честно её продавать.
  /// Зеркало `LIVING_SYSTEMS` в `alma/billing/catalogue.py`: натальная карта,
  /// проданная помесячно, была бы арендой числа, не двигавшегося с рождения.
  bool get isLiving => switch (this) {
        SystemSlug.transits ||
        SystemSlug.solarReturn ||
        SystemSlug.compatibility =>
          true,
        _ => false,
      };

  /// Отрезок пути в `/v1/systems/…`.
  String get path => slug;
}

/* ── кто это ───────────────────────────────────────────────────────────── */

/// Что возвращает `/v1/auth/*`. Аккаунт настоящий с первого запроса; это то,
/// что он о себе говорит.
/// Ответ на просьбу прислать ссылку входа.
///
/// `sent` здесь всегда `true` и **не означает «адрес нам знаком»**: сервер
/// отвечает одинаково любому адресу, потому что разный ответ — это способ
/// проверить чужую почту на наличие аккаунта.
class MagicLinkSent {
  const MagicLinkSent({required this.expiresInMinutes, this.debugToken});

  final int expiresInMinutes;

  /// Токен из письма, отданный напрямую. Приходит **только** когда почтовик не
  /// настроен и сборка не продакшн: иначе локальный вход нечем закончить.
  /// В продакшне поля нет вовсе — не «пустое», а отсутствующее.
  final String? debugToken;

  factory MagicLinkSent.fromJson(Map<String, dynamic> json) => MagicLinkSent(
        expiresInMinutes: (json['expires_in_minutes'] as num?)?.toInt() ?? 0,
        debugToken: json['debug_token'] as String?,
      );
}

class AlmaSessionInfo {
  const AlmaSessionInfo({
    required this.token,
    required this.userId,
    required this.isGuest,
    required this.locale,
    this.email,
    this.displayName,
  });

  final String token;
  final String userId;
  final bool isGuest;
  final String locale;
  final String? email;
  final String? displayName;

  factory AlmaSessionInfo.fromJson(Map<String, dynamic> json) => AlmaSessionInfo(
        token: json['token'] as String,
        userId: json['user_id'] as String,
        isGuest: json['is_guest'] as bool? ?? true,
        locale: json['locale'] as String? ?? 'en',
        email: json['email'] as String?,
        displayName: json['display_name'] as String?,
      );
}

/// Более полная картина из `GET /v1/account`.
class AlmaAccount {
  const AlmaAccount({
    required this.id,
    required this.locale,
    required this.isGuest,
    required this.createdAt,
    required this.unlocked,
    this.email,
    this.displayName,
    this.provider,
  });

  final String id;
  final String locale;
  final bool isGuest;
  final String createdAt;

  /// Какие системы этот аккаунт вправе читать целиком.
  final List<String> unlocked;

  final String? email;
  final String? displayName;

  /// `"guest"`, `"apple"`, `"google"`, `"email"`.
  final String? provider;

  factory AlmaAccount.fromJson(Map<String, dynamic> json) => AlmaAccount(
        id: json['id'] as String,
        locale: json['locale'] as String? ?? 'en',
        isGuest: json['is_guest'] as bool? ?? true,
        createdAt: json['created_at'] as String? ?? '',
        unlocked:
            (json['unlocked'] as List?)?.map((e) => e as String).toList() ?? const [],
        email: json['email'] as String?,
        displayName: json['display_name'] as String?,
        provider: json['provider'] as String?,
      );

  AlmaAccount copyWith({String? locale}) => AlmaAccount(
        id: id,
        locale: locale ?? this.locale,
        isGuest: isGuest,
        createdAt: createdAt,
        unlocked: unlocked,
        email: email,
        displayName: displayName,
        provider: provider,
      );
}

/* ── данные рождения ───────────────────────────────────────────────────── */

/// Одно рождение, как его отправляет приложение.
///
/// Отсутствующее `birthTime` — полноправное состояние и единственное
/// представление «не знаю»: не пустая строка, не «unknown», не полдень. Тот же
/// договор проверяет и сервер с другой стороны.
class BirthInput {
  const BirthInput({
    required this.birthDate,
    required this.latitude,
    required this.longitude,
    required this.timezone,
    this.birthTime,
    this.placeLabel,
    this.placeId,
    this.name,
    this.onAmbiguous,
  });

  /// «ГГГГ-ММ-ДД», гражданская дата.
  final String birthDate;

  /// «ЧЧ:ММ» в 24-часовом виде, или `null`.
  final String? birthTime;

  final double latitude;
  final double longitude;

  /// Зона IANA, которую сервер знает. Неизвестная отвергается, а не заменяется
  /// на что-то: карта, молча посчитанная в UTC, выглядит точно как правильная.
  final String timezone;

  final String? placeLabel;
  final int? placeId;
  final String? name;

  /// `"raise"` просит сервер сообщить о двусмысленности перевода часов, а не
  /// выбирать за человека; два других значения на неё отвечают.
  final String? onAmbiguous;

  Map<String, dynamic> toJson() => {
        'birth_date': birthDate,
        if (birthTime != null) 'birth_time': birthTime,
        'latitude': latitude,
        'longitude': longitude,
        'timezone': timezone,
        if (placeLabel != null) 'place_label': placeLabel,
        if (placeId != null) 'place_id': placeId,
        if (name != null) 'name': name,
        if (onAmbiguous != null) 'on_ambiguous': onAmbiguous,
      };
}

/// Сохранённое рождение — владельца аккаунта или того, с кем он сравнивает.
class Profile {
  const Profile({
    required this.id,
    required this.isSelf,
    required this.birthDate,
    required this.latitude,
    required this.longitude,
    required this.timezone,
    this.name,
    this.relation,
    this.birthTime,
    this.placeLabel,
  });

  final String id;

  /// Владелец аккаунта. Ровно у одного профиля это истина.
  final bool isSelf;

  final String birthDate;
  final double latitude;
  final double longitude;
  final String timezone;

  final String? name;

  /// «партнёр», «мама», … — свободный текст, и `null`, когда не сказано.
  final String? relation;

  final String? birthTime;
  final String? placeLabel;

  bool get birthTimeKnown => birthTime != null;

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
        id: json['id'] as String,
        isSelf: json['is_self'] as bool? ?? false,
        birthDate: json['birth_date'] as String,
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        timezone: json['timezone'] as String,
        name: json['name'] as String?,
        relation: json['relation'] as String?,
        birthTime: json['birth_time'] as String?,
        placeLabel: json['place_label'] as String?,
      );
}

/// Место из справочника.
class Place {
  const Place({
    required this.id,
    required this.name,
    required this.country,
    required this.countryCode,
    required this.label,
    required this.latitude,
    required this.longitude,
    required this.timezone,
    this.region,
  });

  final int id;
  final String name;
  final String country;
  final String countryCode;

  /// Как строка показывается — «Milan, Lombardy, Italy».
  final String label;

  final double latitude;
  final double longitude;
  final String timezone;
  final String? region;

  factory Place.fromJson(Map<String, dynamic> json) => Place(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String,
        country: json['country'] as String? ?? '',
        countryCode: json['country_code'] as String? ?? '',
        label: json['label'] as String? ?? json['name'] as String,
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        timezone: json['timezone'] as String,
        region: json['region'] as String?,
      );
}

/* ── расчёт ────────────────────────────────────────────────────────────── */

/// Вправе ли этот аккаунт читать вещь — и почему нет.
class Access {
  const Access({required this.allowed, required this.reason, this.kind, this.expiresAt});

  final bool allowed;

  /// Собственное предложение сервера. Показывается как есть; оно приходит на
  /// языке аккаунта.
  final String reason;

  /// `"free"`, `"door"`, `"archive"`, `"subscription"` — или `null`, когда
  /// ничто его не даёт.
  final String? kind;

  final String? expiresAt;

  factory Access.fromJson(Map<String, dynamic> json) => Access(
        allowed: json['allowed'] as bool? ?? false,
        reason: json['reason'] as String? ?? '',
        kind: json['kind'] as String?,
        expiresAt: json['expires_at'] as String?,
      );
}

/// Ответ одной системы.
///
/// `data` — просто карта, потому что восемь систем возвращают восемь разных
/// форм и общего честного типа у них нет. Экран, рисующий одну систему, читает
/// ту ветку, которую знает.
///
/// **Закрытый результат — тоже настоящий результат.** Сервер урезает `data` до
/// предпросмотра и опустошает `factors`, выставляя `locked`. Расчёт бесплатен
/// всегда; продаётся написанное истолкование, поэтому закрытый ответ — не
/// ошибка и обращаться с ним как с ошибкой нельзя.
class CalcResult {
  const CalcResult({
    required this.system,
    required this.engineVersion,
    required this.computedAt,
    required this.subject,
    required this.data,
    required this.factors,
    required this.unavailable,
    required this.notes,
    required this.provenance,
    required this.access,
    this.locked,
  });

  final String system;
  final String engineVersion;
  final String computedAt;

  /// Рождение, из которого это посчитано, возвращённое обратно.
  final Map<String, dynamic> subject;

  /// Собственная выдача системы — урезанная до предпросмотра, когда закрыто.
  final Map<String, dynamic> data;

  /// Позиции, на которые можно ссылаться. Пусто, когда закрыто.
  final List<String> factors;

  /// Что посчитать не удалось и о чём честно сообщено, а не выдумано, —
  /// главным образом дома без времени рождения.
  final List<String> unavailable;

  final List<String> notes;
  final Map<String, dynamic> provenance;
  final Access access;
  final bool? locked;

  bool get isLocked => locked ?? false;
  SystemSlug? get slug => SystemSlug.from(system);

  factory CalcResult.fromJson(Map<String, dynamic> json) => CalcResult(
        system: json['system'] as String,
        engineVersion: json['engine_version'] as String? ?? '',
        computedAt: json['computed_at'] as String? ?? '',
        subject: (json['subject'] as Map?)?.cast<String, dynamic>() ?? const {},
        data: (json['data'] as Map?)?.cast<String, dynamic>() ?? const {},
        factors: (json['factors'] as List?)?.map((e) => e as String).toList() ?? const [],
        unavailable:
            (json['unavailable'] as List?)?.map((e) => e as String).toList() ?? const [],
        notes: (json['notes'] as List?)?.map((e) => e as String).toList() ?? const [],
        provenance: (json['provenance'] as Map?)?.cast<String, dynamic>() ?? const {},
        access: Access.fromJson(
          (json['access'] as Map?)?.cast<String, dynamic>() ?? const {},
        ),
        locked: json['locked'] as bool?,
      );
}

/* ── кабинет ───────────────────────────────────────────────────────────── */

/// Одна строка хаба.
class HubEntry {
  const HubEntry({required this.slug, required this.unlocked, required this.status});

  /// Типизировано, в отличие от `status` ниже, и несимметрия намеренная.
  /// Девятая система — это изменение продукта: ей нужна вкладка, значок, список
  /// глав и товар в магазине, — поэтому приложение, которое не может её
  /// разобрать, говорит о себе правду.
  final SystemSlug slug;

  final bool unlocked;

  /// `"calculated"`, `"open"`, `"needs-time"`, `"add-person"`, `"not-yet"`.
  /// Строка, а не перечисление, намеренно: это то единственное поле, где
  /// добавление состояния на сервере должно выродиться в показ незнакомого
  /// слова, а не в отказ разбора, гасящий весь хаб.
  final String status;

  static HubEntry? fromJson(Map<String, dynamic> json) {
    final slug = SystemSlug.from(json['slug'] as String?);
    if (slug == null) return null;
    return HubEntry(
      slug: slug,
      unlocked: json['unlocked'] as bool? ?? false,
      status: json['status'] as String? ?? '',
    );
  }
}

/// Всё, что нужно первой странице кабинета, одним запросом.
class Hub {
  const Hub({
    required this.hasBirthData,
    required this.birthTimeKnown,
    required this.people,
    required this.systems,
  });

  final bool hasBirthData;
  final bool birthTimeKnown;

  /// Сколько сохранено **других** людей. Совместимости нужен хотя бы один.
  final int people;

  final List<HubEntry> systems;

  factory Hub.fromJson(Map<String, dynamic> json) => Hub(
        hasBirthData: json['has_birth_data'] as bool? ?? false,
        birthTimeKnown: json['birth_time_known'] as bool? ?? false,
        people: (json['people'] as num?)?.toInt() ?? 0,
        systems: (json['systems'] as List? ?? const [])
            .map((e) => HubEntry.fromJson((e as Map).cast<String, dynamic>()))
            .whereType<HubEntry>()
            .toList(),
      );
}

/// Одна глава в оглавлении.
class ChapterEntry {
  const ChapterEntry({
    required this.slug,
    required this.numeral,
    required this.index,
    required this.title,
    required this.question,
    required this.free,
    required this.open,
    required this.written,
    required this.needsBirthTime,
  });

  final String slug;

  /// «I», «II», «XVI» — набирается засечным, как типографика.
  final String numeral;

  final int index;

  /// Бесплатную натальную главу приложение переименовывает на своей стороне,
  /// называя знак Солнца человека — «Солнце — Телец», — чего сервер сделать не
  /// может, не зная, чей список он печатает.
  final String title;

  /// Вопрос, на который отвечает глава, на языке человека.
  final String question;

  /// Единственная бесплатная глава системы.
  final bool free;

  /// Вправе ли этот аккаунт открыть её сейчас.
  final bool open;

  /// Написана ли уже. Написанная открывается мгновенно и говорит то же, что
  /// говорила в прошлый раз.
  final bool written;

  final bool needsBirthTime;

  ChapterEntry withTitle(String replacement) => ChapterEntry(
        slug: slug,
        numeral: numeral,
        index: index,
        title: replacement,
        question: question,
        free: free,
        open: open,
        written: written,
        needsBirthTime: needsBirthTime,
      );

  factory ChapterEntry.fromJson(Map<String, dynamic> json) => ChapterEntry(
        slug: json['slug'] as String,
        numeral: json['numeral'] as String? ?? '',
        index: (json['index'] as num?)?.toInt() ?? 0,
        title: json['title'] as String? ?? '',
        question: json['question'] as String? ?? '',
        free: json['free'] as bool? ?? false,
        open: json['open'] as bool? ?? false,
        written: json['written'] as bool? ?? false,
        needsBirthTime: json['needs_birth_time'] as bool? ?? false,
      );
}

class ChapterList {
  const ChapterList({required this.system, required this.chapters, required this.total});

  final String system;
  final List<ChapterEntry> chapters;
  final int total;

  factory ChapterList.fromJson(Map<String, dynamic> json) => ChapterList(
        system: json['system'] as String? ?? '',
        chapters: (json['chapters'] as List? ?? const [])
            .map((e) => ChapterEntry.fromJson((e as Map).cast<String, dynamic>()))
            .toList(),
        total: (json['total'] as num?)?.toInt() ?? 0,
      );
}

/// Одна написанная глава. Это и есть продукт.
class Reading {
  const Reading({
    required this.system,
    required this.chapter,
    required this.title,
    required this.teaser,
    required this.body,
    required this.citedFactors,
    required this.readFrom,
    required this.model,
    this.areas = const {},
    this.advice,
  });

  final String system;
  final String chapter;
  final String title;

  /// Первая строка, бесплатная даже когда глава — нет.
  final String teaser;

  final List<String> body;

  /// Четыре области дня, написанные словами: `work`/`love`/`money`/`body` →
  /// одна короткая фраза.
  ///
  /// **Пустая карта — нормальное состояние, а не сбой.** Поле просит одна
  /// глава из сорока одной (`transits/active`), и главы, написанные до его
  /// появления, лежат в кэше сервера без него. Экран в обоих случаях
  /// возвращается к прежней строке-факту, а не показывает пустоту.
  final Map<String, String> areas;

  /// Позиции, из которых прочитан текст. Каждое предложение ссылается на одну —
  /// именно это отличает Alma от ленты гороскопов, и экран обязан их
  /// показывать, а не прятать.
  final List<String> citedFactors;

  /// То же самое, уже собранное в строку.
  ///
  /// **Не показывается.** Сервер строит эту фразу по-английски и без локали:
  /// `"Read from: " + …` в `writer.py`. На Android она печаталась под русской
  /// главой, и это чинилось 9 августа. Поле оставлено только потому, что сервер
  /// его шлёт; подпись над ярлыками своя и переведённая.
  final String readFrom;

  final String model;

  /// Необязательно: не каждая глава им заканчивается, а заголовок с пустотой
  /// под ним хуже, чем отсутствие заголовка.
  final String? advice;

  factory Reading.fromJson(Map<String, dynamic> json) => Reading(
        system: json['system'] as String? ?? '',
        chapter: json['chapter'] as String? ?? '',
        title: json['title'] as String? ?? '',
        teaser: json['teaser'] as String? ?? '',
        body: (json['body'] as List? ?? const []).map((e) => e as String).toList(),
        citedFactors:
            (json['cited_factors'] as List? ?? const []).map((e) => e as String).toList(),
        readFrom: json['read_from'] as String? ?? '',
        model: json['model'] as String? ?? '',
        areas: {
          for (final item in (json['areas'] as List? ?? const []))
            if (item is Map &&
                (item['area'] as String? ?? '').isNotEmpty &&
                (item['line'] as String? ?? '').trim().isNotEmpty)
              item['area'] as String: (item['line'] as String).trim(),
        },
        advice: ((json['advice'] as String?) ?? '').trim().isEmpty
            ? null
            : json['advice'] as String,
      );
}

/// Ответ на запрос главы. Приходит только тогда, когда глава положена: без
/// права сервер отвечает 402 `locked` и ничего не пишет.
///
/// Здесь было поле `preview` — «глава настоящая, но неоплаченная», по которому
/// экран размывал все абзацы кроме первого. Владелец отменил само правило
/// (платить за генерацию до покупки), сервер этот ключ больше не шлёт, и поле
/// снято, чтобы никто не восстановил размытие по мёртвому флагу.
class ReadingResponse {
  const ReadingResponse({
    required this.reading,
    required this.cached,
    this.createdAt,
  });

  final Reading reading;

  /// Пришло ли из хранилища. Глава пишется один раз и возвращается всегда;
  /// `false` значит, что человек только что оплатил само написание.
  final bool cached;

  final String? createdAt;

  factory ReadingResponse.fromJson(Map<String, dynamic> json) => ReadingResponse(
        reading: Reading.fromJson((json['reading'] as Map).cast<String, dynamic>()),
        cached: json['cached'] as bool? ?? false,
        createdAt: json['created_at'] as String?,
      );
}

/* ── беседа ────────────────────────────────────────────────────────────── */

/// Что Alma сейчас сделала — в отличие от того, что она нашла.
///
/// Порт `ChatTurnKind` с обоих нативов (`ChatPieces.swift:27`,
/// `ChatTurnKind.kt:28`); значения — те же четыре строки провода, что называет
/// сервер (`alma/ai/conversation.py`, `WIRE_KINDS`).
///
/// **Баг, ради невозможности которого этот тип существует.** Раньше реплика
/// несла один булев `answered_from_chart`, и клиенты штамповали «НЕ ИЗ ТВОЕЙ
/// КАРТЫ» всякий раз, когда он был `false`. Поле оказалось про две разные вещи
/// — «я посмотрела карту, и она об этом молчит» и «эта реплика вообще ничего о
/// тебе не утверждает», — так что приветствие, которое второе, помечалось как
/// первое: человеку, написавшему «привет», сообщали, что его «привет» не найден
/// в его карте.
///
/// **Незнакомое значение — не ошибка.** Новая ветка таксономии с сервера свежее
/// сборки обязана выродиться в «просто реплику», а не в сбой разбора посреди
/// чужого разговора. Поэтому по проводу едет строка, а [of] ничего не бросает.
enum ChatTurnKind {
  /// Утверждение об этом человеке, прочитанное из его позиций. Единственный
  /// вид, обязанный показать цитаты, — в них и вся разница между Alma и
  /// чат-ботом в шляпе астролога.
  reading('reading'),

  /// Карту она прочла, и карте про это сказать нечего. Словами она это уже
  /// сказала; экран добавляет тихую строку, чтобы общий ответ не приняли за
  /// чтение.
  chartSilent('chart_silent'),

  /// Реплика, которая ни о ком ничего не утверждает: приветствие, спасибо,
  /// вопрос о том, что она умеет, письмо на языке, на котором мы ещё не пишем.
  /// **Никогда не подписывается** — здесь нечего уточнять.
  conversation('conversation'),

  /// Беда, вопрос о здоровье — группа D таксономии. Рисуется прозой, и ничем
  /// не украшается: тому, кто только что написал, что ему плохо, не выдают
  /// строку служебных пометок.
  care('care');

  const ChatTurnKind(this.wire);

  /// Имя на проводе. Сервер шлёт именно эти строки — не внутренние
  /// `reading | silent | aside`, которыми он их зовёт у себя.
  final String wire;

  /// Что рисовать — из того, что сервер на самом деле прислал.
  ///
  /// **Интересна здесь именно ветка без поля**, потому что старый ответ не
  /// умеет отличить приветствие от молчащей карты — ровно та двусмысленность,
  /// ради снятия которой `turn_kind` и появился. С цитатами это чтение. Без них
  /// кандидатов два: «она поздоровалась», где подпись — ложь, и «карта молчит»,
  /// где правила беседы и так велят ей сказать это своими словами, то есть
  /// подпись — повтор. Выбор [conversation] меняет ложь на повтор, и это
  /// правильная сторона размена; оставленный здесь [chartSilent] — это тот
  /// самый кадр из отчёта об ошибке.
  ///
  /// Следствие, которое стоит назвать вслух: **тихая строка появляется только
  /// тогда, когда сервер назвал вид.** Молчание на проводе покупает молчание на
  /// экране. `answered_from_chart` не спрашивается здесь намеренно.
  static ChatTurnKind of(String? raw, {required List<String> citedFactors}) {
    for (final kind in ChatTurnKind.values) {
      if (kind.wire == raw) return kind;
    }
    return citedFactors.isEmpty ? conversation : reading;
  }

  /// Место ли строке «прочитано из» под этим ответом. Цитаты показываются
  /// везде, где они есть, — [care], назвавший позицию, всё-таки сделал
  /// утверждение, — с единственным исключением: [conversation] не утверждает
  /// ничего, и всё, что он процитировал, — украшение.
  bool get showsCitations => this != conversation;

  /// Место ли честной приписке под этим ответом.
  bool get showsChartSilentNote => this == chartSilent;
}

/// Ответ Alma на один вопрос. Форма снята с живого `/v1/chat`:
/// `{thread_id, message: {id, role, body, cited_factors, turn_kind}, …}`.
class ChatReply {
  const ChatReply({
    required this.threadId,
    required this.body,
    required this.citedFactors,
    this.kind = ChatTurnKind.conversation,
    this.questionsLeft,
  });

  final String? threadId;
  final String body;

  /// Что это была за реплика. Разбирается из `turn_kind`, а когда его нет — из
  /// того же, из чего его выводят нативы: наличия цитат.
  final ChatTurnKind kind;

  /// Позиции, из которых прочитан ответ. Обещание продукта: каждый ответ их
  /// называет, и лента обязана их показывать.
  final List<String> citedFactors;

  final int? questionsLeft;

  /// Абзацы — тело, разрезанное по пустой строке.
  List<String> get paragraphs =>
      body.split('\n\n').where((p) => p.trim().isNotEmpty).toList();

  factory ChatReply.fromJson(Map<String, dynamic> json) {
    final message = (json['message'] as Map?)?.cast<String, dynamic>() ?? const {};
    final cited = (message['cited_factors'] as List? ?? const [])
        .map((e) => e.toString())
        .toList();
    return ChatReply(
      threadId: json['thread_id'] as String?,
      body: message['body'] as String? ?? '',
      citedFactors: cited,
      kind: ChatTurnKind.of(message['turn_kind'] as String?, citedFactors: cited),
      questionsLeft: (json['questions_left'] as num?)?.toInt(),
    );
  }
}


/// Ссылка на беседу в списке: чем открыть и что показать в строке.
class ChatThreadRef {
  const ChatThreadRef({required this.id, this.title});

  final String id;
  final String? title;

  factory ChatThreadRef.fromJson(Map<String, dynamic> json) => ChatThreadRef(
        id: json['id'] as String? ?? '',
        title: json['title'] as String?,
      );
}

/// Одна реплика сохранённой беседы.
///
/// Роль сервер называет `user` и `alma` — не `assistant`; выдумывать второе
/// значит рисовать все ответы Alma как реплики человека.
class ChatTurn {
  const ChatTurn({
    required this.mine,
    required this.body,
    required this.citedFactors,
    this.kind = ChatTurnKind.conversation,
  });

  final bool mine;
  final String body;
  final List<String> citedFactors;

  /// Тот же вид реплики, что и у живого ответа.
  ///
  /// **Одна вью — одно правило, и разбор обязан быть один.** `GET
  /// /v1/chat/threads/{id}` отдаёт `turn_kind` наравне с живым `/v1/chat`
  /// (`readings.py:1180`), и пока порт его не читал ни там, ни там, разницы не
  /// было видно. Стоит разобрать его только в живой ленте — и то же сообщение
  /// после перезапуска нарисуется без тихой строки: ровно тот баг, из-за
  /// которого на нативе вьюху и сделали общей.
  final ChatTurnKind kind;

  factory ChatTurn.fromJson(Map<String, dynamic> json) {
    final cited = ((json['cited_factors'] as List?) ?? const [])
        .map((f) => f.toString())
        .toList();
    return ChatTurn(
      mine: (json['role'] as String?) == 'user',
      body: json['body'] as String? ?? '',
      citedFactors: cited,
      kind: ChatTurnKind.of(json['turn_kind'] as String?, citedFactors: cited),
    );
  }
}


/// Что аккаунт уже держит.
///
/// Порт `Entitlements` с iOS. Два вопроса витрины — «есть ли живой план» и
/// «куплен ли архив» — отвечаются по строкам прав, а не по `unlocked`, и
/// разница существенная: `unlocked` это плоский список систем, потому что
/// сервер разворачивает право «всё» в восемь, а не шлёт звёздочку. «Владеет
/// восемью системами» правда и про того, кто купил архив, и про того, кто
/// купил пять дверей и снимает три живых. Спрятать архив от второго — спрятать
/// то, что он вот-вот захочет.
class Entitlements {
  const Entitlements({required this.unlocked, required this.rows});

  const Entitlements.none() : unlocked = const [], rows = const [];

  /// Слаги систем, открытых прямо сейчас.
  final List<String> unlocked;

  /// Сами права: `active`, `kind` (`one_time` | `consumable` | `monthly`) и
  /// `scope` (`system` | `static` | `pair` | `all` | `live`).
  final List<Map<String, dynamic>> rows;

  bool get hasPlan =>
      rows.any((row) => row['active'] == true && row['kind'] == 'monthly');

  /// Куплен ли бандл из пяти разборов.
  ///
  /// Читается по `scope == 'static'`, а не по «открыто пять систем»: подписка
  /// тоже открывает все пять, и спрятать от подписчицы бандл значит спрятать
  /// ровно то, что она захочет перед отменой. Прежнее условие (`scope == 'all'`
  /// и разовая покупка) описывало архив $38.99, которого больше нет.
  bool get ownsArchive => rows.any((row) =>
      row['active'] == true &&
      row['scope'] == 'static' &&
      row['kind'] == 'one_time');

  bool opened(SystemSlug system) => unlocked.contains(system.slug);

  factory Entitlements.fromJson(Map<String, dynamic> json) => Entitlements(
        unlocked: ((json['unlocked'] as List?) ?? const [])
            .map((s) => s.toString())
            .toList(),
        rows: ((json['entitlements'] as List?) ?? const [])
            .whereType<Map>()
            .map((row) => row.cast<String, dynamic>())
            .toList(),
      );
}

/// Полка целиком: строки прайса и адрес, по которому подписку останавливают.
///
/// **`manage_url` — единственное поле каталога, которого клиент не знает сам.**
/// Его заполняют только магазинные переходники (`appstore.py`,
/// `googleplay.py`); у Paddle и Dodo подписку останавливает наш же
/// `POST /v1/billing/subscription/cancel`, и адреса там нет вовсе — проверено
/// живым каталогом на 8018, где стоит Dodo. Пустое значение поэтому нормальное
/// состояние, а не отказ: оно значит «продаём не через магазин».
class Catalogue {
  const Catalogue({required this.plans, this.manageUrl});

  final List<Plan> plans;

  /// Куда идти отменять, когда это не мы. Пусто — значит некуда, и решать
  /// придётся по платформе.
  final String? manageUrl;

  factory Catalogue.fromJson(Map<String, dynamic> json) => Catalogue(
        plans: ((json['items'] as List?) ?? const [])
            .map((row) => Plan.fromJson((row as Map).cast<String, dynamic>()))
            .toList(),
        manageUrl: (json['manage_url'] as String?)?.trim().isNotEmpty == true
            ? (json['manage_url'] as String).trim()
            : null,
      );
}

/// Строка полки: чем это называется, сколько стоит и что открывает.
class Plan {
  const Plan({
    required this.slug,
    required this.name,
    required this.kind,
    required this.display,
    required this.interval,
    required this.scope,
    required this.offered,
  });

  final String slug;
  final String name;

  /// `one_time`, `weekly`, `monthly`, `annual`.
  final String kind;

  /// Цена словами, как её напечатал сервер: «$78.99». Своего форматирования
  /// здесь нет намеренно — витрина и чек обязаны показывать одно число.
  final String display;

  final String interval;

  /// `system` — одна система, `all` — всё сразу.
  final String scope;

  /// `shelf` — лежит на полке; иное значение означает условную цену, которую
  /// нельзя предлагать просто так.
  final String offered;

  bool get isSubscription => kind != 'one_time';

  factory Plan.fromJson(Map<String, dynamic> json) => Plan(
        slug: json['slug'] as String? ?? '',
        name: json['name'] as String? ?? '',
        kind: json['kind'] as String? ?? 'one_time',
        display: json['display'] as String? ?? '',
        interval: json['interval'] as String? ?? '',
        scope: json['scope'] as String? ?? 'system',
        offered: json['offered'] as String? ?? '',
      );
}

/// Ступени воронки, которые шлёт приложение.
///
/// Порт `FunnelStage` из `APIModels.swift`, и список **короче** серверного
/// намеренно. `landing_view` и `portrait_view` принадлежат вебу; `purchase` и
/// `daily_sent` сервер помечает `server_known` и отвечает на них 422 — они
/// пишутся из платёжной записи и из отправки уведомления, а не из телефона.
/// Слать их отсюда значило бы измерять собственное намерение вместо факта.
enum FunnelStage {
  quizStart('quiz_start'),
  quizComplete('quiz_complete'),
  offerView('offer_view'),
  checkoutOpened('checkout_opened'),
  purchaseCompleted('purchase_completed'),
  offerDeclined('offer_declined'),

  /* ── лестница монетизации v3 (§7 ТЗ) ──────────────────────────────────────
     Каждая из этих ступеней **обязана** нести `surface` из §3 ТЗ: сервер
     помечает их `monetization=True` и без поверхности не пишет вовсе
     (`alma/funnel.py`, `SurfaceMissing`). Поэтому их шлёт маршрутизатор
     пейволлов, а не экраны: поверхность известна намерению
     ([PaywallIntent.surfaceCode]), и посчитанная по месту она разойдётся с ним
     в первый же день, когда два экрана начнут продавать одно и то же.        */

  /// Пейволл показан. `surface`, `sku`, `trigger`.
  paywallShown('paywall_shown'),

  /// Пейволл закрыт. `method` — крестиком, «не сейчас» или жестом назад.
  paywallDismissed('paywall_dismissed'),

  /// Поднялся системный лист покупки. Не переименованный `checkout_opened`:
  /// тот пишет сервер, открывая сессию для браузера, этот — телефон.
  checkoutStarted('checkout_started'),

  /// Свободные вопросы кончились, и человек отправил следующий.
  questionQuotaHit('question_quota_hit'),

  /// Вход в отмену подписки — до всякого редиректа в настройки магазина.
  cancelFlowEntered('cancel_flow_entered'),

  /// Показан и принят оффер спасения. Их отношение и есть «save-оффер спасает
  /// ≥10% отмен» из §7.
  saveOfferShown('save_offer_shown'),
  saveOfferAccepted('save_offer_accepted');

  const FunnelStage(this.wire);

  /// Имя, которое знает сервер (`alma/funnel.py`).
  final String wire;
}
