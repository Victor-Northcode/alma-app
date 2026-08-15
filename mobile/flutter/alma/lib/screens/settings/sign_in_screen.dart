import 'package:flutter/material.dart';

import '../../design/buttons.dart';
import '../../design/emblem.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../state/session.dart';

/// Вход в аккаунт.
///
/// Порт `mobile/ios/Alma/Screens/Settings/SignInScreen.swift` по макету `s44`.
/// Строки экрана были перенесены давно, а самого экрана в порте не было — то
/// есть человек, переставивший телефон, терял купленное и не имел способа
/// вернуть его.
///
/// **Порядок здесь перевёрнут относительно натива, и это решение дизайна.**
/// На нативе первыми стоят Apple и Google, почта — под ними, «или по почте».
/// В макете наоборот: поле почты и золотая кнопка сверху, Apple и Google под
/// связкой «или войди через». Почта — единственный способ входа, который
/// работает на любом устройстве и не требует чужого аккаунта; кнопка, которая
/// работает у всех, и должна быть главной.
///
/// Пароля нет и не будет: сервер знает только одноразовые ссылки и провайдеров.
class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key});

  /// Кнопки Apple и Google **за флагом**.
  ///
  /// Обе требуют нативной обвязки, которой в порте пока нет: Google — своего
  /// клиента и `URL scheme`, Apple — заявки в возможностях цели. Кнопка,
  /// нарисованная поверх отсутствующей обвязки, отвечала бы ошибкой на каждое
  /// нажатие, а это хуже её отсутствия: неработающая кнопка входа читается как
  /// «аккаунт сломан». Ссылка на почту работает по-настоящему.
  static bool get providersReady =>
      const String.fromEnvironment('ALMA_SIGNIN_PROVIDERS') == '1';

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final _email = TextEditingController();
  final _token = TextEditingController();

  bool _working = false;
  String? _notice;
  bool _noticeBad = false;

  /// Токен из ответа сервера, когда почтовик не настроен. Только для разработки
  /// — в продакшне сервер его не присылает вовсе, и блок не появляется.
  String? _debugToken;

  @override
  void initState() {
    super.initState();
    _email.addListener(_refresh);
  }

  @override
  void dispose() {
    _email.removeListener(_refresh);
    _email.dispose();
    _token.dispose();
    super.dispose();
  }

  void _refresh() => setState(() {});

  /// Адрес похож на адрес. **Проверка нарочно снисходительная**, как на нативе:
  /// поле, отвергающее верный адрес, хуже поля, пропускающего опечатку. Опечатка
  /// даёт письмо, которое не пришло, — это человек видит; отказ даёт кнопку,
  /// которая не нажимается, и никакого объяснения.
  bool get _emailLooksReal {
    final value = _email.text.trim();
    final at = value.indexOf('@');
    if (at < 1) return false;
    final domain = value.substring(at + 1);
    return domain.contains('.') &&
        !domain.endsWith('.') &&
        !domain.contains('@');
  }

  Future<void> _run(
    Future<void> Function() work, {
    required String done,
  }) async {
    if (_working) return;
    setState(() {
      _working = true;
      _notice = null;
    });
    final l = L.of(context);
    try {
      await work();
      if (!mounted) return;
      setState(() {
        _notice = done;
        _noticeBad = false;
      });
    } on AlmaError catch (error) {
      if (!mounted) return;
      setState(() {
        // Сервер объясняет отказ на языке аккаунта — эту фразу и показываем.
        // Своя общая строка только там, где у него объяснения не нашлось.
        _notice = error is ServerRefused && error.message.isNotEmpty
            ? error.message
            : l.scrSignInFailed;
        _noticeBad = true;
      });
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _sendLink() async {
    final l = L.of(context);
    final session = SessionScope.of(context);
    await _run(
      () async {
        final sent = await session.client
            .requestMagicLink(_email.text.trim(), locale: session.locale);
        if (mounted) setState(() => _debugToken = sent.debugToken);
      },
      done: l.scrSignInLinkSent,
    );
  }

  Future<void> _consume(String token) async {
    final l = L.of(context);
    final session = SessionScope.of(context);
    await _run(
      () async {
        await session.client.consumeMagicLink(token);
        // Аккаунт сменился — всё, что экран под нами показывает, теперь
        // принадлежит другому человеку. Перечитываем целиком.
        await session.start(force: true);
        if (mounted) setState(() => _debugToken = null);
      },
      done: l.scrSignInDone,
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final session = SessionScope.of(context);
    final signedIn = session.account?.isGuest == false;

    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: NightSky(
        mood: SkyMood.ceremony,
        seed: 0x5349474E,
        child: SafeArea(
          child: Stack(children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(
                  AlmaMetrics.pad, 8, AlmaMetrics.pad, 32),
              children: [
                const SizedBox(height: 44),
                const Center(child: AlmaEmblem(size: 126)),
                const SizedBox(height: 34),
                Text(l.scrSignInTitle,
                    textAlign: TextAlign.center,
                    style: AlmaType.displayL.copyWith(fontSize: 30)),
                const SizedBox(height: 8),
                Text(
                  signedIn ? l.scrSignInAlready : l.scrSignInLead,
                  textAlign: TextAlign.center,
                  style: AlmaType.meta
                      .copyWith(color: AlmaPalette.body.withValues(alpha: 0.6)),
                ),
                const SizedBox(height: 30),
                CeremonialField(
                  controller: _email,
                  hint: l.scrSignInEmailPlaceholder,
                  keyboardType: TextInputType.emailAddress,
                  onSubmitted: (_) => _emailLooksReal ? _sendLink() : null,
                ),
                const SizedBox(height: 12),
                AlmaButton(
                  label: _working ? l.scrSignInSending : l.scrSignInSendLink,
                  shortLabel: l.scrSignInSendLinkShort,
                  onTap: _emailLooksReal && !_working ? _sendLink : null,
                ),
                if (SignInScreen.providersReady) ...[
                  const SizedBox(height: 26),
                  Text(l.scrSignInOrWith,
                      textAlign: TextAlign.center,
                      style: AlmaType.meta.copyWith(
                          fontSize: 12,
                          color: AlmaPalette.body.withValues(alpha: 0.5))),
                  const SizedBox(height: 14),
                  const _Providers(),
                ],
                if (_debugToken != null) ...[
                  const SizedBox(height: 26),
                  _DebugConsume(
                    token: _token,
                    suggestion: _debugToken!,
                    onConsume: _consume,
                  ),
                ],
                const SizedBox(height: 26),
                if (_notice != null)
                  Text(
                    _notice!,
                    textAlign: TextAlign.center,
                    style: AlmaType.meta.copyWith(
                      color: _noticeBad
                          ? AlmaPalette.disagree
                          : AlmaPalette.goldBright,
                    ),
                  ),
              ],
            ),
            // Обещание про адрес — внизу и мелким, как весь мелкий шрифт
            // продукта. Оно длиннее макетного «No password, no newsletter»
            // намеренно: там сказано, чего мы **не** делаем, здесь — что делаем.
            Align(
              alignment: Alignment.bottomCenter,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(28, 0, 28, 4),
                child: Text(
                  l.scrSignInPrivacy,
                  textAlign: TextAlign.center,
                  style: AlmaType.meta.copyWith(
                      fontSize: 12.5,
                      color: AlmaPalette.body.withValues(alpha: 0.5)),
                ),
              ),
            ),
            Positioned(
              left: 0,
              top: 0,
              child: IconButton(
                onPressed: () => Navigator.of(context).maybePop(),
                icon: Text('←',
                    style: AlmaType.body
                        .copyWith(fontSize: 18, color: AlmaPalette.gold)),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

/// Apple и Google — две равные половины строки, 54 в высоту, как в макете.
///
/// **Подписи — литералы, и это не забытая локализация.** В макете на кнопках
/// стоят сами марки, а марки не переводятся ни на один из семи языков. Строка
/// `scrSignInGoogle` («Continue with Google») осталась от натива, где кнопка
/// одна на всю ширину; здесь их две по 169 точек, и полная фраза туда не
/// встаёт. Что это вход, говорит связка «или войди через» над ними.
class _Providers extends StatelessWidget {
  const _Providers();

  @override
  Widget build(BuildContext context) {
    return const Row(children: [
      Expanded(child: _Provider(label: 'Apple')),
      SizedBox(width: 12),
      Expanded(child: _Provider(label: 'Google')),
    ]);
  }
}

class _Provider extends StatelessWidget {
  const _Provider({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        height: 54,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: const Color(0xFF0C0E18),
          borderRadius: BorderRadius.circular(27),
          border: Border.all(color: const Color(0x24EDE7DA)),
        ),
        child: Text(label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AlmaType.button
                .copyWith(fontSize: 15, color: AlmaPalette.inkLight)),
      );
}

/// Ввод токена руками — только когда сервер его отдал, то есть только в
/// разработке. В продакшне `debug_token` не приходит и блока не существует.
class _DebugConsume extends StatelessWidget {
  const _DebugConsume({
    required this.token,
    required this.suggestion,
    required this.onConsume,
  });

  final TextEditingController token;
  final String suggestion;
  final Future<void> Function(String) onConsume;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('debug: почтовик не настроен, токен ниже',
          style: AlmaType.meta.copyWith(color: AlmaPalette.gold)),
      const SizedBox(height: 8),
      CeremonialField(controller: token, hint: suggestion),
      const SizedBox(height: 10),
      AlmaButton(
        label: 'Войти этим токеном',
        kind: AlmaButtonKind.outline,
        onTap: () => onConsume(
            token.text.trim().isEmpty ? suggestion : token.text.trim()),
      ),
    ]);
  }
}
