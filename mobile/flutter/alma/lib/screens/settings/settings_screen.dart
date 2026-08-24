import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../billing/store_words.dart';
import '../../net/alma_client.dart';
import '../../notify/push_devices.dart';
import '../../net/models.dart' show FunnelStage, SystemSlug;
import '../../state/locale_override.dart';
import '../../state/session.dart';
import '../../billing/alma_store.dart';
import '../cabinet_words.dart';
import '../onboarding/coach_anchors.dart';
import '../today/today_screen.dart' show openSubscription;
import '../paywall/cancel_save_screen.dart';
import '../paywall/paywall_router.dart';
import '../legal/legal_screen.dart';
import 'sign_in_screen.dart';
import '../legal/legal_text.dart';

/// Настройки.
///
/// Порт `mobile/ios/Alma/Screens/Settings/SettingsScreen.swift`, теперь по
/// кадрам нативного экрана, а не по памяти. Первый порт собрал те же данные
/// **не теми элементами** — пилюлями там, где у натива строки списка, — и
/// владелец назвал его кривым справедливо.
///
/// Порядок разделов нативный: аккаунт → данные рождения → каждое утро → язык →
/// план → данные и документы.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  Map<String, dynamic>? _daily;
  Map<String, dynamic>? _plan;

  /// Куда сервер велит идти отменять подписку — `manage_url` с полки.
  ///
  /// Заполняют его только магазинные переходники; у Paddle и Dodo подписку
  /// останавливаем мы сами, и поля в ответе нет вовсе. `null` поэтому значит
  /// «сервер не назвал адреса», а не «не успели спросить».
  String? _manageUrl;

  bool _started = false;

  /// Не «нет данных», а «спросили и не ответили». Раздел, который просто
  /// исчезает при отказе сети, врёт молча: у «каждого утра» пропадает
  /// единственный выключатель уведомлений, у плана — восстановление покупок.
  bool _dailyFailed = false;
  bool _planFailed = false;

  /// Где сейчас выгрузка данных: ничего / собираю / готово / не собралась.
  _Export _export = _Export.idle;

  /// Где сейчас удаление аккаунта. Двухшаговое намеренно: маршрут уничтожает
  /// оплаченные чтения, которые нельзя переписать слово в слово.
  _Delete _delete = _Delete.idle;
  final _confirm = TextEditingController();

  /// Где сейчас отмена подписки.
  ///
  /// **Тоже два шага, и по другой причине.** У удаления второй шаг защищает от
  /// промаха; здесь он объясняет. «Cancel any time» напечатано на каждой
  /// витрине, и человек, дошедший до этой кнопки, боится ровно одного — что
  /// отмена отберёт оплаченное. Первый шаг говорит, что не отберёт, и называет
  /// дату; списание останавливает только второй.
  _Cancel _cancel = _Cancel.idle;

  @override
  void dispose() {
    _confirm.dispose();
    super.dispose();
  }

  /// Чем этот аккаунт подтверждает себя: почтой у вошедшего, собственным
  /// идентификатором у гостя.
  ///
  /// **Гость удаляет тоже, и это тот экран, где это важнее всего.** Alma
  /// заводит серверный аккаунт на первом же запросе и кладёт в него дату,
  /// время и координату рождения раньше, чем человек увидел экран входа. Гость
  /// — не крайний случай, а состояние, в котором начинается каждая установка,
  /// и состояние, в котором лежат самые чувствительные данные из всех, что у
  /// нас есть. Требовать адрес почты как плату за удаление уже взятого — ровно
  /// то, что запрещает Guideline 5.1.1(v), и с чем рецензент встречается лично,
  /// потому что он тоже гость.
  String? _confirmationOf(AlmaSession session) =>
      session.account?.email ?? session.account?.id;

  bool _typedMatches(String? confirmation) {
    if (confirmation == null || confirmation.isEmpty) return false;
    final typed = _confirm.text.trim();
    // Адрес — без учёта регистра; идентификатор аккаунта — точно, потому что
    // он сгенерирован, а не набран по памяти, и сложенный регистр принял бы
    // почти-совпадение.
    return confirmation.contains('@')
        ? typed.toLowerCase() == confirmation.toLowerCase()
        : typed == confirmation;
  }

  Future<void> _exportEverything() async {
    setState(() => _export = _Export.working);
    try {
      final document = await SessionScope.of(context).client.exportAccount();
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/alma-export.json');
      // С отступами и отсортированными ключами: файл существует, чтобы его
      // **читали** — тот, кто его попросил, и тот, кому он его покажет.
      await file.writeAsString(
          const JsonEncoder.withIndent('  ').convert(document));
      if (mounted) setState(() => _export = _Export.ready(file.path));
    } catch (_) {
      if (mounted) setState(() => _export = _Export.failed);
    }
  }

  Future<void> _confirmDelete(AlmaSession session) async {
    final confirmation = _confirmationOf(session);
    if (!_typedMatches(confirmation)) {
      setState(() => _delete = _Delete.mismatch);
      return;
    }
    setState(() => _delete = _Delete.working);
    try {
      // **Сначала устройство, потом аккаунт.** Сервер и сам чистит строки
      // (`accounts.erase` → `tokens.forget`), но местную запись о токене он
      // достать не может: она лежит в `shared_preferences` этого телефона и
      // пережила бы удаление. Следующий гость на том же аппарате получил бы
      // `sync`, считающий себя уже зарегистрированным, и не отправил бы токен
      // заново. Отказ сети здесь не должен мешать удалению — оно важнее.
      try {
        await AlmaPush.instance.forget(session.client);
      } catch (_) {}
      await session.client.deleteAccount(confirmation!);
      if (!mounted) return;
      setState(() => _delete = _Delete.done);
      // **Дважды.** После удаления сохранённый токен указывает на строку,
      // которой больше нет; клиент чистит хранилище, когда видит 410 на
      // следующем запросе. Первый старт падает и чистит, второй не находит
      // токена и оставляет приложение без аккаунта — правильный конец для
      // того, кто только что попросил себя стереть.
      await session.start(force: true);
      await session.start(force: true);
    } on AlmaError {
      if (mounted) setState(() => _delete = _Delete.failed);
    }
  }

  /// Второй шаг отмены — единственный, который уходит на сервер.
  ///
  /// Порядок здесь тот же, что на бэкенде: сначала платёжная система, потом
  /// наша запись. Поэтому отказ значит «ничего не изменилось» буквально, и
  /// экрану есть что сказать честного — `cabPlanCancelFailed` обещает ровно
  /// это, и форма остаётся на месте, чтобы было чем повторить.
  Future<void> _confirmCancel(AlmaSession session) async {
    // Язык берётся до запроса: после `await` контекст трогать нельзя, а дата
    // из ответа нужна набранной по правилам читателя.
    final locale = L.of(context).localeName;
    setState(() => _cancel = _Cancel.working);
    try {
      final answer = await session.client.cancelSubscription();
      if (!mounted) return;
      setState(() => _cancel =
          _Cancel.done(_instantDate(locale, answer['access_until'] as String?)));
      // **Права не отзываются, и перечитываем мы не за тем.** Отмена снимает
      // `renews_at` и не трогает `expires_at`, так что доступ никуда не
      // денется. Перечитать надо строку выше: пока она говорит «Продлевается 4
      // марта», человек, только что отменивший подписку, читает это как
      // «отмена не сработала» — и следующее, что он делает, это звонок в банк.
      // После перечитывания там встанет «Действует до 4 марта. Продлеваться не
      // будет», и это уже правда.
      await _loadPlan();
    } on ServerRefused catch (refusal) {
      if (!mounted) return;
      // 409 — не поломка. Это `cancel_at_store`: подписку продал магазин,
      // сервер ничего не записал, и правильный ответ — дверь, а не извинение.
      setState(() =>
          _cancel = refusal.status == 409 ? _Cancel.atStore : _Cancel.failed);
    } on AlmaError {
      if (mounted) setState(() => _cancel = _Cancel.failed);
    }
  }

  /// «Управлять подпиской» — и один экран между нажатием и магазином.
  ///
  /// **Спасение, а не задержка.** ТЗ P8: перед редиректом в системные настройки
  /// показывается V9 — «забери свой разбор навсегда», — и показывается он один
  /// раз за жизнь подписки. Всё остальное здесь про то, куда идти дальше:
  ///
  /// * купила дверь — остаёмся на месте. Она пришла сюда за тем, чтобы не
  ///   платить дальше, и получила ровно это; вытолкнуть её после покупки в
  ///   настройки Apple значило бы продать и всё равно выпроводить;
  /// * «просто отменить» — открываем магазин, немедленно и без второго вопроса;
  /// * оффера не было (спасать нечего, уже показывали) — тоже сразу магазин.
  ///
  /// Жест «назад» с V9 не ведёт никуда: это отказ от самого разговора об
  /// отмене, и додумывать за него «всё-таки открой магазин» мы не вправе.
  Future<void> _manageSubscription() async {
    final session = SessionScope.of(context);
    // Ступень §7: вход в отмену. Она — знаменатель для обеих ступеней
    // спасения, поэтому уходит до всякого показа.
    session.client
        .track(FunnelStage.cancelFlowEntered, meta: {'surface': 'p8'});
    final outcome = await offerToSave(context);
    if (!mounted) return;
    if (outcome == PaywallOutcome.bought) {
      session.client
          .track(FunnelStage.saveOfferAccepted, meta: {'surface': 'p8'});
      // Право изменилось — строка «что открыто» обязана это показать.
      await session.refreshRights();
      return;
    }
    if (outcome == PaywallOutcome.dismissed) return;
    await launchUrl(
      manageSubscriptionUri(_manageUrl),
      mode: LaunchMode.externalApplication,
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      _loadDaily();
      _loadPlan();
    }
  }

  Future<void> _loadDaily() async {
    setState(() => _dailyFailed = false);
    // Правда о разрешении — в системе, а не в нашей записи (`PUSH.md §5.6`).
    // Разрешение отзывают в настройках телефона, и приложению об этом никто не
    // сообщает: без этой проверки выключатель говорил бы «важное по утрам»
    // поверх отозванного разрешения, и человек ждал бы писем, которых система
    // не пропустит. Спрашиваем при каждом открытии раздела — ответ локальный и
    // мгновенный, сети не стоит.
    try {
      final daily = await SessionScope.of(context).client.dailySettings();
      if (mounted) setState(() => _daily = daily);
    } catch (_) {
      if (mounted) setState(() => _dailyFailed = _daily == null);
    }
  }

  /// Система уведомления не пропускает, хотя в аккаунте они включены.

  Future<void> _loadPlan() async {
    setState(() => _planFailed = false);
    final session = SessionScope.of(context);
    try {
      final plan = await session.client.entitlements();
      if (mounted) setState(() => _plan = plan);
    } catch (_) {
      if (mounted) setState(() => _planFailed = _plan == null);
    }
    // **Адрес отмены — отдельным тихим запросом, и только у подписчика.**
    //
    // `manage_url` лежит на полке (`GET /v1/billing/catalogue`), а не в правах,
    // и нужен он ровно одной кнопке — той, что стоит под живой подпиской.
    // Спрашивать его у того, у кого подписки нет, значит класть лишний запрос
    // на каждое открытие настроек ради кнопки, которой там не будет.
    //
    // Отказ не делает раздел плана сломанным: без адреса кнопка ведёт в магазин
    // своей платформы, и для всего купленного внутри приложения это и есть
    // верный ответ.
    if (!mounted || !_hasSubscription) return;
    try {
      final shelf = await session.client.catalogue(locale: session.locale);
      if (mounted) setState(() => _manageUrl = shelf.manageUrl);
    } catch (_) {
      // Молча: у кнопки есть чем ответить и без сервера.
    }
  }

  /// Есть ли живая подписка — тот же вопрос, по которому раздел плана решает,
  /// рисовать ли кнопку магазина. Разовые покупки не считаются: у купленной
  /// навсегда двери отменять нечего.
  bool get _hasSubscription =>
      (((_plan?['entitlements'] as List?) ?? const []).whereType<Map>()).any(
          (row) => row['active'] == true && row['kind'] != 'one_time');


  /// Что стоит под строкой удаления. Подтверждение набором — не «вы уверены?»:
  /// одно нажатие мимо не должно уничтожать оплаченные чтения.
  List<Widget> _deleteState(L l, AlmaSession session) {
    final confirmation = _confirmationOf(session);
    final guest = confirmation != null && !confirmation.contains('@');
    switch (_delete) {
      case _Delete.idle:
        return const [];
      case _Delete.done:
        return [_note(l.stateAccountDeleted)];
      // **Отказ не уносит форму.** Раньше `failed` возвращал одну строку, а с
      // ней исчезали и набранное подтверждение, и обе кнопки: человек, у
      // которого запрос не прошёл, читал «не удалось» и не имел, чем повторить,
      // — оставалось закрыть и начать сначала. Ошибка стоит **под** кнопками,
      // как на нативе, и форма остаётся на месте.
      case _Delete.working:
      case _Delete.failed:
      case _Delete.confirming:
      case _Delete.mismatch:
        return [
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(l.cabPlanDeleteWarning, style: AlmaType.meta),
                // Гостю — как в макете: почему у него нет адреса, и сам код
                // под этим. Вошедшему объяснять нечего, у него подсказка стоит
                // в самом поле: «Type your email address to confirm».
                if (guest) ...[
                  const SizedBox(height: 14),
                  Text(l.cabSettingsDeleteGuestNote, style: AlmaType.meta),
                  const SizedBox(height: 6),
                  SelectableText(confirmation,
                      style: AlmaType.numeral.copyWith(
                          color: AlmaPalette.gold, fontSize: 15)),
                ],
                const SizedBox(height: 10),
                Container(
                  height: 52,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  alignment: Alignment.centerLeft,
                  decoration: BoxDecoration(
                    border: Border.all(color: AlmaPalette.hairline),
                    borderRadius: BorderRadius.circular(26),
                  ),
                  child: TextField(
                    controller: _confirm,
                    autocorrect: false,
                    enableSuggestions: false,
                    // Поле стояло пустым и без единого слова о том, что в него
                    // набирать. Подсказка — та же, что на нативе, и она разная
                    // у гостя и у вошедшего, потому что и набирают они разное.
                    keyboardType:
                        guest ? TextInputType.text : TextInputType.emailAddress,
                    style: AlmaType.body.copyWith(fontSize: 16),
                    decoration: InputDecoration(
                      border: InputBorder.none,
                      hintText: guest
                          ? l.cabSettingsDeleteConfirmGuest
                          : l.cabSettingsDeleteConfirm,
                      hintStyle: AlmaType.body
                          .copyWith(fontSize: 16, color: AlmaPalette.muted3),
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                ),
                const SizedBox(height: 14),
                Row(children: [
                  AlmaButton(
                    kind: AlmaButtonKind.danger,
                    fills: false,
                    label: _delete == _Delete.working
                        ? l.cabPlanDeleting
                        : l.cabPlanDeleteForever,
                    // Кнопка гаснет, пока набранное не совпало: отказ после
                    // нажатия — это отказ, которого можно было не допускать.
                    // И на время запроса — тоже, чтобы второе нажатие не ушло
                    // вторым удалением.
                    onTap: _typedMatches(confirmation) &&
                            _delete != _Delete.working
                        ? () => _confirmDelete(session)
                        : null,
                  ),
                  const SizedBox(width: 12),
                  AlmaButton(
                    kind: AlmaButtonKind.veil,
                    fills: false,
                    label: l.cabinetBack,
                    onTap: _delete == _Delete.working
                        ? null
                        : () => setState(() {
                              _confirm.clear();
                              _delete = _Delete.idle;
                            }),
                  ),
                ]),
                if (_delete == _Delete.mismatch ||
                    _delete == _Delete.failed) ...[
                  const SizedBox(height: 10),
                  Text(
                    _delete == _Delete.mismatch
                        ? l.cabPlanDeleteMismatch
                        : l.cabPlanDeleteFailed,
                    style:
                        AlmaType.meta.copyWith(color: AlmaPalette.disagree),
                  ),
                ],
                const SizedBox(height: 6),
              ],
            ),
          ),
        ];
    }
  }

  Widget _note(String text) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Text(text, style: AlmaType.meta),
      );

  /// Выбор уходит на сервер, экран верит себе сразу — та же оптимистика, что у
  /// языка на iOS.
  Future<void> _setDaily({String? daily, int? hour}) async {
    final updated = Map<String, dynamic>.from(_daily ?? {});
    if (daily != null) updated['daily'] = daily;
    if (hour != null) updated['hour'] = hour;
    setState(() => _daily = updated);
    try {
      final server =
          await SessionScope.of(context).client.setDaily(daily: daily, hour: hour);
      if (mounted) setState(() => _daily = server);
    } on AlmaError {
      // Экран уже показывает выбор; сервер догонит при следующем открытии.
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final l = L.of(context);
    final account = session.account;
    final profile = session.profile;

    return ScreenScaffold(
      seed: 0x53455454,
      title: l.cabSettingsTitle,
      children: [
        _Section(label: l.cabAccountLabel, children: [
          const SizedBox(height: 14),
          Text(
            // **Имя — то, которое человек дал, где бы он его ни дал.**
            //
            // Здесь читался один `account.displayName`, а он появляется только
            // после входа. Имя же вводят на втором экране путешествия, и оно
            // ложится на **профиль**: тот, кто набрал «Анатолий» и прошёл
            // восемь экранов, открывал настройки и читал, что он Гость. Ровно
            // эту ошибку нативный экран уже нашёл и исправил, а порт внёс её
            // обратно.
            //
            // Вторая половина той же ошибки — вошедший без имени. Тот, кто
            // пропустил имя в путешествии и вошёл кодом, читал «Гость» над
            // собственной почтой (поймано на эмуляторе 25.08.2026): заголовок
            // врал ровно то состояние, которое строкой ниже опровергала почта.
            _displayName(session) ??
                ((account?.isGuest ?? true) ? l.cabGuest : l.cabSignedInNoName),
            style: AlmaType.headingM.copyWith(fontSize: 22),
          ),
          if (account?.email != null) ...[
            const SizedBox(height: 4),
            Text(account!.email!, style: AlmaType.meta),
          ],
          if (account?.isGuest ?? true) ...[
            const SizedBox(height: 14),
            // Честное состояние, а не упрёк: карта живёт на этом телефоне, вход
            // делает её долговечной.
            Text(l.cabGuestNoteApp, style: AlmaType.meta),
            const SizedBox(height: 16),
            // По содержимому и слева, как на нативе: кнопка во всю ширину
            // читается как главное действие экрана, а вход здесь — предложение.
            Align(
              alignment: Alignment.centerLeft,
              // **Кнопка вела в пустоту.** `onTap: () {}` — присутствующее и
              // мёртвое действие: человек, у которого карта живёт на одном
              // телефоне, нажимал «Войти» и не получал ничего. Экрана входа в
              // порте не было вовсе, хотя строки к нему были перенесены.
              child: _OutlineButton(
                label: l.cabSignIn,
                onTap: () => Navigator.of(context, rootNavigator: true).push(
                  CupertinoPageRoute(builder: (_) => const SignInScreen()),
                ),
              ),
            ),
          ],
        ]),
        if (profile != null)
          _Section(label: l.cabBirthDataLabel, children: [
            _Row(label: l.cabSettingsDate, value: _civilDate(l.localeName, profile.birthDate)),
            _Row(
              label: l.cabSettingsTime,
              value: profile.birthTime == null
                  ? l.cabUnknownTime
                  : '${profile.birthTime} · ${profile.timezone}',
            ),
            if (profile.placeLabel != null)
              _Row(label: l.cabSettingsPlace, value: profile.placeLabel!),
            if (profile.name != null)
              _Row(label: l.cabSettingsFullName, value: profile.name!),
          ]),
        ..._everyMorning(l),
        _Section(label: l.cabSettingsLanguage, children: [
          // Выбор языка прямо здесь, попапом (владелец, 22 авг: «хочу поменять
          // сам, в выпадающей фигне»). Раньше строка отправляла в настройки
          // телефона; теперь выбранное переопределяет язык телефона
          // (LocaleOverride) и сразу же уходит на сервер — контент и интерфейс
          // переключаются вместе, без перезапуска.
          _Row(
            label: _endonym(session.locale),
            value: '',
            arrow: true,
            onTap: () => _pickLanguage(session),
          ),
        ]),
        ..._planSection(l, session),
        _Section(label: l.cabDataAndLegal, children: [
          // **Выгрузка и удаление — то, чего в порте не было вовсе.**
          //
          // Оба магазина требуют способ забрать свои данные и удалить аккаунт
          // изнутри приложения; у Play это ещё и поле формы, которое
          // проверяется. На нативе они здесь же и в этом же порядке.
          _Row(
            label: l.cabSettingsExportData,
            value: '',
            arrow: true,
            // Сначала попап с объяснением, потом работа (владелец, 22 авг):
            // выгрузка стартовала молча по тапу, и человек не знал, на что
            // согласился, пока не приехал файл.
            onTap: _export == _Export.working ? null : () => _confirmExport(l),
          ),
          _Row(
            label: l.cabSettingsDeleteAccount,
            value: '',
            arrow: true,
            danger: true,
            onTap: () => setState(() {
              _confirm.clear();
              _delete = _Delete.confirming;
            }),
          ),
          ..._deleteState(l, session),
          // **Документы — одна строка с выбором, а не пять строк списка.**
          //
          // Пять юридических строк подряд съедали пол-экрана настроек, и
          // владелец просил сократить листание (22 авг). Сам текст по-прежнему
          // в бинарнике и открывается внутри приложения — прежняя починка про
          // мёртвые ссылки на сайт не тронута, изменился только вход.
          _Row(
            label: l.cabSettingsDocuments,
            value: '',
            arrow: true,
            onTap: () => _pickDocument(l),
          ),
          // **Мелкий шрифт — в конце и мелким.**
          //
          // Кто продавец, кто оператор и чем Alma не является: это обязано
          // стоять в приложении, а не только в документе, — но стоять там, где
          // читают в конце, а не поверх содержимого.
          const SizedBox(height: 26),
          Text(l.cabMerchantLine(LegalText.merchant), style: AlmaType.meta),
          const SizedBox(height: 8),
          Text('${LegalText.operatorName} · Wyoming, United States',
              style: AlmaType.meta),
          const SizedBox(height: 8),
          Text(l.cabDisclaimer, style: AlmaType.meta),
        ]),
      ],
    );
  }

  /// «Каждое утро» — тремя строками списка с галочкой, как у натива, а не
  /// пилюлями. Под ними пояснение выбранного режима, строка часа, тихие часы,
  /// пояс устройства и счётчик точных дней.
  List<Widget> _everyMorning(L l) {
    final daily = _daily;
    // **Выключатель не исчезает.** Раздел возвращал пустой список, пока
    // `/v1/notifications` не ответит, — то есть у человека, пришедшего сюда
    // после уведомления, которого он не хотел, при отказе сети пропадала сама
    // возможность их выключить. Отказ показываем отказом, с чем повторить.
    if (daily == null) {
      if (!_dailyFailed) return const [];
      return [
        _Section(label: l.dailySettingTitle, children: [
          const SizedBox(height: 14),
          Text(l.stateOffline, style: AlmaType.meta),
          const SizedBox(height: 12),
          AlmaButton(
            kind: AlmaButtonKind.veil,
            fills: false,
            label: l.stateRetry,
            onTap: _loadDaily,
          ),
        ]),
      ];
    }
    final mode = daily['daily'] as String? ?? 'off';
    final hour = (daily['hour'] as num?)?.toInt() ?? 10;
    final zone = daily['timezone'] as String?;
    final verified = (daily['verified_days'] as num?)?.toInt();

    return [
      _Section(label: l.dailySettingTitle, children: [
        const SizedBox(height: 14),
        // **Тумблер на три положения вместо трёх строк.** Владелец (22 авг):
        // «не выбор из 3 строк, а тумблер, который можно двигать влево-вправо
        // и по центру». Отказ системы больше не живёт баннером над выбором —
        // он всплывает попапом ровно в момент, когда человек включает то, что
        // система не пропустит: объяснение в момент действия, а не мебель.
        _TriToggle(
          // Якорь пятого шага обучалки — подсвечивается сам тумблер.
          key: CoachAnchors.settingsMorning,
          labels: [
            l.dailySettingOff,
            l.dailySettingOccasionally,
            l.dailySettingOnlyWhatMatters,
          ],
          selected: switch (mode) {
            'occasional' => 1,
            'important' => 2,
            _ => 0,
          },
          onChanged: (index) {
            final value = const ['off', 'occasional', 'important'][index];
            // Статус спрашивается У СИСТЕМЫ в момент включения, а не берётся из
            // кэша загрузки экрана: человек давал разрешение секунду назад, а
            // попап всё равно говорил «выключены» — владелец поймал 24 авг.
            if (value != 'off') {
              unawaited(AlmaPush.instance.allowed.then((yes) {
                if (!mounted) return;
                if (!yes) _explainDenied(l);
              }));
            }
            _setDaily(daily: value);
          },
        ),
        if (mode != 'off') ...[
          const SizedBox(height: 14),
          Text(
            mode == 'occasional'
                ? l.dailySettingOccasionallyDetail
                : l.dailySettingOnlyMattersDetail,
            style: AlmaType.meta,
          ),
          const SizedBox(height: 14),
          // Час — одна строка со значением и шагом вверх-вниз, как на нативе.
          // Четырнадцать пилюль занимали пол-экрана ради одного числа.
          _HourRow(
            label: l.dailySettingHour,
            hour: hour,
            onChange: (value) => _setDaily(hour: value),
          ),
          const SizedBox(height: 12),
          Text(l.dailySettingQuiet, style: AlmaType.meta),
          const SizedBox(height: 6),
          if (zone != null)
            _Row(
              label: l.dailySettingTimezone,
              value: zone,
              caption: l.dailySettingTimezoneDevice,
            ),
          if (verified != null)
            _Row(label: l.dailyVerifiedLabel, value: '$verified'),
        ],
      ]),
    ];
  }

  /// Ночной попап — один вид на все три случая (отказ системы, выгрузка,
  /// документы): та же ночь, то же золото, радиус листа. Material-серый
  /// `AlertDialog` в этом продукте читался бы чужим окном.
  Future<T?> _nightDialog<T>({required WidgetBuilder builder}) =>
      showDialog<T>(
        context: context,
        barrierColor: AlmaPalette.night.withValues(alpha: 0.72),
        builder: (context) => Dialog(
          backgroundColor: AlmaPalette.night700,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
            side: BorderSide(color: AlmaPalette.hairlineGold),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 22, 20, 16),
            child: builder(context),
          ),
        ),
      );

  /// Система не пропускает уведомления — сказать попапом в момент включения,
  /// а не баннером-мебелью над тумблером (владелец, 22 авг).
  void _explainDenied(L l) {
    _nightDialog<void>(
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l.dailyStatusDenied, style: AlmaType.body),
          const SizedBox(height: 18),
          AlmaButton(
            label: l.dailyStatusOpenSettings,
            onTap: () {
              Navigator.of(context).pop();
              AlmaPush.instance.openSystemSettings();
            },
          ),
          const SizedBox(height: 8),
          Center(
            child: TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text(l.paywallNotNow,
                  style: AlmaType.meta.copyWith(color: AlmaPalette.gold)),
            ),
          ),
        ],
      ),
    );
  }

  /// Выгрузка данных — сначала попап с тем, что именно уедет в файл.
  /// Выгрузка живёт в попапе ЦЕЛИКОМ: объяснение → прогресс → «Сохранить файл»
  /// — всё в одном окне. Владелец (24 авг): «не должно быть „твой файл готов“
  /// и „сохранить“ вот тут [в списке настроек], а в попапе». Инлайновых строк
  /// под настройками больше нет.
  void _confirmExport(L l) {
    _nightDialog<void>(
      builder: (context) => StatefulBuilder(
        builder: (context, refresh) {
          final export = _export;
          Future<void> run() async {
            refresh(() {});
            await _exportEverything();
            if (context.mounted) refresh(() {});
          }

          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l.cabSettingsExportData, style: AlmaType.headingM),
              const SizedBox(height: 10),
              Text(
                switch (export) {
                  _ExportWorking() => l.cabPlanExporting,
                  _ExportReady() => l.cabExportReady,
                  _ExportFailed() => l.cabPlanExportFailed,
                  _ => l.cabExportNote,
                },
                style: AlmaType.body,
              ),
              const SizedBox(height: 18),
              if (export is _ExportReady)
                AlmaButton(
                  label: l.cabSaveFile,
                  onTap: () => Share.shareXFiles([XFile(export.path)]),
                )
              else
                AlmaButton(
                  label: export is _ExportFailed
                      ? l.stateRetry
                      : l.cabSettingsExportData,
                  onTap: export is _ExportWorking ? null : run,
                ),
              const SizedBox(height: 8),
              Center(
                child: TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: Text(
                      export is _ExportReady ? l.journeyClose : l.paywallNotNow,
                      style: AlmaType.meta.copyWith(color: AlmaPalette.gold)),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  /// Пять документов — одним попапом-списком; выбранный открывается прежней
  /// внутренней читалкой.
  void _pickDocument(L l) {
    _nightDialog<void>(
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final document in LegalDocument.values)
            InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: () {
                Navigator.of(context).pop();
                Navigator.of(this.context, rootNavigator: true).push(
                  CupertinoPageRoute(
                      builder: (context) => LegalScreen(document: document)),
                );
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 13),
                child: Text(LegalScreen.title(l, document),
                    style: AlmaType.body),
              ),
            ),
        ],
      ),
    );
  }

  /// Выбор языка. Эндонимы — имена собственные, им перевод не нужен; галочка
  /// стоит на текущем. Выбор пишется в LocaleOverride (интерфейс) и на сервер
  /// (язык, на котором Alma пишет) — одним касанием.
  void _pickLanguage(AlmaSession session) {
    const codes = ['en', 'es', 'de', 'it', 'fr', 'pt-BR', 'ru'];
    _nightDialog<void>(
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final code in codes)
            InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: () {
                Navigator.of(context).pop();
                HapticFeedback.selectionClick();
                // Код интерфейса: у сервера pt-BR, у ARB — просто pt.
                LocaleOverride.set(code == 'pt-BR'
                    ? const Locale('pt')
                    : Locale(code));
                session.setLocale(code);
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 13),
                child: Row(children: [
                  Expanded(
                      child: Text(_endonym(code), style: AlmaType.body)),
                  if (code == session.locale)
                    const Icon(Icons.check,
                        size: 18, color: AlmaPalette.gold),
                ]),
              ),
            ),
        ],
      ),
    );
  }

  /// Раздел «план» — и он стоит **всегда**.
  ///
  /// **Восстановление покупок пропадало вместе с сетью.** Весь раздел
  /// возвращал пустой список, пока `/v1/billing/entitlements` не ответит, а
  /// внутри него жила единственная в приложении кнопка «Восстановить
  /// покупки». То есть у человека, у которого запрос не прошёл — на новом
  /// телефоне, в дороге, в день, когда наш сервер лежит, — исчезала ровно та
  /// кнопка, которая для этого случая и существует, и которую Guideline 3.1.1
  /// требует держать достижимой. Теперь состояние права — внутреннее дело
  /// раздела, а восстановление стоит под ним при любом ответе.
  List<Widget> _planSection(L l, AlmaSession session) {
    final plan = _plan;
    final rows = (plan?['entitlements'] as List? ?? const [])
        .whereType<Map>()
        .map((e) => e.cast<String, dynamic>())
        .toList();
    // Подписка — активное право, купленное не навсегда. Спрашиваем `kind`, а
    // не `system`: оба повторяющихся продукта лежат под `system: "*"`, и
    // сравнение по нему объявляло месячного подписчика годовым.
    final subscription = rows
        .where((r) => r['active'] == true && r['kind'] != 'one_time')
        .firstOrNull;
    // Двери и архив: куплены один раз, держатся навсегда.
    final doors =
        rows.where((r) => r['active'] == true && r['kind'] == 'one_time').toList();
    // План, который кончился. Об этом стоит сказать вслух: одно слово «Free»
    // тому, кто платил в прошлом году, читается как потерянная запись, а не
    // как закончившийся год.
    final lapsed = subscription == null
        ? rows.where((r) => r['active'] != true && r['kind'] != 'one_time').firstOrNull
        : null;

    return [
      _Section(label: l.cabSettingsPlan, children: [
        if (plan == null && _planFailed) ...[
          const SizedBox(height: 14),
          Text(l.stateOffline, style: AlmaType.meta),
          const SizedBox(height: 12),
          AlmaButton(
            kind: AlmaButtonKind.veil,
            fills: false,
            label: l.stateRetry,
            onTap: _loadPlan,
          ),
        ] else if (plan == null) ...[
          const SizedBox(height: 14),
          Text(l.stateLoadingShort, style: AlmaType.meta),
        ] else if (subscription != null)
          ..._subscribed(l, session, subscription)
        else
          ..._unsubscribed(l, doors, lapsed),
        // **Восстановление — вне витрины.**
        //
        // Apple отклоняет приложение, которое продаёт разовые покупки и не
        // даёт их вернуть в месте, до которого можно дойти, не открывая
        // пейволл. И это же единственное, что помогает человеку с новым
        // телефоном, — случай, который действительно случается.
        const SizedBox(height: 18),
        // Успешное восстановление меняет права — раздел выше обязан
        // перечитать их сам, иначе человек видит «всё открыто снова» над
        // словом «Free».
        _RestoreRow(store: AlmaStore.shared, onRestored: _loadPlan),
      ]),
    ];
  }

  /// Активная подписка (s30): имя плана мелким, срок под ним крупным.
  ///
  /// **Это не строка списка.** Здесь стояла пара «подпись — значение» в одну
  /// строку, и в правую половину загонялось целое предложение («Действует до
  /// 14 марта 2027. Продлеваться не будет.»), которое ломалось на три строки
  /// у правого края. В макете имя плана — надпись над сроком, а срок — сам
  /// текст строки.
  List<Widget> _subscribed(
      L l, AlmaSession session, Map<String, dynamic> row) {
    final renews = _instantDate(l.localeName, row['renews_at'] as String?);
    final expires = _instantDate(l.localeName, row['expires_at'] as String?);
    final store = _boughtInStore(row);
    return [
      Padding(
        padding: const EdgeInsets.only(top: 15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_planName(l, row['kind'] as String?), style: AlmaType.meta),
            const SizedBox(height: 5),
            Text(
              // **«Продлевается» — только пока продлевается.**
              //
              // Здесь всегда печаталось «Действует до …, продлеваться не
              // будет» по `expires_at`, а `expires_at` есть и у живой
              // подписки. То есть человеку, который платит дальше, сообщали,
              // что списаний больше не будет, — и наоборот, тому, кто только
              // что отменил, ничего не подтверждали. Обе ошибки про деньги.
              //
              // Какая из трёх фраз — решает `source`, то есть кто продал, а не
              // есть ли у нас адрес: подписку из App Store списывает, чекует и
              // предупреждает Apple, чей бы адрес мы ни держали.
              renews != null
                  ? (store
                      ? l.cabPlanRenewsAtStore(renews)
                      : (session.account?.email?.isNotEmpty == true
                          ? l.cabPlanRenews(renews)
                          : l.cabPlanRenewsNoEmail(renews)))
                  : (expires != null ? l.cabPlanRunsUntil(expires) : ''),
              style: AlmaType.body
                  .copyWith(color: AlmaPalette.inkLight, fontSize: 17),
            ),
          ],
        ),
      ),
      // **Управление подпиской — у того, кто её продал, и продавцов два.**
      //
      // Ссылка в App Store стоит всегда: для всего купленного в приложении это
      // единственная дорога — ни Apple, ни Google не позволяют серверу
      // остановить подписку, принадлежащую их аккаунту, — и Guideline 3.1.2
      // требует её присутствия. Под ней, и только у подписки, купленной **не**
      // в магазине, стоит отмена в два нажатия: её платёжное средство держим
      // мы, и `POST /v1/billing/subscription/cancel` её действительно
      // останавливает.
      const SizedBox(height: 14),
      AlmaButton(
        kind: AlmaButtonKind.outline,
        fills: false,
        label: l.storeManageInStore,
        onTap: _manageSubscription,
      ),
      // Обещание про кошелёк — только там, где оно правда. У подписки,
      // купленной не в магазине, платёжное средство держим мы, и эта фраза
      // отправила бы человека искать отмену туда, где её нет.
      if (store) ...[
        const SizedBox(height: 10),
        Text(l.storeManagedBy, style: AlmaType.meta),
      ] else
        // **Граница проходит здесь.** Предложить отмену магазинной подписки
        // внутри приложения — нарушение правил магазина и обещание, которого
        // мы не можем сдержать: сервер ответит 409 и ничего не запишет.
        ..._cancelBlock(l, session, row),
      // Плашка честности W5 — после управления, а не перед ним: сначала
      // человек видит, что открыто и чем управлять, потом условие. Наоборот
      // читалось бы предупреждением (порядок — довод самого кадра).
      const SizedBox(height: 14),
      _cancelHonesty(l),
    ];
  }

  /// Что случится при отмене — словами холста (W5, `sub.cancel_honesty`).
  ///
  /// §7 ТЗ называет это главной защитой от красной линии («думала, всё входит
  /// в подписку»): подписка кончилась, часть глав закрылась — и человек обязан
  /// был прочитать об этом заранее, у строки собственного плана, а не узнать
  /// из закрывшейся главы. Сокращать и разбивать строку нельзя — правило
  /// спеки W5.
  Widget _cancelHonesty(L l) {
    final text = l.paywallV3SubCancelHonesty;
    // Зачин до первого двоеточия — цветом goldBright, как на холсте. Знак
    // ищется в переведённой строке: у всех семи языков зачин им кончается (у
    // французского перед знаком стоит узкий неразрывный — он входит в зачин).
    final at = text.indexOf(':');
    final style = AlmaType.meta.copyWith(
      fontSize: 12.5,
      height: 1.55,
      color: AlmaPalette.body.withValues(alpha: 0.78),
    );
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        // Числа кадра W5: кант золота на 0.24 и ночь-700 на 0.35. В палитре
        // таких ступеней нет, и ставятся они числом на месте — довод про
        // золотой волосяной ряд в paywall_parts.dart.
        border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.24)),
        color: AlmaPalette.night700.withValues(alpha: 0.35),
      ),
      child: at < 0
          ? Text(text, style: style)
          : Text.rich(TextSpan(style: style, children: [
              TextSpan(
                text: text.substring(0, at + 1),
                style: style.copyWith(color: AlmaPalette.goldBright),
              ),
              TextSpan(text: text.substring(at + 1)),
            ])),
    );
  }

  /// Отмена веб-подписки в два шага — и первый не отправляет ничего.
  ///
  /// Порт `cancelBlock` из `SettingsScreen.swift`. Шаг первый разворачивает
  /// объяснение: что останавливается, что остаётся, и до какого числа
  /// остаётся. Шаг второй — та же красная кнопка, и вот она уже уходит на
  /// сервер. Между ними «Оставить план», и это единственное, что здесь есть от
  /// удержания: ни скидки, ни «а давай подумаем», ни третьего экрана. Кнопка,
  /// после которой приходится ещё раз доказывать, что ты правда хочешь уйти, —
  /// это и есть тот самый тёмный узор, за который выписывают штрафы.
  List<Widget> _cancelBlock(L l, AlmaSession session, Map<String, dynamic> row) {
    switch (_cancel) {
      case _CancelIdle():
        // Только пока есть что останавливать. У подписки без `renews_at`
        // следующего списания уже нет — она либо отменена, либо доживает
        // оплаченный срок, — и сервер ответил бы 404 на кнопку, которую экран
        // не должен был показывать.
        if (row['renews_at'] == null) return const [];
        return [
          const SizedBox(height: 10),
          AlmaButton(
            kind: AlmaButtonKind.danger,
            fills: false,
            label: l.cabPlanCancelSubscription,
            // Первое нажатие не касается сети вовсе: оно разворачивает текст.
            onTap: () => setState(() => _cancel = _Cancel.confirming),
          ),
        ];

      // Форма подтверждения — и она же остаётся стоять при отказе, как у
      // удаления: у человека, чей запрос не прошёл, должно быть чем повторить,
      // а не одна строка «не получилось» вместо кнопок.
      case _CancelConfirming():
      case _CancelWorking():
      case _CancelFailed():
        final working = _cancel is _CancelWorking;
        // Конец оплаченного периода — `expires_at`, то есть ровно то число,
        // которое сервер вернёт в `access_until` вторым шагом. Голой датой, а
        // не фразой: сказать здесь «Действует до …, продлеваться не будет»
        // нельзя — до второго нажатия подписка продлевается, и это была бы
        // единственная ложь на экране, который затеян ради доверия.
        final until = _instantDate(l.localeName, row['expires_at'] as String?);
        return [
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(l.cabPlanCancelWhat, style: AlmaType.meta),
                if (until != null) ...[
                  const SizedBox(height: 8),
                  Text(until,
                      style: AlmaType.numeral
                          .copyWith(color: AlmaPalette.gold, fontSize: 17)),
                ],
                const SizedBox(height: 14),
                // Wrap, а не Row: два длинных слова рядом («Отменить подписку»
                // и «Оставить план») на узком экране и при крупном шрифте не
                // помещаются в строку, и Row вместо переноса рисует полосатое
                // переполнение.
                Wrap(spacing: 12, runSpacing: 10, children: [
                  AlmaButton(
                    kind: AlmaButtonKind.danger,
                    fills: false,
                    label: working
                        ? l.cabPlanCancelling
                        : l.cabPlanCancelSubscription,
                    // Гаснет на время запроса: второе нажатие — вторая отмена.
                    onTap: working ? null : () => _confirmCancel(session),
                  ),
                  AlmaButton(
                    kind: AlmaButtonKind.veil,
                    fills: false,
                    label: l.cabPlanKeepPlan,
                    onTap:
                        working ? null : () => setState(() => _cancel = _Cancel.idle),
                  ),
                ]),
                if (_cancel is _CancelFailed) ...[
                  const SizedBox(height: 10),
                  Text(l.cabPlanCancelFailed,
                      style:
                          AlmaType.meta.copyWith(color: AlmaPalette.disagree)),
                ],
              ],
            ),
          ),
        ];

      case final _CancelDone done:
        return [
          const SizedBox(height: 12),
          // Дата — из ответа сервера, а не из строки, которую экран показывал
          // до запроса: сервер её и считает (`max(expires_at)`), и он один
          // знает, чем кончилось.
          Text(
            done.until != null
                ? l.cabPlanCancelled(done.until!)
                : l.cabPlanCancelledNoDate,
            style: AlmaType.meta,
          ),
        ];

      case _CancelAtStore():
        // 409: подписку продал магазин, и сервер ничего не записал. Досюда
        // доходит только право без `source` — бэкенд старше этой сборки, —
        // потому что кнопки отмены у магазинной подписки нет вовсе. Ссылка в
        // App Store стоит выше, второй такой же здесь не нужно.
        return [
          const SizedBox(height: 12),
          Text(l.storeManagedBy, style: AlmaType.meta),
        ];
    }
  }

  /// Подписки нет: что открыто навсегда и чем это было раньше.
  List<Widget> _unsubscribed(
      L l, List<Map<String, dynamic>> doors, Map<String, dynamic>? lapsed) {
    final ended = _instantDate(l.localeName, lapsed?['expires_at'] as String?);
    return [
      const SizedBox(height: 14),
      Text(doors.isEmpty ? l.cabPlanFreePlan : l.cabPlanOwnedPlan,
          style: AlmaType.headingM.copyWith(fontSize: 22)),
      const SizedBox(height: 12),
      // Пара «заголовок — пояснение» та же, что на нативе: `cab.plan.freeNote`
      // у пустого счёта, `cab.plan.oneTimeNote` у того, кто уже купил дверь.
      Text(doors.isEmpty ? l.cabPlanFreeNote : l.cabPlanOneTimeNote,
          style: AlmaType.meta),
      if (ended != null) ...[
        const SizedBox(height: 8),
        Text(l.cabPlanPlanEnded(ended), style: AlmaType.meta),
      ],
      // Каждая дверь и день, когда её купили. Это тот чек, который экран
      // может показать, ничего не спрашивая у магазина.
      for (final door in doors)
        _Row(
          label: _doorName(l, door['system'] as String?),
          value: _instantDate(l.localeName, door['granted_at'] as String?) ?? '',
        ),
      // Самый недорогой посетитель с намерением, какой у этого приложения
      // бывает, — тот, кто сам открыл настройки посмотреть на план. Раздел
      // **описывал** план и не давал ничего нажать.
      const SizedBox(height: 14),
      AlmaButton(
        kind: AlmaButtonKind.outline,
        fills: false,
        label: l.cabPlansCta,
        // **Тот же экран, что у «Сегодня», — решение владельца.** Кнопка вела
        // на витрину «все планы», и одна и та же надпись открывала два разных
        // экрана: с «Сегодня» — подписку с картиной и составом, отсюда — сухой
        // список цен. «Должно быть так, как в today». Витрина осталась
        // достижимой тихой ссылкой «All plans» с самого экрана подписки —
        // ровно так, как ей и положено открываться по ТЗ (P7: только по тихим
        // ссылкам, никогда сама).
        onTap: () => openSubscription(context, trigger: 'settings_plan'),
      ),
    ];
  }

  /// Магазин ли держит это право — и, значит, его отмену. Пустой `source` —
  /// бэкенд старше этой сборки; тогда говорим меньше, а не выдумываем.
  static bool _boughtInStore(Map<String, dynamic> row) =>
      row['source'] == 'appstore' || row['source'] == 'googleplay';

  /// Как называется ступень, на которой человек стоит, — на его языке.
  ///
  /// Раньше здесь печаталось `row['system']`, и только для значения `'all'`,
  /// которого сервер не присылает: повторяющиеся продукты лежат под `"*"`.
  /// То есть в настройках подписчика стоял сырой слаг вроде `natal`.
  /// **Подписка в продукте одна — месячная.** Недельную и годовую сняли вместе
  /// с самими планами (ТЗ v3 §8): их нет ни в каталоге, ни в консолях сторов,
  /// ни на одном экране. Ветки под них печатали названия несуществующих
  /// тарифов и переживали свои товары ровно так, как переживает мёртвый код:
  /// молча, пока однажды не покажут человеку то, чего он не покупал.
  ///
  /// Историческая подписка (если такая где-то осталась) попадает в общую
  /// ветку и называется просто планом — это правда, и она не обещает года.
  static String _planName(L l, String? kind) => switch (kind) {
        'monthly' => l.cabSettingsEverythingMonthly,
        _ => l.cabSettingsPlan,
      };

  /// Как называется купленное навсегда. `"*"` — набор из пяти разборов.
  ///
  /// Сентинел `"*"` достался от архива за $38.99, который открывал все восемь
  /// систем; в монетизации v3 его нет, а под тем же сентинелом лежит набор из
  /// **пяти** разборов за $19.99. Строка архива («All eight systems») называла
  /// его чужим именем и чужим размером — в списке покупок человека, то есть
  /// там, где он проверяет, за что заплатил.
  static String _doorName(L l, String? system) {
    final slug = SystemSlug.from(system);
    // `system` живёт в расширении `CabinetWordsMore`, а не в самом классе:
    // статический член расширения зовётся по имени расширения.
    if (slug != null) return CabinetWordsMore.system(l, slug);
    return system == '*' ? l.paywallV3BundleTitle : (system ?? '');
  }

  /// Как звать этого человека: имя с карты, потом имя с аккаунта, потом никак.
  static String? _displayName(AlmaSession session) {
    final onProfile = session.profile?.name?.trim();
    if (onProfile != null && onProfile.isNotEmpty) return onProfile;
    final onAccount = session.account?.displayName?.trim();
    if (onAccount != null && onAccount.isNotEmpty) return onAccount;
    return null;
  }

  /// Гражданская дата — не мгновение. «1992-05-11» без пояса; разбор её как
  /// времени в поясе устройства делал бы её десятым мая для всех западнее
  /// Лондона.
  String _civilDate(String locale, String civil) {
    final parts = civil.split('-');
    if (parts.length != 3) return civil;
    final date =
        DateTime.utc(int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
    return DateFormat.yMMMMd(locale).format(date);
  }

  /// Мгновение — наоборот, обязано приехать в пояс читателя. `expires_at` и
  /// `renews_at` сервер отдаёт в UTC (`as_utc` там же и стоит), и отрезание
  /// хвоста по «T» печатало дату UTC: тому, кто западнее Лондона, срок плана
  /// показывался на день позже, чем он есть, — а это ровно та дата, по которой
  /// решают, отменять ли подписку.
  String? _instantDate(String locale, String? instant) {
    if (instant == null) return null;
    final parsed = DateTime.tryParse(instant);
    if (parsed == null) return null;
    return DateFormat.yMMMMd(locale).format(parsed.toLocal());
  }
}

