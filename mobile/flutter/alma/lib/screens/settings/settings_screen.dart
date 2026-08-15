import 'dart:io';
import 'dart:convert';
import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../design/buttons.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../state/session.dart';
import '../../billing/alma_store.dart';
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
  bool _started = false;

  /// Где сейчас выгрузка данных: ничего / собираю / готово / не собралась.
  _Export _export = _Export.idle;

  /// Где сейчас удаление аккаунта. Двухшаговое намеренно: маршрут уничтожает
  /// оплаченные чтения, которые нельзя переписать слово в слово.
  _Delete _delete = _Delete.idle;
  final _confirm = TextEditingController();

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

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      final client = SessionScope.of(context).client;
      client.dailySettings().then((d) {
        if (mounted) setState(() => _daily = d);
      }).catchError((Object _) {});
      client.entitlements().then((e) {
        if (mounted) setState(() => _plan = e);
      }).catchError((Object _) {});
    }
  }


  /// Что стоит под строкой выгрузки.
  List<Widget> _exportState(L l) => switch (_export) {
        _ExportIdle() => [_note(l.cabExportNote)],
        _ExportWorking() => [_note(l.cabPlanExporting)],
        _ExportFailed() => [_note(l.cabPlanExportFailed)],
        final _ExportReady ready => [
            _note(l.cabExportReady),
            Padding(
              padding: const EdgeInsets.only(top: 10, bottom: 6),
              child: AlmaButton(
                kind: AlmaButtonKind.outline,
                fills: false,
                label: l.cabSaveFile,
                // Файл уже существует к этому моменту — поэтому лист
                // «поделиться» открывается мгновенно, а не ждёт сети. Лист,
                // которому надо дождаться запроса, открывается пустым.
                onTap: () => Share.shareXFiles([XFile(ready.path)]),
              ),
            ),
          ],
      };

  /// Что стоит под строкой удаления. Подтверждение набором — не «вы уверены?»:
  /// одно нажатие мимо не должно уничтожать оплаченные чтения.
  List<Widget> _deleteState(L l, AlmaSession session) {
    final confirmation = _confirmationOf(session);
    final guest = confirmation != null && !confirmation.contains('@');
    switch (_delete) {
      case _Delete.idle:
        return const [];
      case _Delete.working:
        return [_note(l.stateLoadingShort)];
      case _Delete.failed:
        return [_note(l.cabPlanDeleteFailed)];
      case _Delete.done:
        return [_note(l.stateAccountDeleted)];
      case _Delete.confirming:
      case _Delete.mismatch:
        return [
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(l.cabPlanDeleteWarning, style: AlmaType.meta),
                const SizedBox(height: 14),
                Text(
                  guest
                      ? l.cabSettingsDeleteGuestNote
                      : l.cabSettingsDeleteConfirm,
                  style: AlmaType.meta,
                ),
                if (guest) ...[
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
                    style: AlmaType.body.copyWith(fontSize: 16),
                    decoration: const InputDecoration(border: InputBorder.none),
                    onChanged: (_) => setState(() {}),
                  ),
                ),
                if (_delete == _Delete.mismatch) ...[
                  const SizedBox(height: 8),
                  Text(l.cabPlanDeleteMismatch,
                      style: AlmaType.meta
                          .copyWith(color: AlmaPalette.disagree)),
                ],
                const SizedBox(height: 14),
                Row(children: [
                  AlmaButton(
                    kind: AlmaButtonKind.danger,
                    fills: false,
                    label: l.cabPlanDeleteForever,
                    // Кнопка гаснет, пока набранное не совпало: отказ после
                    // нажатия — это отказ, которого можно было не допускать.
                    onTap: _typedMatches(confirmation)
                        ? () => _confirmDelete(session)
                        : null,
                  ),
                  const SizedBox(width: 12),
                  AlmaButton(
                    kind: AlmaButtonKind.veil,
                    fills: false,
                    label: l.cabinetBack,
                    onTap: () => setState(() {
                      _confirm.clear();
                      _delete = _Delete.idle;
                    }),
                  ),
                ]),
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
            account?.displayName?.isNotEmpty == true
                ? account!.displayName!
                : l.cabGuest,
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
          // Строка-действие, а не переключатель: язык живёт в настройках
          // телефона, и приложение отправляет туда, а не заводит вторую ручку.
          _Row(
            label: _endonym(session.locale),
            value: l.cabSettingsInterfaceLanguageAction,
            arrow: true,
            onTap: () => launchUrl(Uri.parse('app-settings:'),
                mode: LaunchMode.externalApplication),
          ),
        ]),
        ..._planSection(l),
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
            onTap: _export == _Export.working ? null : _exportEverything,
          ),
          ..._exportState(l),
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
          // **Документы открываются внутри приложения.**
          //
          // Здесь стоял `launchUrl` на `$_site/…`, то есть на `alma.pazl.ai`,
          // которого не существует: пять строк открывали браузер с ошибкой.
          // Присутствующая и мёртвая ссылка хуже отсутствующей — она читается
          // как попытка закрыть чек-лист. Текст лежит в бинарнике и не
          // нуждается в сети совсем.
          for (final document in LegalDocument.values)
            _Row(
              label: LegalScreen.title(l, document),
              value: '',
              arrow: true,
              onTap: () => Navigator.of(context, rootNavigator: true).push(
                CupertinoPageRoute(
                    builder: (context) => LegalScreen(document: document)),
              ),
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
    if (daily == null) return const [];
    final mode = daily['daily'] as String? ?? 'off';
    final hour = (daily['hour'] as num?)?.toInt() ?? 10;
    final zone = daily['timezone'] as String?;
    final verified = (daily['verified_days'] as num?)?.toInt();

    return [
      _Section(label: l.dailySettingTitle, children: [
        for (final (value, label) in [
          ('off', l.dailySettingOff),
          ('occasional', l.dailySettingOccasionally),
          ('important', l.dailySettingOnlyWhatMatters),
        ])
          _Row(
            label: label,
            value: '',
            checked: mode == value,
            onTap: () => _setDaily(daily: value),
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

  List<Widget> _planSection(L l) {
    final plan = _plan;
    if (plan == null) return const [];
    final rows = (plan['entitlements'] as List? ?? const [])
        .whereType<Map>()
        .map((e) => e.cast<String, dynamic>())
        .toList();
    return [
      _Section(label: l.cabSettingsPlan, children: [
        if (rows.isEmpty) ...[
          _Row(label: l.cabPlanFreePlan, value: ''),
          const SizedBox(height: 12),
          Text(l.cabPlanFreeNote, style: AlmaType.meta),
        ] else ...[
          for (final row in rows)
            _Row(
              label: row['system'] == 'all'
                  ? l.cabSettingsEverythingMonthly
                  : (row['system'] as String? ?? ''),
              value: row['expires_at'] is String
                  ? l.cabPlanRunsUntil(_civilDate(
                      l.localeName, (row['expires_at'] as String).split('T').first))
                  : '',
            ),
          // **Управление подпиской — у того, кто её продал.**
          //
          // Ни Apple, ни Google не позволяют серверу остановить подписку,
          // принадлежащую их аккаунту, и локальный флажок «отменено» не
          // останавливает списание. Поэтому здесь ссылка в магазин, а не
          // кнопка отмены: `POST /v1/billing/subscription/cancel` на такую
          // подписку отвечает 409 и ничего не пишет — правильно, — и кнопка
          // туда вела бы к фразе, показывающей обратно на эту же ссылку.
          if (rows.any(_isSubscription)) ...[
            const SizedBox(height: 14),
            AlmaButton(
              kind: AlmaButtonKind.outline,
              fills: false,
              label: l.cabManageInStore,
              onTap: () => launchUrl(
                Uri.parse('https://apps.apple.com/account/subscriptions'),
                mode: LaunchMode.externalApplication,
              ),
            ),
            const SizedBox(height: 10),
            Text(l.cabManagedByApple, style: AlmaType.meta),
          ],
        ],
        // **Восстановление — вне витрины.**
        //
        // Apple отклоняет приложение, которое продаёт разовые покупки и не
        // даёт их вернуть в месте, до которого можно дойти, не открывая
        // пейволл. И это же единственное, что помогает человеку с новым
        // телефоном, — случай, который действительно случается.
        const SizedBox(height: 18),
        _RestoreRow(store: AlmaStore.shared),
      ]),
    ];
  }

  /// Подписка ли это право. `one_time` — купленная навсегда дверь: её не
  /// отменяют и ею не управляют в магазине.
  static bool _isSubscription(Map<String, dynamic> row) =>
      const ['weekly', 'monthly', 'annual'].contains(row['kind']);

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


/// Восстановление покупок в настройках: кнопка и то, чем магазин ответил.
class _RestoreRow extends StatefulWidget {
  const _RestoreRow({required this.store});

  final AlmaStore store;

  @override
  State<_RestoreRow> createState() => _RestoreRowState();
}

class _RestoreRowState extends State<_RestoreRow> {
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
    if (mounted) setState(() {});
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
          label: store.restoring ? l.paywallRestoring : l.paywallRestore,
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
                StoreMessage.storeSilent => l.paywallStoreUnavailable,
                StoreMessage.pending => l.paywallPending,
                StoreMessage.offline => l.paywallOffline,
                StoreMessage.notVerified => l.paywallNotVerified,
                StoreMessage.verifyLater => l.paywallVerifyLater,
                StoreMessage.withdrawn => l.paywallWithdrawn,
                StoreMessage.unlocked => l.paywallRestored,
                StoreMessage.restoring => l.paywallRestoring,
                StoreMessage.restored => l.paywallRestored,
                StoreMessage.restoredNone => l.paywallRestoredNone,
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
