import 'dart:async';

import 'package:flutter/material.dart';

import '../../design/brand_marks.dart';
import '../../design/buttons.dart';
import '../../design/close_button.dart';
import '../../design/emblem.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/providers_sign_in.dart';
import '../../state/session.dart';
import 'sign_in_code_screen.dart';

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

  /// Какие двери этот сервер умеет открывать. Оба `false`, пока он не ответил:
  /// кнопка, мигнувшая и исчезнувшая, хуже кнопки, появившейся на полсекунды
  /// позже.
  bool _apple = false;
  bool _google = false;

  /// Какой провайдер сейчас спрашивает у системы — `'apple'`, `'google'` или
  /// `null`. Гасит **обе** кнопки: два системных окна разом не открываются, и
  /// второе нажатие в ожидании первого — это заявка, которую некому принять.
  String? _provider;

  bool _asked = false;

  @override
  void initState() {
    super.initState();
    _email.addListener(_refresh);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // `SessionScope` из `initState` недоступен — ловушка, записанная в
    // `docs/WORKING.md`: исключение уходит в невозвращённое будущее, и экран
    // молча стоит вечно.
    if (_asked) return;
    _asked = true;
    unawaited(_askProviders());
  }

  /// Спросить сервер, что он умеет. Молчание — не «умеет всё».
  ///
  /// Отказ сети оставляет обе кнопки скрытыми и **не показывает ошибку**:
  /// человек пришёл сюда войти по почте, поле для почты на месте, и красная
  /// строка про недоступные провайдеры сообщила бы о поломке там, где её нет.
  Future<void> _askProviders() async {
    try {
      final can = await SessionScope.of(context).client.authProviders();
      if (!mounted) return;
      setState(() {
        _apple = (can['apple'] ?? false) && AlmaProviders.appleShows;
        _google = can['google'] ?? false;
      });
    } catch (_) {
      // Тишина намеренная — см. выше.
    }
  }

  /// Войти через провайдера. `null` от обвязки — человек передумал.
  Future<void> _viaProvider(String which) async {
    if (_provider != null) return;
    setState(() {
      _provider = which;
      _notice = null;
    });
    final l = L.of(context);
    final session = SessionScope.of(context);
    final navigator = Navigator.of(context);
    try {
      final info = which == 'apple'
          ? await AlmaProviders.apple(session.client)
          : await AlmaProviders.google(session.client);
      if (!mounted) return;
      if (info == null) {
        setState(() => _provider = null);
        return;
      }
      // Токен уже в связке — его положил туда сам клиент. Осталось
      // перечитать аккаунт целиком: до этой секунды экран под нами показывал
      // гостя, а теперь там другой человек. Та же строка, что у входа по
      // ссылке, и по той же причине.
      await session.start(force: true);
      if (!mounted) return;
      navigator.maybePop();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _provider = null;
        _noticeBad = true;
        // Особой ветки про скрытую почту Apple больше нет: с 27.08.2026
        // релейный адрес принят, сервер ключует вход стабильным `sub`.
        _notice = error is ServerRefused && error.message.isNotEmpty
            ? error.message
            : l.scrSignInFailed;
      });
    }
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
        // **Типизированные отказы — своими словами, на языке экрана.** Сервер
        // говорит по-английски («this code is not valid»), и на русском экране
        // это читалось протечкой (владелец, 24 авг). Код отказа known — берём
        // локализованную фразу; незнакомый — серверная как запасная.
        _notice = switch (error) {
          ServerRefused(code: 'link_invalid') => l.scrSignInCodeInvalid,
          ServerRefused(code: 'link_used') => l.scrSignInCodeUsed,
          ServerRefused(code: 'link_expired') => l.scrSignInCodeExpired,
          ServerRefused(code: 'magic_link_rate_limit') => l.scrSignInTooMany,
          ServerRefused(:final message) when message.isNotEmpty => message,
          _ => l.scrSignInFailed,
        };
        _noticeBad = true;
      });
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _sendLink() async {
    final l = L.of(context);
    final session = SessionScope.of(context);
    final navigator = Navigator.of(context);
    await _run(
      () async {
        final sent = await session.client
            .requestMagicLink(_email.text.trim(), locale: session.locale);
        if (!mounted) return;
        setState(() => _debugToken = sent.debugToken);
        // Письмо ушло — человека красиво уводит на экран шести ячеек
        // (владелец, 25.08.2026). Вернулся с «true» — вход случился, и этот
        // экран закрывает себя сам.
        //
        // Поле почты отпускает фокус до ухода — в обе стороны. Экран под
        // экраном кода помнит, кто был в фокусе, и вернул бы клавиатуру полю
        // ровно в ту секунду, когда сам закрывается; клавиатура без поля и
        // есть «после входа зависает клавиатура» (владелец, 26.08.2026).
        FocusManager.instance.primaryFocus?.unfocus();
        final entered = await navigator.push<bool>(
          MaterialPageRoute(
            builder: (_) => SignInCodeScreen(email: _email.text.trim()),
          ),
        );
        if (entered == true && mounted) {
          FocusManager.instance.primaryFocus?.unfocus();
          navigator.maybePop();
        }
      },
      done: l.scrSignInCodeSent,
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
      // **Тело не сжимается под клавиатуру.** Иначе подпись про адрес,
      // прижатая к низу, ехала вверх вместе с клавиатурой и вставала над
      // полем — владелец: «пусть остаётся внизу, за клавой» (24 авг). Список
      // получает отступ в высоту клавиатуры сам, ниже.
      resizeToAvoidBottomInset: false,
      body: NightSky(
        mood: SkyMood.ceremony,
        seed: 0x5349474E,
        child: SafeArea(
          child: Stack(children: [
            ListView(
              padding: EdgeInsets.fromLTRB(
                  AlmaMetrics.pad,
                  8,
                  AlmaMetrics.pad,
                  32 + MediaQuery.viewInsetsOf(context).bottom),
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
                if (_apple || _google) ...[
                  const SizedBox(height: 26),
                  Text(l.scrSignInOrWith,
                      textAlign: TextAlign.center,
                      style: AlmaType.meta.copyWith(
                          fontSize: 12,
                          color: AlmaPalette.body.withValues(alpha: 0.5))),
                  const SizedBox(height: 14),
                  _Providers(
                    apple: _apple,
                    google: _google,
                    busy: _provider,
                    onTap: _viaProvider,
                  ),
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
            // Единое закрытие поверх-экранов: крестик справа (см. AlmaClose).
            Positioned(
              right: 8,
              top: 4,
              child: AlmaClose(onTap: () => Navigator.of(context).maybePop()),
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
  const _Providers({
    required this.apple,
    required this.google,
    required this.busy,
    required this.onTap,
  });

  final bool apple;
  final bool google;

  /// Какой провайдер сейчас разговаривает с системой, или `null`.
  final String? busy;
  final void Function(String which) onTap;

  @override
  Widget build(BuildContext context) {
    final buttons = <Widget>[
      // **Порядок не алфавитный.** Apple первым там, где он есть: на iOS это
      // вход, который система показывает своим листом и который Apple требует
      // предлагать наравне с чужими провайдерами (Guideline 4.8).
      if (apple)
        _Provider(
          label: 'Apple',
          working: busy == 'apple',
          onTap: busy == null ? () => onTap('apple') : null,
        ),
      if (google)
        _Provider(
          label: 'Google',
          working: busy == 'google',
          onTap: busy == null ? () => onTap('google') : null,
        ),
    ];
    // Одна доступная дверь занимает строку целиком, а не половину с дырой
    // рядом: на Android Apple не показывается вовсе, и ряд из одной кнопки в
    // пол-экрана читался бы как «вторая не загрузилась».
    return Row(
      children: [
        for (final (index, button) in buttons.indexed) ...[
          if (index > 0) const SizedBox(width: 12),
          Expanded(child: button),
        ],
      ],
    );
  }
}

class _Provider extends StatelessWidget {
  const _Provider({required this.label, required this.working, this.onTap});

  final String label;
  final bool working;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          height: 54,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: const Color(0xFF0C0E18),
            borderRadius: BorderRadius.circular(27),
            border: Border.all(color: const Color(0x24EDE7DA)),
          ),
          // Ожидание — на самой кнопке, а не поверх экрана: системный лист
          // Apple или окно выбора аккаунта Google приходит не мгновенно, и
          // кнопка, ничем не ответившая на нажатие, получает второе.
          child: working
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: AlmaPalette.gold),
                )
              // **Марка и подпись, а не одна подпись.** Так собраны кнопки
              // входа во всяком приложении, которое их показывает, и не из
              // моды: знак узнаётся раньше, чем прочитано слово, а на двух
              // кнопках рядом именно это и решает, куда нажать.
              //
              // Марка не гаснет вместе с подписью, когда кнопка занята: серое
              // яблоко и серая «G» — это чужие знаки, перекрашенные нами, чего
              // обе компании не разрешают. Гаснет слово, знак остаётся собой.
              : Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    label == 'Apple'
                        ? BrandMark.apple()
                        : BrandMark.google(),
                    const SizedBox(width: 9),
                    Flexible(
                      child: Text(label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: AlmaType.button.copyWith(
                              fontSize: 15,
                              color: onTap == null
                                  ? AlmaPalette.muted3
                                  : AlmaPalette.inkLight)),
                    ),
                  ],
                ),
        ),
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