/// Куда ведёт «управлять подпиской».
///
/// **Сначала слово сервера, потом платформа — и никогда чужой магазин.**
/// Кнопка была прибита к `apps.apple.com/account/subscriptions` без всякой
/// развилки, то есть на Android она открывала App Store: человеку, который
/// хочет перестать платить, показывали магазин, где его подписки нет. Хуже
/// отсутствующей кнопки — только кнопка, ведущая не туда.
///
/// [published] — `manage_url` с полки (`GET /v1/billing/catalogue`). Он верен
/// первым, потому что знает больше нас: Play-адаптер дописывает туда
/// `?package=…`, то есть открывает нужную строку, а не общий список
/// (`googleplay.py:1132`). Заполняют его только магазинные переходники, и
/// пустое значение — обычное состояние (на Paddle и Dodo подписку
/// останавливает наш собственный `/subscription/cancel`), а не поломка.
///
/// Адреса запасного пути — те же константы, что стоят на сервере
/// (`appstore.py:138`, `googleplay.py:119`) и в нативах. Ни один магазин не
/// даёт серверу остановить чужую подписку, поэтому Guideline 3.1.2 и правила
/// Play требуют, чтобы ссылка была, — а сборка без сети обязана назвать её
/// сама.
///
/// [onAndroid] существует ради проверки: `Platform.isAndroid` на машине, где
/// гоняют тесты, отвечает «нет» вместе с `Platform.isIOS`, и правило было бы
/// нечем прижать.
Uri manageSubscriptionUri(String? published, {bool? onAndroid}) {
  final named = published?.trim() ?? '';
  if (named.isNotEmpty) {
    final parsed = Uri.tryParse(named);
    // Только абсолютный адрес: обрывок вроде «subscriptions» открыть нечем, и
    // молча ничего не сделавшая кнопка хуже, чем кнопка в общий список.
    if (parsed != null && parsed.hasScheme && parsed.host.isNotEmpty) {
      return parsed;
    }
  }
  final android = onAndroid ?? (!kIsWeb && Platform.isAndroid);
  return Uri.parse(android
      ? 'https://play.google.com/store/account/subscriptions'
      : 'https://apps.apple.com/account/subscriptions');
}

