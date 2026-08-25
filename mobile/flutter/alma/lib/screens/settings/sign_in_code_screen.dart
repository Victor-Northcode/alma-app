import 'package:flutter/material.dart';
import 'package:flutter/services.dart'
    show
        FilteringTextInputFormatter,
        HapticFeedback,
        LengthLimitingTextInputFormatter;

import '../../design/close_button.dart';
import '../../design/emblem.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../state/session.dart';

/// Шесть ячеек кода — отдельный экран после «Отправить код».
///
/// Владелец (25.08.2026): «вводил не в строку, а в шесть ячеек, красиво, уже
/// на следующем экране». Ячейки — витрина; сам ввод живёт в невидимом поле
/// под ними: системная клавиатура, вставка из буфера и автоподстановка кода
/// из письма работают как с обычным полем, а не как с шестью.
///
/// Шестая цифра отправляет код сама: кнопка «Войти» здесь была бы вторым
/// нажатием ради того, что экран уже знает.
class SignInCodeScreen extends StatefulWidget {
  const SignInCodeScreen({super.key, required this.email});

  final String email;

  @override
  State<SignInCodeScreen> createState() => _SignInCodeScreenState();
}

class _SignInCodeScreenState extends State<SignInCodeScreen> {
  final _code = TextEditingController();
  final _focus = FocusNode();

  bool _working = false;
  String? _notice;
  bool _noticeBad = false;

  @override
  void initState() {
    super.initState();
    _code.addListener(_changed);
  }

  @override
  void dispose() {
    _code.removeListener(_changed);
    _code.dispose();
    _focus.dispose();
    super.dispose();
  }

  void _changed() {
    setState(() {});
    if (_code.text.length == 6 && !_working) _signIn();
  }

  Future<void> _signIn() async {
    final l = L.of(context);
    final session = SessionScope.of(context);
    final navigator = Navigator.of(context);
    setState(() {
      _working = true;
      _notice = null;
    });
    try {
      await session.client.consumeEmailCode(widget.email, _code.text.trim());
      await session.start(force: true);
      if (!mounted) return;
      HapticFeedback.selectionClick();
      // Возврат с ответом «вошли»: экран входа под нами закрывает и себя.
      navigator.pop(true);
    } on AlmaError catch (error) {
      if (!mounted) return;
      setState(() {
        _working = false;
        _noticeBad = true;
        _code.clear();
        _notice = switch (error) {
          ServerRefused(code: 'link_invalid') => l.scrSignInCodeInvalid,
          ServerRefused(code: 'link_used') => l.scrSignInCodeUsed,
          ServerRefused(code: 'link_expired') => l.scrSignInCodeExpired,
          ServerRefused(code: 'magic_link_rate_limit') => l.scrSignInTooMany,
          ServerRefused(:final message) when message.isNotEmpty => message,
          _ => l.scrSignInFailed,
        };
      });
      _focus.requestFocus();
    }
  }

  Future<void> _resend() async {
    final l = L.of(context);
    final session = SessionScope.of(context);
    setState(() => _notice = null);
    try {
      await session.client
          .requestMagicLink(widget.email, locale: session.locale);
      if (!mounted) return;
      setState(() {
        _noticeBad = false;
        _notice = l.scrSignInCodeSentAgain;
      });
    } on AlmaError catch (error) {
      if (!mounted) return;
      setState(() {
        _noticeBad = true;
        _notice = error is ServerRefused &&
                error.code == 'magic_link_rate_limit'
            ? l.scrSignInTooMany
            : l.scrSignInFailed;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final typed = _code.text;

    return Scaffold(
      backgroundColor: AlmaPalette.night,
      resizeToAvoidBottomInset: false,
      body: NightSky(
        mood: SkyMood.ceremony,
        seed: 0x434F4445,
        child: SafeArea(
          child: Stack(children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(
                  AlmaMetrics.pad, 8, AlmaMetrics.pad, 32),
              children: [
                const SizedBox(height: 44),
                const Center(child: AlmaEmblem(size: 108)),
                const SizedBox(height: 30),
                Text(l.scrSignInCodeTitle,
                    textAlign: TextAlign.center,
                    style: AlmaType.displayL.copyWith(fontSize: 28)),
                const SizedBox(height: 8),
                Text(
                  l.scrSignInCodeSentTo(widget.email),
                  textAlign: TextAlign.center,
                  style: AlmaType.meta
                      .copyWith(color: AlmaPalette.body.withValues(alpha: 0.6)),
                ),
                const SizedBox(height: 30),
                // Витрина из шести ячеек над невидимым полем: тап по любой
                // ячейке поднимает клавиатуру настоящего поля.
                GestureDetector(
                  onTap: _focus.requestFocus,
                  child: Stack(alignment: Alignment.center, children: [
                    Opacity(
                      opacity: 0,
                      child: SizedBox(
                        height: 1,
                        child: TextField(
                          controller: _code,
                          focusNode: _focus,
                          autofocus: true,
                          enabled: !_working,
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly,
                            LengthLimitingTextInputFormatter(6),
                          ],
                          // Код из письма подставляется системой одним тапом.
                          autofillHints: const [AutofillHints.oneTimeCode],
                        ),
                      ),
                    ),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        for (var i = 0; i < 6; i++) ...[
                          if (i > 0) SizedBox(width: i == 3 ? 18 : 8),
                          _Cell(
                            digit: i < typed.length ? typed[i] : null,
                            active: !_working &&
                                i == typed.length &&
                                _focus.hasFocus,
                          ),
                        ],
                      ],
                    ),
                  ]),
                ),
                const SizedBox(height: 26),
                if (_working)
                  const Center(
                    child: SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: AlmaPalette.gold),
                    ),
                  )
                else
                  Center(
                    child: TextButton(
                      onPressed: _resend,
                      child: Text(l.scrSignInSendLinkShort,
                          style:
                              AlmaType.meta.copyWith(color: AlmaPalette.gold)),
                    ),
                  ),
                const SizedBox(height: 14),
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

/// Одна ячейка кода. Активная (следующая к заполнению) держит золотой кант —
/// глаз видит, куда встанет цифра; заполненная — цифру на спокойной обводке.
class _Cell extends StatelessWidget {
  const _Cell({required this.digit, required this.active});

  final String? digit;
  final bool active;

  @override
  Widget build(BuildContext context) => AnimatedContainer(
        duration: const Duration(milliseconds: 120),
        width: 46,
        height: 58,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: AlmaPalette.night700.withValues(alpha: 0.55),
          borderRadius: BorderRadius.circular(13),
          border: Border.all(
            color: active
                ? AlmaPalette.gold
                : digit != null
                    ? AlmaPalette.gold.withValues(alpha: 0.45)
                    : AlmaPalette.hairline,
            width: active ? 1.4 : 1,
          ),
        ),
        child: Text(
          digit ?? '',
          style: AlmaType.numeral
              .copyWith(fontSize: 26, color: AlmaPalette.inkLight),
        ),
      );
}
