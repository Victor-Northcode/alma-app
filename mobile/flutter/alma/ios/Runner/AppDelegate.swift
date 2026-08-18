import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  /// Канал до `lib/notify/push_devices.dart`.
  ///
  /// **Токен APNs не даёт ни один пакет, и это решение, а не пробел.**
  /// `docs/PUSH.md §2.1` отказался гонять iOS через FCM: бэкенд ходит в APNs
  /// напрямую, а значит Firebase в этой сборке нечего делать. Токен же выдаёт
  /// сама iOS — методом делегата приложения, — и всё, чего не хватало, это
  /// двадцати строк, чтобы передать его наверх.
  private var push: FlutterMethodChannel?

  /// Дартовый вызов, который ждёт ответа делегата.
  ///
  /// Ровно один: `registerForRemoteNotifications` отвечает не возвратом, а
  /// вызовом одного из двух методов ниже — когда-нибудь. Между просьбой и
  /// ответом лежит сеть, поэтому ожидание живёт здесь, а не в стеке.
  private var waiting: FlutterResult?

  /// Пуш, по которому приложение открыли, — пока Dart не был готов слушать.
  ///
  /// Тап по уведомлению будит процесс раньше, чем поднимется движок Flutter:
  /// ответ делегата приходит в первые миллисекунды, а канал начинают слушать
  /// секундой позже. Потерять этот единственный тап — значит не досчитать
  /// ровно тех, кого пуш привёл, то есть саму метрику `push_opened` (§7 ТЗ).
  /// Поэтому payload ждёт здесь, и Dart забирает его методом `launchPush`.
  private var pendingOpen: [String: Any]?

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    UNUserNotificationCenter.current().delegate = self
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  /// Тап по уведомлению — и в работающем приложении, и в мёртвом.
  override func userNotificationCenter(
    _ center: UNUserNotificationCenter,
    didReceive response: UNNotificationResponse,
    withCompletionHandler completionHandler: @escaping () -> Void
  ) {
    let payload = response.notification.request.content.userInfo
    var opened: [String: Any] = [:]
    // Наверх едут только строковые поля верхнего уровня: серверный payload
    // кладёт тип пуша строкой (`type`), и большего каналу знать не нужно.
    for (key, value) in payload {
      if let name = key as? String, let text = value as? String {
        opened[name] = text
      }
    }
    if let channel = push {
      channel.invokeMethod("pushOpened", arguments: opened)
    } else {
      pendingOpen = opened
    }
    completionHandler()
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)

    let channel = FlutterMethodChannel(
      name: "ai.pazl.alma/push",
      binaryMessenger: engineBridge.applicationRegistrar.messenger()
    )
    channel.setMethodCallHandler { [weak self] call, result in
      switch call.method {
      case "apnsToken":
        self?.requestToken(result)
      case "launchPush":
        // Пуш, открывший мёртвое приложение. Отдаётся один раз: второй вопрос
        // получает nil, и Dart не насчитает два открытия из одного тапа.
        result(self?.pendingOpen)
        self?.pendingOpen = nil
      default:
        result(FlutterMethodNotImplemented)
      }
    }
    push = channel
  }

  /// Попросить у APNs токен этого устройства.
  ///
  /// Разрешение спрашивает Dart (`permission_handler`) **до** этого вызова, и
  /// порядок обязателен только в одну сторону: регистрация без разрешения
  /// технически проходит и токен даёт, но показывать по нему будет нечего.
  private func requestToken(_ result: @escaping FlutterResult) {
    if let pending = waiting {
      // Второй вопрос, пока первый не ответил. Отпускаем предыдущего — иначе
      // его `FlutterResult` не позовут никогда и дартовый вызов повиснет
      // навсегда.
      pending(FlutterError(code: "superseded", message: "новый запрос токена", details: nil))
    }
    waiting = result
    UIApplication.shared.registerForRemoteNotifications()

    // **Своя граница ожидания.** APNs не обязан отвечать: в самолётном режиме
    // ни один из двух методов делегата не вызывается вовсе, и без этого
    // таймера экран пред-вопроса стоял бы на «Разрешить» до перезапуска.
    // Двадцать секунд — заметно больше сети и заметно меньше терпения.
    DispatchQueue.main.asyncAfter(deadline: .now() + 20) { [weak self] in
      guard let self, self.waiting != nil else { return }
      self.finish(.failure("timeout", "APNs не ответил"))
    }
  }

  override func application(
    _ application: UIApplication,
    didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
  ) {
    super.application(application, didRegisterForRemoteNotificationsWithDeviceToken: deviceToken)
    // Шестнадцатеричная строка, потому что путь запроса к APNs — это она же
    // (`PUSH.md §1.5`), и никакого другого представления сервер не примет.
    let hex = deviceToken.map { String(format: "%02x", $0) }.joined()
    finish(.token(hex))
  }

  override func application(
    _ application: UIApplication,
    didFailToRegisterForRemoteNotificationsWithError error: Error
  ) {
    super.application(application, didFailToRegisterForRemoteNotificationsWithError: error)
    // Самая частая причина — сборка без возможности Push Notifications:
    // профиль без `aps-environment` получает отказ здесь, а не при отправке.
    // Dart считает это «слать пока некуда» и идёт дальше — экран анкеты не
    // место для сообщения о настройках учётной записи Apple.
    finish(.failure("unavailable", error.localizedDescription))
  }

  private enum Answer {
    case token(String)
    case failure(String, String)
  }

  /// Ответить дартовой стороне ровно один раз.
  ///
  /// Два `result(...)` на один вызов — это «Reply already submitted» в логе и
  /// потерянный ответ; поэтому ожидание обнуляется до вызова, а не после.
  private func finish(_ answer: Answer) {
    guard let result = waiting else { return }
    waiting = nil
    switch answer {
    case .token(let hex):
      result([
        "token": hex,
        // Версия сборки и версия системы едут вместе с токеном: на сервере
        // они нужны затем, чтобы «перестало работать четырнадцатого» имело
        // ответ (`PUSH.md §3`). Отдельного пакета ради двух строк из
        // `Info.plist` брать незачем.
        "app_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "",
        "os_version": UIDevice.current.systemVersion,
      ])
    case .failure(let code, let message):
      result(FlutterError(code: code, message: message, details: nil))
    }
  }
}