/// Раздел: золотая подпись, гаснущая линейка и строки под ней.
class _Section extends StatelessWidget {
  const _Section({required this.label, required this.children});

  final String label;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 30),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(label.toUpperCase(), style: AlmaType.overline),
          const SizedBox(width: 12),
          Expanded(
            child: Container(
              height: 1,
              decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
            ),
          ),
        ]),
        ...children,
      ]),
    );
  }
}

/// Одна строка: подпись слева, значение справа, волосяная линия снизу.
///
/// Умеет четыре вида, все четыре есть у натива: значение, значение с подписью
/// под ним, галочка выбора и стрелка действия.
class _Row extends StatelessWidget {
  const _Row({
    required this.label,
    required this.value,
    this.caption,
    // Вид «галочка выбора» осиротел 22 авг: три строки утренней рассылки стали
    // тумблером. Умение оставлено — это один из четырёх нативных видов строки,
    // и следующий выбор из списка в настройках возьмёт его готовым.
    // ignore: unused_element_parameter
    this.checked = false,
    this.arrow = false,
    this.danger = false,
    this.onTap,
  });

  final String label;
  final String value;
  final String? caption;
  final bool checked;
  final bool arrow;

  /// Удаление аккаунта. Цветом несогласия и без заливки: залитую красную
  /// кнопку нажимают рефлексом.
  final bool danger;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final row = Container(
      padding: const EdgeInsets.symmetric(vertical: 15),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      // **Почему spaceBetween и разный вес.** У Expanded и Flexible по
      // умолчанию один и тот же flex, и Row делит свободное место поровну:
      // значение оказывалось заперто в своей половине, не доходило до правого
      // края, а «11:26 · Europe/Moscow» переносилось на две строки, хотя на
      // нативе стоит одной. Натив пишет HStack { подпись; Spacer; значение } —
      // подпись слева, значение прижато вправо, и обоим достаётся столько,
      // сколько нужно. spaceBetween делает то же самое, а вес 4/6 отдаёт
      // значению больше, потому что подписи здесь короче.
      child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
        Flexible(
          flex: 4,
          child: Text(
            label,
            style: danger
                ? AlmaType.body
                    .copyWith(color: AlmaPalette.disagree, fontSize: 17)
                : checked || onTap != null && value.isEmpty
                    ? AlmaType.body
                        .copyWith(color: AlmaPalette.inkLight, fontSize: 17)
                    : AlmaType.meta.copyWith(fontSize: 15),
          ),
        ),
        const SizedBox(width: 16),
        if (value.isNotEmpty)
          Flexible(
            flex: 6,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Значение — светлым текстовым, а не золотым засечным.
                // Засечное золото на этом экране принадлежит числам карты
                // (градусы, римские цифры), а дата рождения и город — обычные
                // факты, и натив набирает их так же, как подписи.
                Text(value,
                    style: arrow
                        ? AlmaType.meta.copyWith(color: AlmaPalette.gold, fontSize: 15)
                        : AlmaType.body
                            .copyWith(color: AlmaPalette.inkLight, fontSize: 17),
                    textAlign: TextAlign.end),
                if (caption != null)
                  Text(caption!,
                      style: AlmaType.meta.copyWith(fontSize: 12),
                      textAlign: TextAlign.end),
              ],
            ),
          ),
        if (checked) ...[
          const SizedBox(width: 10),
          const Text('✓', style: TextStyle(color: AlmaPalette.gold, fontSize: 17)),
        ],
        if (arrow) ...[
          const SizedBox(width: 8),
          const Text('↗', style: TextStyle(color: AlmaPalette.gold, fontSize: 15)),
        ],
      ]),
    );
    if (onTap == null) return row;
    return InkWell(onTap: onTap, child: row);
  }
}

