import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;
import 'dart:ui' show PlatformDispatcher;

import 'package:flutter/foundation.dart'
    show ValueNotifier, kIsWeb, kReleaseMode;
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart'
    show AppLifecycleState, WidgetsBinding, WidgetsBindingObserver;
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../net/alma_client.dart';

/// Чем закончился разговор про уведомления.
///
/// Четыре исхода, и различие нужно не для отчёта, а для поведения: только
/// [denied] — необратимый ответ, за который система больше не спросит, и только
/// [registered] значит, что сервер знает, куда слать.
enum PushOutcome {
  /// Разрешение есть, токен получен, устройство записано на сервере.
  registered,

  /// Разрешение есть, а слать всё равно некуда: на Android нет регистрации FCM
  /// (нет проекта Firebase), на симуляторе без учётной записи Apple iOS не
  /// выдаёт токен. Не ошибка и не отказ — просто транспорта пока нет.
  granted,

  /// Система сказала «нет». Повторно она об этом не спросит: iOS помнит ответ
  /// до переустановки, Android 13 — тоже (`docs/PUSH.md §5.1`).
  denied,

  /// Разрешение есть, токен есть, сервер не ответил. Единственный исход,
  /// который чинится сам: [AlmaPush.sync] повторит при следующем запуске.
  offline,
}

/// Тап по уведомлению, которому ещё некому было ответить.
///
/// **Зачем признак, а не вызов.** Слушателя у тапа двое, и они живут в разных
/// местах дерева: корень (`AlmaApp`) пишет ступень воронки — там есть сессия, —
/// а открывает место оболочка (`CabinetShell`), потому что вкладки и стек
/// «Моих систем» знает только она. [AlmaPush.onOpened] — одно поле, и второй
/// присвоивший затёр бы первого. Ровно то же решение и по той же причине, что
/// у `almaDraft` в `state/ask_alma.dart`.
///
/// **И зачем он не гаснет сам.** Тап по мёртвому приложению доезжает раньше,
/// чем построится кабинет: `AlmaPush.listen` забирает его у делегата в первые
/// миллисекунды, а на экране в это время заставка, а то и анкета. Вызов в эту
/// секунду ушёл бы в пустоту — навигатора вкладок ещё нет. Признак ждёт, пока
/// кабинет действительно откроется, и гасит его тот, кто открыл место.
///
/// Полезная нагрузка — как её отдал сервер (`docs/PUSH.md §2.3`): `type` из
/// закрытого списка и, у пары, `profile_id`.
final ValueNotifier<Map<String, String>?> pushedOpen = ValueNotifier(null);

/// Уведомления на стороне телефона: разрешение, токен устройства, регистрация.
///
/// Порядок вопросов — единственное, что здесь по-настоящему дорого, и он
/// записан в `docs/PUSH.md §5.5`: **сначала спрашивает приложение своим
/// экраном, и только потом система.** Причина механическая, а не вежливая. Наш
/// вопрос повторяемый: человек, нажавший «Не сейчас», встретит его снова.
/// Системный — нет: iOS показывает своё окно один раз за установку, Android 13
/// после отказа не показывает его до переустановки. Значит системное окно —
/// расходуемый ресурс, и тратить его вслепую нельзя. Экран пред-вопроса
/// (`screens/journey/push_ask_screen.dart`) существует ровно для этого, и
/// [ask] вызывается только из него — после того, как человек уже сказал «да»
/// нам.
///
/// **Токен получает не пакет, а сама iOS.** `PUSH.md §2.1` отказался гонять
/// iOS через FCM: бэкенд ходит в APNs напрямую, и токен приходит из
/// `application(_:didRegisterForRemoteNotificationsWithDeviceToken:)` в
/// `ios/Runner/AppDelegate.swift` через канал [_channel]. На Android тем же
/// каналом приходит токен FCM — из `MainActivity.kt`, нативно, а не пакетом
/// `firebase_messaging`: `PUSH.md §7.1` защищает строку «iOS links no
/// third-party framework at all», а кроссплатформенный плагин затащил бы
/// Firebase и в iOS-сборку. `PUSH.md §2.1`: на Android у FCM альтернативы нет,
/// на iOS — есть, и мы ей пользуемся.
///
/// **Ничто не заперто за ответом.** Guideline 5.1.2(i): отказавшийся получает
/// тот же продукт, а «Сегодня» показывает то же самое чтение внутри
/// приложения. Уведомление — указатель на него, а не способ его прочесть.
class AlmaPush {
  AlmaPush._();

