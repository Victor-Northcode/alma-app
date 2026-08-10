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
    this.advice,
  });

  final String system;
  final String chapter;
  final String title;

  /// Первая строка, бесплатная даже когда глава — нет.
  final String teaser;

  final List<String> body;

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
        advice: ((json['advice'] as String?) ?? '').trim().isEmpty
            ? null
            : json['advice'] as String,
      );
}

class ReadingResponse {
  const ReadingResponse({
    required this.reading,
    required this.cached,
    this.preview,
    this.createdAt,
  });

  final Reading reading;

  /// Пришло ли из хранилища. Глава пишется один раз и возвращается всегда;
  /// `false` значит, что человек только что оплатил само написание.
  final bool cached;

  /// Глава настоящая и неоплаченная: первый абзац показывается открыто,
  /// остальное под размытием, кнопка открытия сверху. На старых серверах поля
  /// нет, и это разбирается как «не предпросмотр».
  final bool? preview;

  final String? createdAt;

  factory ReadingResponse.fromJson(Map<String, dynamic> json) => ReadingResponse(
        reading: Reading.fromJson((json['reading'] as Map).cast<String, dynamic>()),
        cached: json['cached'] as bool? ?? false,
        preview: json['preview'] as bool?,
        createdAt: json['created_at'] as String?,
      );
}

/* ── беседа ────────────────────────────────────────────────────────────── */

/// Ответ Alma на один вопрос. Форма снята с живого `/v1/chat`:
/// `{thread_id, message: {id, role, body, cited_factors, turn_kind}, …}`.
class ChatReply {
  const ChatReply({
    required this.threadId,
    required this.body,
    required this.citedFactors,
    this.questionsLeft,
  });

  final String? threadId;
  final String body;

  /// Позиции, из которых прочитан ответ. Обещание продукта: каждый ответ их
  /// называет, и лента обязана их показывать.
  final List<String> citedFactors;

  final int? questionsLeft;

  /// Абзацы — тело, разрезанное по пустой строке.
  List<String> get paragraphs =>
      body.split('\n\n').where((p) => p.trim().isNotEmpty).toList();

  factory ChatReply.fromJson(Map<String, dynamic> json) {
    final message = (json['message'] as Map?)?.cast<String, dynamic>() ?? const {};
    return ChatReply(
      threadId: json['thread_id'] as String?,
      body: message['body'] as String? ?? '',
      citedFactors: (message['cited_factors'] as List? ?? const [])
          .map((e) => e as String)
          .toList(),
      questionsLeft: (json['questions_left'] as num?)?.toInt(),
    );
  }
}