/// «Приходит в 10:00 ⌃⌄» — час с шагом вверх и вниз, в границах тихих часов.
/// Тумблер на три положения: трек с тремя ячейками и ползунок, который едет
/// тапом и пальцем. Просьба владельца (22 авг) — вместо трёх строк с галочкой.
class _TriToggle extends StatelessWidget {
  const _TriToggle({
    super.key,
    required this.labels,
    required this.selected,
    required this.onChanged,
  }) : assert(labels.length == 3);

  final List<String> labels;
  final int selected;
  final ValueChanged<int> onChanged;

  void _pick(int index) {
    if (index == selected) return;
    HapticFeedback.selectionClick();
    onChanged(index);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      final cell = constraints.maxWidth / 3;
      return GestureDetector(
        // Палец тянет ползунок: позиция считается от места касания, поэтому
        // и перетаскивание, и тап попадают в одну и ту же арифметику.
        onHorizontalDragUpdate: (details) =>
            _pick((details.localPosition.dx / cell).floor().clamp(0, 2)),
        onTapUp: (details) =>
            _pick((details.localPosition.dx / cell).floor().clamp(0, 2)),
        child: Container(
          // 52, а не 44: третья подпись («Только долгие транзиты», 22 знака)
          // в треть ширины не влезала одной строкой и обрезалась многоточием —
          // владелец: «не видно, что написано» (24 авг). Теперь две строки.
          height: 52,
          decoration: BoxDecoration(
            color: AlmaPalette.veil,
            borderRadius: BorderRadius.circular(26),
            border: Border.all(color: AlmaPalette.hairline),
          ),
          child: Stack(children: [
            AnimatedAlign(
              // -1 / 0 / 1 — три положения «влево, по центру, вправо».
              alignment: Alignment(selected - 1.0, 0),
              duration: AlmaMotion.ui,
              curve: AlmaMotion.uiCurve,
              child: Container(
                width: cell,
                height: 52,
                decoration: BoxDecoration(
                  color: AlmaPalette.button,
                  borderRadius: BorderRadius.circular(26),
                  border: Border.all(
                      color: AlmaPalette.gold.withValues(alpha: 0.55)),
                ),
              ),
            ),
            Row(children: [
              for (final (index, label) in labels.indexed)
                Expanded(
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                      child: Text(
                        label,
                        maxLines: 2,
                        textAlign: TextAlign.center,
                        style: AlmaType.meta.copyWith(
                          fontSize: 12,
                          height: 1.15,
                          color: index == selected
                              ? AlmaPalette.inkLight
                              : AlmaPalette.muted2,
                        ),
                      ),
                    ),
                  ),
                ),
            ]),
          ]),
        ),
      );
    });
  }
}