  /// Одна на приложение: у телефона один токен, и два владельца этого знания
  /// разошлись бы в первый же день.
  static final AlmaPush instance = AlmaPush._();

  /// Канал до `AppDelegate`. Имя — с идентификатором продукта, а не `push`:
  /// каналы плагинов живут в том же пространстве имён, и «push» там занять
  /// может кто угодно.
  static const MethodChannel _channel = MethodChannel('ai.pazl.alma/push');

  /// Что мы уже сказали серверу, чтобы было чем это отменить.
  ///
  /// В настройках, а не в связке ключей: токен устройства — не секрет и не
  /// аккаунт, Apple прямо просит его **не** кэшировать как ценность, а
  /// единственный смысл записи — знать, что удалять при выходе. Переживать
  /// удаление приложения ей незачем: удалённое приложение всё равно получит
  /// 410 и строка уйдёт сама (`notify/tokens.py`).
  static const String _memory = 'alma.push.device';

  /// Показывали ли уже экран пред-вопроса (`PushAskScreen`).
  ///
  /// Хранится отдельно от разрешения, потому что `Permission.notification.status`
  /// не отличает «человек отказал» от «ещё не спрашивали»: iOS отвечает `denied`
  /// в обоих случаях, а системный вопрос — одноразовый (`PUSH.md §5.5`). Пишется
  /// **до** показа экрана, как `OnboardingMemory.markSeen`, — прибитое на
  /// полпути приложение не должно спросить дважды.
  static const String _preAsked = 'alma.push.preasked';

  /// Пора ли показать пред-вопрос: ещё не показывали и разрешения ещё нет.
  Future<bool> preAskDue() async {
    if (kIsWeb) return false;
    if (await allowed) return false;
    final prefs = await SharedPreferences.getInstance();
    return !(prefs.getBool(_preAsked) ?? false);
  }