class _HourRow extends StatelessWidget {
  const _HourRow(
      {required this.label, required this.hour, required this.onChange});

  final String label;
  final int hour;
  final ValueChanged<int> onChange;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 15),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(children: [
        Expanded(child: Text(label, style: AlmaType.meta)),
        Text('${hour.toString().padLeft(2, '0')}:00',
            style: AlmaType.numeral.copyWith(fontSize: 18)),
        const SizedBox(width: 8),
        Column(mainAxisSize: MainAxisSize.min, children: [
          // Никогда ночью: восемь утра и девять вечера — границы, за которые
          // шаг не выпускает. Тот же договор, что печатает строка тихих часов.
          _Step(glyph: '⌃', onTap: hour < 21 ? () => onChange(hour + 1) : null),
          _Step(glyph: '⌄', onTap: hour > 8 ? () => onChange(hour - 1) : null),
        ]),
      ]),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.glyph, this.onTap});

  final String glyph;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkResponse(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        child: Text(
          glyph,
          style: TextStyle(
            fontSize: 13,
            color: onTap == null
                ? AlmaPalette.muted3.withValues(alpha: 0.4)
                : AlmaPalette.gold,
          ),
        ),
      ),
    );
  }
}

/// Обведённая кнопка — «Войти». Тот же вид, что на нативном экране: золотой
/// контур на ночи, без заливки.
class _OutlineButton extends StatelessWidget {
  const _OutlineButton({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(28),
      // Без `alignment`: Container с выравниванием раздувается до максимума
      // доступной ширины, и кнопка растягивалась во весь экран, хотя на нативе
      // она по содержимому. Размер задаёт padding.
      child: Container(
        height: 54,
        padding: const EdgeInsets.symmetric(horizontal: 34),
        decoration: BoxDecoration(
          border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.55)),
          borderRadius: BorderRadius.circular(28),
        ),
        child: Center(
          widthFactor: 1,
          child: Text(label,
              style: AlmaType.button.copyWith(color: AlmaPalette.goldBright)),
        ),
      ),
    );
  }
}