  /// Запомнить, что пред-вопрос показан. Один раз и навсегда: «не сейчас» —
  /// ответ, а не пауза (тот же закон, что у пилюли).
  Future<void> markPreAsked() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_preAsked, true);
  }

  /// Кто слушает открытия по пушу. Ставит оболочка при старте; пока пусто —
  /// открытия копятся некуда, и это честно: считать их некому.
  void Function(Map<String, String> payload)? onOpened;

  /// Начать слушать тапы по уведомлениям — живые и тот, что открыл процесс.
  ///
  /// Живой тап приходит вызовом `pushOpened` с той стороны канала; тап по
  /// мёртвому приложению делегат придерживает у себя, и его забирает разовый
  /// вопрос `launchPush` — см. AppDelegate о том, почему иначе он терялся бы.
  Future<void> listen() async {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'pushOpened') _deliver(call.arguments);
      return null;
    });
    try {
      _deliver(await _channel.invokeMethod<dynamic>('launchPush'));
    } catch (_) {
      // Тут нечего чинить: нет нативной стороны — нет и открытий.
    }
  }

  void _deliver(dynamic raw) {
    if (raw is! Map) return;
    final payload = <String, String>{
      for (final entry in raw.entries)
        if (entry.key is String && entry.value is String)
          entry.key as String: entry.value as String,
    };
    onOpened?.call(payload);
  }

  /// Разговоры с системой идут по одному, в очередь.
  ///
  /// **Не отбрасывание второго зова, а именно очередь.** Кнопка «Разрешить»
  /// блокируется на время запроса, но [sync] зовут ещё и по возвращению в
  /// приложение, и это разные вопросы: отдав второму исход первого, мы бы
  /// иногда не показывали системное окно вовсе. Два
  /// `registerForRemoteNotifications` подряд при этом дали бы два ожидания
  /// одного ответа делегата, поэтому и очередь.
  Future<PushOutcome>? _running;

  Future<PushOutcome> _queue(Future<PushOutcome> Function() work) {
    final previous = _running;
    final next = previous == null
        ? work()
        : previous.then<PushOutcome>((_) => work(), onError: (_) => work());
    _running = next;
    next.whenComplete(() {
      if (identical(_running, next)) _running = null;
    });
    return next;
  }

  /// Разрешение спрошено, токен взят, устройство записано.
  ///
  /// Зовётся **после** нашего экрана и только по нажатию «Разрешить». Ничего
  /// не бросает: у экрана анкеты нет ответа на отказ сети, и человек в хвосте
  /// путешествия не должен встретить сообщение об ошибке вместо следующего
  /// шага.
  Future<PushOutcome> ask(AlmaClient client) => _queue(() => _ask(client));

  Future<PushOutcome> _ask(AlmaClient client) async {
    if (kIsWeb) return PushOutcome.granted;
    if (!await _request()) {
      // Отказ окончателен, и запись о прошлой регистрации теперь враньё.
      await _remember(null);
      return PushOutcome.denied;
    }
    return _register(client);
  }

  /// Сверить, что знает система, с тем, что знает сервер.
  ///
  /// Зовётся на запуске и по возвращению в приложение, и делает две разные
  /// вещи. Если разрешение есть — перерегистрирует устройство: это прямое
  /// указание Google («ставить отметку времени при каждой выгрузке, менялся
  /// токен или нет»), и то же самое чинит часовой пояс тому, кто прилетел в
  /// другую страну, — `notify/tokens.py` обновляет строку целиком.
  ///
  /// Если разрешение **отозвали** в настройках телефона — снимает устройство с
  /// учёта. `PUSH.md §5.6`: правда о разрешении живёт в системе, а не в нашем
  /// флаге, и переключатель, который говорит «включено» поверх отозванного
  /// разрешения, — это обещание, которого никто не сдержит.
  Future<PushOutcome> sync(AlmaClient client) {
    _watch(client);
    return _queue(() => _sync(client));
  }

  Future<PushOutcome> _sync(AlmaClient client) async {
    if (kIsWeb) return PushOutcome.granted;
    if (!await allowed) {
      // Спрашивать заново нечего — система уже ответила и переспрашивать себе
      // дороже. Единственное честное действие: перестать ждать доставки.
      await forget(client);
      return PushOutcome.denied;
    }
    return _register(client);
  }

  /// Снять это устройство с учёта: `POST /v1/notifications/devices/delete`.
  ///
  /// **Выход из аккаунта, отозванное разрешение, удаление аккаунта.** Первые
  /// два обязаны сказать это сами; третий сервер делает и без нас —
  /// `accounts.erase` зовёт `tokens.forget`, — но местную запись всё равно надо
  /// стереть, иначе следующий гость на этом же телефоне унаследует
  /// уверенность, что он зарегистрирован.
  ///
  /// Молча при отказе сети и **запись стирается в любом случае**: строку,
  /// пережившую неудачное удаление, через девяносто дней молчания уберёт
  /// `tokens.sweep`, а вот запись, пережившая выход, врала бы вечно.
  Future<void> forget(AlmaClient client) async {
    final device = await _registered();
    await _remember(null);
    if (device == null) return;
    try {
      await client.forgetDevice(
        platform: device['platform'] as String,
        token: device['token'] as String,
      );
    } on AlmaError {
      // Молча: см. выше.
    }
  }

  /// Разрешает ли система показывать уведомления **прямо сейчас**.
  ///
  /// Спрашивается у системы, а не у своей памяти: разрешение отзывают в
  /// настройках телефона, и приложение об этом никто не уведомляет.
  ///
  /// `provisional` считается разрешением, и это не натяжка: на iOS это рабочее
  /// состояние, в котором уведомления приходят тихо, в центр уведомлений, с
  /// кнопками «Оставить» и «Выключить» (`PUSH.md §5.4`). Человек, проживший в
  /// нём год, получает продукт, а не сломанную функцию.
  Future<bool> get allowed async {
    if (kIsWeb) return false;
    final status = await Permission.notification.status;
    return _known = status.isGranted || status.isProvisional || status.isLimited;
  }

  /// Открыть страницу приложения в настройках телефона.
  ///
  /// Единственный путь назад из отказа: второго системного вопроса ни одна из
  /// платформ не даёт (`PUSH.md §5.5`). Живёт здесь, а не на экране настроек,
  /// чтобы `permission_handler` знал ровно один файл продукта — иначе через
  /// месяц его будут звать из трёх мест с тремя разными представлениями о том,
  /// что считается разрешением.
  Future<void> openSystemSettings() async {
    if (kIsWeb) return;
    await openAppSettings();
  }

  /// Что система отвечала в прошлый раз.
  ///
  /// Существует ради возвращений в приложение. Разрешение отзывают редко, а
  /// между приложениями переключаются десятки раз в день, и сверять состояние
  /// **запросом к серверу** на каждое возвращение значило бы платить сетью за
  /// событие, которого почти никогда не происходит. Система отвечает локально
  /// и мгновенно; на сервер уходит только то возвращение, на котором ответ
  /// изменился.
  bool? _known;

  bool _watching = false;

  /// Слушать возвращения в приложение. Ставится при первом [sync] и живёт до
  /// конца: `PUSH.md §5.6` — правда о разрешении в системе, а не в нашем
  /// флаге, и человек, выключивший уведомления в настройках телефона, не
  /// должен остаться строкой, которой каждое утро что-то шлют.
  void _watch(AlmaClient client) {
    if (_watching || kIsWeb) return;
    _watching = true;
    WidgetsBinding.instance.addObserver(_Foreground(() async {
      final before = _known;
      if (await allowed != before) await sync(client);
    }));
  }

  /// Системное окно. Возвращает, разрешили ли.
  Future<bool> _request() async {
    try {
      final status = await Permission.notification.request();
      return _known =
          status.isGranted || status.isProvisional || status.isLimited;
    } on PlatformException {
      // Платформа без уведомлений (или без плагина): не отказ человека, а
      // отсутствие механизма. Считается отказом, потому что слать всё равно
      // некуда, но запоминать тут нечего.
      return false;
    }
  }

  /// Токен на сервер.
  Future<PushOutcome> _register(AlmaClient client) async {
    final device = await _identity();
    if (device == null) return PushOutcome.granted;
    try {
      await client.registerDevice(device);
      await _remember({
        'platform': device.platform,
        'token': device.token,
      });
      return PushOutcome.registered;
    } on AlmaError {
      // Записывать нечего: сервер о токене не узнал, и снимать с учёта нечего.
      // `sync` повторит при следующем запуске.
      return PushOutcome.offline;
    }
  }

  /// Кто мы для APNs или для FCM. `null` — транспорта на этой платформе нет.
  Future<PushDevice?> _identity() async {
    if (kIsWeb) return null;
    final apple = Platform.isIOS;
    if (!apple && !Platform.isAndroid) return null;
    Map<Object?, Object?>? answer;
    try {
      answer = await _channel.invokeMethod<Map<Object?, Object?>>(
        apple ? 'apnsToken' : 'fcmToken',
      );
    } on PlatformException {
      // iOS — `didFailToRegisterForRemoteNotifications`: чаще всего сборка без
      // возможности Push Notifications в профиле, реже — симулятор, не
      // связанный с учётной записью Apple. Android — `fcm_unavailable`: чаще
      // всего устройство без Google Play services, где токена не будет никогда.
      // И то и другое чинит владелец или сама железка, а не приложение, и
      // падать здесь незачем.
      return null;
    } on MissingPluginException {
      return null;
    }
    final token = answer?['token'] as String?;
    if (token == null || token.isEmpty) return null;
    return PushDevice(
      platform: apple ? 'ios' : 'android',
      token: token,
      // **Среда решается сборкой, а не настройкой сервера.** `PUSH.md §1.8`:
      // токен осмыслен только в той среде, что его выдала, а TestFlight — это
      // `production`, сколько бы он ни назывался тестированием. Отладочная и
      // профильная сборки несут `aps-environment: development`, релизная —
      // `production`, и `kReleaseMode` различает ровно это. Ошибиться здесь
      // значит получить `200` на каждую отправку и тишину на телефоне.
      // На Android поле бессмысленно, и сервер это знает: `tokens.clean`
      // для платформы `android` возвращает `production`, что бы ни прислали.
      // Шлём то же слово, а не `null`, чтобы колонка не стала трёхзначной —
      // ровно то, что объясняет `ENVIRONMENTS` в `notify/tokens.py`.
      environment:
          apple ? (kReleaseMode ? 'production' : 'sandbox') : 'production',
      // `null` — законный ответ и он значит «не знаем»; см. [PushDevice.timezone].
      timezone: AlmaClient.deviceTimezone(),
      // Язык **телефона**, а не аккаунта: iOS подставляет `loc-args` в строку
      // из бандла на языке устройства, и сервер должен переводить аргументы в
      // тот же язык (`PUSH.md §1.6`).
      locale: PlatformDispatcher.instance.locale.toLanguageTag(),
      appVersion: answer?['app_version'] as String?,
      osVersion: answer?['os_version'] as String?,
    );
  }

  /// Что мы уже сказали серверу — то, что можно отменить.
  Future<Map<String, dynamic>?> _registered() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_memory);
    if (raw == null) return null;
    try {
      final parsed = jsonDecode(raw);
      return parsed is Map<String, dynamic> ? parsed : null;
    } catch (_) {
      return null;
    }
  }

  Future<void> _remember(Map<String, dynamic>? device) async {
    final prefs = await SharedPreferences.getInstance();
    if (device == null) {
      await prefs.remove(_memory);
    } else {
      await prefs.setString(_memory, jsonEncode(device));
    }
  }

  // Зоны устройства здесь больше нет: она одна на приложение и живёт в
  // `AlmaClient.deviceTimezone`. Копия стояла тут «временно», разошлась с
  // оригиналом ровно тем способом, каким расходятся копии, — и обе отвечали
  // 'UTC' там, где не знали ответа. Одна функция — одно правило.
}

/// Возвращение в приложение — единственное событие жизненного цикла, которое
/// здесь что-то значит.
class _Foreground with WidgetsBindingObserver {
  _Foreground(this.onReturn);

  final Future<void> Function() onReturn;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) onReturn();
  }
}

/// Одна установка, как её описывает `DeviceIn` в `api/routers/notify.py`.
///
/// Форма снята **с кода маршрута**, а не с документации: `platform` — только
/// `ios` или `android`, `token` — от 32 до 512 символов, `environment` — только
/// `sandbox` или `production` и только для iOS.
class PushDevice {
  const PushDevice({
    required this.platform,
    required this.token,
    required this.environment,
    required this.timezone,
    required this.locale,
    this.appVersion,
    this.osVersion,
  });

  final String platform;
  final String token;
  final String environment;

  /// Часовой пояс телефона — или `null`, когда узнать его не удалось.
  ///
  /// **Обязательным он быть не может, потому что мы его иногда не знаем.**
  /// Поле было `String`, и заполнялось оно догадкой 'UTC' — то есть незнание
  /// приезжало на сервер под видом знания и садилось в строку устройства,
  /// откуда бьёт по часу доставки: `notify/rules.zone_for` ставит зону
  /// устройства **выше** зоны рождения, так что выдуманная UTC побеждала
  /// настоящую и будила подписчика в Окленде среди ночи. Тот же сервер у себя
  /// ступень UTC снёс намеренно («законная зона для того, кто в ней живёт, и
  /// незаконная догадка») — клиент обходил защиту снаружи.
  final String? timezone;
  final String locale;
  final String? appVersion;
  final String? osVersion;