/// Эндоним — имя языка на нём самом, и оно не переводится никогда.
String _endonym(String code) => switch (code) {
      'en' => 'English',
      'es' => 'Español',
      'de' => 'Deutsch',
      'it' => 'Italiano',
      'fr' => 'Français',
      'pt-BR' => 'Português',
      'ru' => 'Русский',
      _ => code,
    };


/// Где выгрузка данных.
sealed class _Export {
  const _Export();
  static const idle = _ExportIdle();
  static const working = _ExportWorking();
  static const failed = _ExportFailed();
  const factory _Export.ready(String path) = _ExportReady;
}

class _ExportIdle extends _Export { const _ExportIdle(); }
class _ExportWorking extends _Export { const _ExportWorking(); }
class _ExportFailed extends _Export { const _ExportFailed(); }
class _ExportReady extends _Export {
  const _ExportReady(this.path);
  final String path;
}

/// Где удаление аккаунта.
enum _Delete { idle, confirming, mismatch, working, failed, done }

/// Где отмена подписки.
///
/// Запечатанным типом, а не тремя флажками: у `isCancelling`/`cancelFailed`/
/// `cancelled` восемь сочетаний, шесть из которых бессмыслица вроде «идёт и уже
/// не получилось». Ровно тот же довод записан в `AccountModel.swift`, где эта
/// машина состояний живёт на нативе.
sealed class _Cancel {
  const _Cancel();
  static const idle = _CancelIdle();
  static const confirming = _CancelConfirming();
  static const working = _CancelWorking();
  static const failed = _CancelFailed();
  static const atStore = _CancelAtStore();