  /// Пустые поля **не отправляются**: `DeviceIn` объявлен `extra="forbid"`, и
  /// хотя `null` там законен, посланное `null` перетирало бы известное сервером
  /// ничем. `tokens.register` обновляет поле только когда оно пришло непустым —
  /// то же правило с той же стороны. Зона идёт этим же путём: неизвестная не
  /// отправляется вовсе, и прежняя известная серверу остаётся на месте.
  Map<String, dynamic> toJson() => {
        'platform': platform,
        'token': token,
        'environment': environment,
        'timezone': ?timezone,
        'locale': locale,
        if (appVersion != null) 'app_version': appVersion,
        if (osVersion != null) 'os_version': osVersion,
      };
}

/// Две ручки устройств, положенные рядом с тем, кто ими пользуется.
///
/// **Здесь они временно.** Их место — `lib/net/alma_client.dart`, рядом с
/// `dailySettings` и `setDaily`, которые ходят на тот же `/v1/notifications`;
/// тот файл сейчас занят другой работой, а расширение переносится оттуда сюда и
/// обратно одним движением, ничего не меняя в вызовах. Вместе с переносом
/// исчезнет и [_call] со своей сборкой заголовков: `AlmaClient._send` делает
/// всё это в одном месте и делает больше — читает новый токен из заголовка
/// ответа и чистит хранилище на 410.
extension PushDevices on AlmaClient {
  /// `POST /v1/notifications/devices` — записать этот телефон.
  ///
  /// Зовётся на **каждом** запуске, а не однажды: строка на сервере хранит
  /// `last_seen_at`, по которому через девяносто дней молчания её сметут, и
  /// часовой пояс, который меняется у того, кто переехал.
  Future<void> registerDevice(PushDevice device) =>
      _call(this, '/v1/notifications/devices', device.toJson());