  /// Остановлено. Внутри — дата, до которой план остаётся открытым; `null`
  /// значит, что сервер её не назвал, и тогда экран о ней не говорит.
  const factory _Cancel.done(String? until) = _CancelDone;
}

class _CancelIdle extends _Cancel { const _CancelIdle(); }
class _CancelConfirming extends _Cancel { const _CancelConfirming(); }
class _CancelWorking extends _Cancel { const _CancelWorking(); }
class _CancelFailed extends _Cancel { const _CancelFailed(); }
class _CancelAtStore extends _Cancel { const _CancelAtStore(); }
class _CancelDone extends _Cancel {
  const _CancelDone(this.until);
  final String? until;
}


/// Восстановление покупок в настройках: кнопка и то, чем магазин ответил.
class _RestoreRow extends StatefulWidget {
  const _RestoreRow({required this.store, required this.onRestored});

  final AlmaStore store;

  /// Перечитать права. Восстановление меняет то, что написано выше в разделе,
  /// и без этого «Всё, что ты покупал, снова открыто» стояло над словом «Free».
  final VoidCallback onRestored;

  @override
  State<_RestoreRow> createState() => _RestoreRowState();
}

class _RestoreRowState extends State<_RestoreRow> {
  StoreMessage? _seen;

  @override
  void initState() {
    super.initState();
    widget.store.addListener(_changed);
  }

  @override
  void dispose() {
    widget.store.removeListener(_changed);
    super.dispose();
  }

  void _changed() {
    if (!mounted) return;
    final message = widget.store.notice?.message;
    // Только на переходе, а не на каждом уведомлении слушателя: иначе один
    // ответ магазина заказывал бы запрос прав по кругу.
    if (message != _seen &&
        (message == StoreMessage.restored || message == StoreMessage.unlocked)) {
      widget.onRestored();
    }
    setState(() => _seen = message);
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final store = widget.store;
    final notice = store.notice;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AlmaButton(
          kind: AlmaButtonKind.veil,
          fills: false,
          label: store.restoring ? l.storeRestoring : l.paywallRestore,
          onTap: store.restoring || store.busy != null
              ? null
              : () {
                  store.attach(SessionScope.of(context));
                  store.restore();
                },
        ),
        if (notice != null)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(
              switch (notice.message) {
                StoreMessage.storeSilent => l.storeUnavailable,
                StoreMessage.pending => l.paywallPending,
                StoreMessage.offline => l.paywallOffline,
                StoreMessage.notVerified => l.paywallNotVerified,
                StoreMessage.verifyLater => l.paywallVerifyLater,
                StoreMessage.withdrawn => l.paywallWithdrawn,
                StoreMessage.unlocked => l.paywallRestored,
                StoreMessage.restoring => l.storeRestoring,
                StoreMessage.restored => l.paywallRestored,
                StoreMessage.restoredNone => l.storeRestoredNone,
              },
              style: AlmaType.meta.copyWith(
                color: switch (notice.tone) {
                  StoreTone.good => AlmaPalette.agree,
                  StoreTone.waiting => AlmaPalette.gold,
                  StoreTone.bad => AlmaPalette.disagree,
                },
              ),
            ),
          ),
      ],
    );
  }
}