  /// `POST /v1/notifications/devices/delete` — забыть этот телефон.
  ///
  /// POST, а не DELETE с телом: маршрут снимает уведомления, и он обязан
  /// сработать с первого раза — а DELETE с телом прокси и клиенты поддерживают
  /// вразнобой. Причина записана и на той стороне, в `notify.py`.
  Future<void> forgetDevice({
    required String platform,
    required String token,
  }) =>
      _call(this, '/v1/notifications/devices/delete', {
        'platform': platform,
        'token': token,
      });
}

/// Запрос с теми же заголовками, что кладёт `AlmaClient._send`.
///
/// Токен читается **своим** `TokenStore`: хранилище одно на приложение, а его
/// кэш — деталь экземпляра. По той же причине свежий `X-Alma-Token` из ответа
/// здесь не принимается: запись мимо кэша клиента оставила бы его с устаревшим
/// значением в памяти. Терять нечего — сервер чеканит новый токен только гостю
/// без токена, а сюда приходят с уже готовым аккаунтом.
Future<void> _call(
  AlmaClient client,
  String path,
  Map<String, dynamic> body,
) async {
  final tokens = TokenStore();
  final request = http.Request('POST', client.baseUrl.resolve(path));
  request.headers.addAll({
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    AlmaClient.anonHeader: await tokens.anonId(),
    // Неизвестной зоне здесь тоже нет заголовка: `deps.device_timezone` читает
    // его как ещё одного кандидата в зону устройства, и 'UTC' наугад испортил
    // бы час доставки ровно так же, как испортил бы его в теле запроса.
    AlmaClient.timezoneHeader: ?AlmaClient.deviceTimezone(),
  });
  // **Без токена никуда не идём, и это защита, а не проверка.** Сервер
  // встречает запрос без токена тем, что чеканит нового гостя и кладёт его в
  // заголовок ответа, — а заголовок здесь намеренно не читается. Запуск без
  // сети, на котором сессия не успела подняться, заводил бы аккаунт-сироту с
  // привязанным к нему телефоном.
  final token = await tokens.read();
  if (token == null) throw const NetworkDown('аккаунта ещё нет');
  request.headers['Authorization'] = 'Bearer $token';
  request.headers[AlmaClient.tokenHeader] = token;
  request.body = jsonEncode(body);

  http.StreamedResponse answer;
  try {
    answer = await _wire.send(request).timeout(AlmaClient.normalTimeout);
  } on TimeoutException {
    throw NetworkDown('истекло время ожидания: POST $path');
  } catch (error) {
    throw NetworkDown(error.toString());
  }

  // Тело вычитывается всегда, даже когда не нужно: недочитанный поток оставляет
  // соединение висеть до таймаута.
  final text = await answer.stream.bytesToString();
  if (answer.statusCode >= 400) {
    String message = '';
    try {
      final parsed = jsonDecode(text);
      if (parsed is Map) {
        final detail = parsed['detail'];
        message = detail is Map
            ? (detail['message'] ?? '').toString()
            : (detail ?? '').toString();
      }
    } catch (_) {}
    throw ServerRefused(status: answer.statusCode, message: message);
  }
}

/// Один клиент на приложение, а не по одному на вызов: незакрытый `http.Client`
/// держит соединения открытыми, а закрывать его после каждой регистрации значило
/// бы переустанавливать TLS на каждом запуске.
final http.Client _wire = http.Client();
