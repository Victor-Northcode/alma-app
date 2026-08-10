import 'package:flutter/material.dart';

import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';

/// Беседа с Alma.
///
/// Порт `mobile/ios/Alma/Screens/Alma/AlmaScreen.swift`. Вступление собрано из
/// собственной карты человека — «Луна у меня — Дева. Что ей на самом деле
/// нужно?» — потому что чужой вопрос не приглашает, а свой уже наполовину
/// задан. Под каждым ответом стоит цитата позиций: это обещание продукта, и
/// экран без неё нарушал бы то, что сам продукт печатает о себе.
class AlmaScreen extends StatefulWidget {
  const AlmaScreen({super.key});

  @override
  State<AlmaScreen> createState() => _AlmaScreenState();
}

class _Turn {
  _Turn({required this.mine, required this.body, this.citedFactors = const []});
  final bool mine;
  final String body;
  final List<String> citedFactors;
}

class _AlmaScreenState extends State<AlmaScreen> {
  final _draft = TextEditingController();
  final _scroll = ScrollController();
  final List<_Turn> _turns = [];
  List<String> _openers = const [];
  String? _threadId;
  bool _sending = false;
  bool _openersLoaded = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_openersLoaded) {
      _openersLoaded = true;
      _loadOpeners();
    }
  }

  /// Вступительные вопросы — из натальной карты, с запасом из каталога, когда
  /// карта ещё не посчитана или в ней нет нужной точки.
  Future<void> _loadOpeners() async {
    final session = SessionScope.of(context);
    final l = L.of(context);
    final fallback = [l.scrChatPrompt1, l.scrChatPrompt2, l.scrChatPrompt3];
    if (!session.hasBirthData) {
      setState(() => _openers = fallback);
      return;
    }
    try {
      final natal = await session.client.compute(SystemSlug.natal);
      final data = natal.data;
      final questions = <String>[];
      if (data['moon_sign'] is String) {
        questions.add(l.scrChatPromptMoon(
            CabinetWordsMore.sign(l, data['moon_sign'] as String)));
      }
      if (data['sun_sign'] is String) {
        questions.add(l.scrChatPromptSun(
            CabinetWordsMore.sign(l, data['sun_sign'] as String)));
      }
      if (data['rising_sign'] is String) {
        questions.add(l.scrChatPromptRising(
            CabinetWordsMore.sign(l, data['rising_sign'] as String)));
      }
      for (final extra in fallback) {
        if (questions.length >= 3) break;
        questions.add(extra);
      }
      if (mounted) setState(() => _openers = questions.take(3).toList());
    } on AlmaError {
      if (mounted) setState(() => _openers = fallback);
    }
  }

  Future<void> _send(String text) async {
    final message = text.trim();
    if (message.isEmpty || _sending) return;
    final session = SessionScope.of(context);
    setState(() {
      _turns.add(_Turn(mine: true, body: message));
      _sending = true;
      _draft.clear();
    });
    _scrollDown();
    try {
      final reply = await session.client.ask(
        message,
        threadId: _threadId,
        locale: session.locale,
      );
      if (!mounted) return;
      setState(() {
        _threadId = reply.threadId ?? _threadId;
        _turns.add(_Turn(
          mine: false,
          body: reply.paragraphs.join('\n\n'),
          citedFactors: reply.citedFactors,
        ));
      });
    } on AlmaError catch (error) {
      if (!mounted) return;
      final l = L.of(context);
      setState(() {
        _turns.add(_Turn(
          mine: false,
          body: error is ServerRefused && error.message.isNotEmpty
              ? error.message
              : l.stateUnavailable,
        ));
      });
    } finally {
      if (mounted) setState(() => _sending = false);
      _scrollDown();
    }
  }

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: AlmaMotion.ui,
          curve: AlmaMotion.uiCurve,
        );
      }
    });
  }

  @override
  void dispose() {
    _draft.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final session = SessionScope.of(context);
    final barHeight =
        AlmaMetrics.tabBarHeight + MediaQuery.paddingOf(context).bottom;
    final keyboard = MediaQuery.viewInsetsOf(context).bottom;

    return NightSky(
      mood: SkyMood.reading,
      seed: 0x414C4D43,
      child: SafeArea(
        bottom: false,
        child: Padding(
          // Над клавиатурой, когда она есть; над баром, когда её нет.
          padding: EdgeInsets.only(
              bottom: keyboard > 0 ? keyboard + 8 : barHeight),
          child: Column(children: [
            Expanded(
              child: _turns.isEmpty
                  ? _opening(l, session)
                  : _transcript(l),
            ),
            _composer(l),
          ]),
        ),
      ),
    );
  }

  /// Вступление: присутствие, две фразы голосом и три вопроса из карты.
  Widget _opening(L l, AlmaSession session) {
    return ListView(
      controller: _scroll,
      padding: const EdgeInsets.symmetric(
          horizontal: AlmaMetrics.pad, vertical: AlmaMetrics.gapLarge),
      children: [
        Center(
          child: Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(colors: [
                AlmaPalette.starFill,
                AlmaPalette.gold.withValues(alpha: 0.5),
                AlmaPalette.gold.withValues(alpha: 0.0),
              ], stops: const [0.0, 0.45, 1.0]),
            ),
          ),
        ),
        const SizedBox(height: 18),
        Text(
          session.hasBirthData ? l.scrChatOpening : l.scrChatNoChart,
          style: AlmaType.voice,
        ),
        const SizedBox(height: 12),
        Text(l.scrChatRule, style: AlmaType.meta),
        if (session.hasBirthData && _openers.isNotEmpty) ...[
          const SizedBox(height: AlmaMetrics.gapLarge),
          Text(l.scrChatCouldAsk.toUpperCase(), style: AlmaType.overline),
          const SizedBox(height: 10),
          for (final prompt in _openers)
            InkWell(
              onTap: () => _send(prompt),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 14),
                decoration: BoxDecoration(
                  border:
                      Border(bottom: BorderSide(color: AlmaPalette.hairline)),
                ),
                child: Row(children: [
                  Expanded(
                    child: Text(prompt,
                        style: AlmaType.body
                            .copyWith(color: AlmaPalette.body.withValues(alpha: 0.9))),
                  ),
                  const Text('→',
                      style:
                          TextStyle(color: AlmaPalette.gold, fontSize: 15)),
                ]),
              ),
            ),
        ],
      ],
    );
  }

  /// Лента: мои реплики пилюлей справа, ответы Alma — засечным на всю ширину,
  /// с подписью «ALMA» и цитатой позиций под текстом.
  Widget _transcript(L l) {
    return ListView.builder(
      controller: _scroll,
      padding: const EdgeInsets.symmetric(
          horizontal: AlmaMetrics.pad, vertical: AlmaMetrics.gap),
      itemCount: _turns.length + (_sending ? 1 : 0),
      itemBuilder: (context, i) {
        if (i == _turns.length) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Text(l.cabReadingChart, style: AlmaType.meta),
          );
        }
        final turn = _turns[i];
        if (turn.mine) {
          return Align(
            alignment: Alignment.centerRight,
            child: Container(
              margin: const EdgeInsets.only(top: 14, left: 48),
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: AlmaPalette.veilStrong,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Text(turn.body, style: AlmaType.body),
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.only(top: 20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text('ALMA', style: AlmaType.overline),
              const SizedBox(width: 12),
              Expanded(
                child: Container(
                  height: 1,
                  decoration:
                      BoxDecoration(gradient: AlmaGradient.fadedRule),
                ),
              ),
            ]),
            const SizedBox(height: 10),
            Text(turn.body, style: AlmaType.voice.copyWith(fontSize: 19)),
            if (turn.citedFactors.isNotEmpty) ...[
              const SizedBox(height: 10),
              // Цитата под ответом — обещание продукта. На Android её не
              // было вовсе, и это стояло в списке расхождений отдельной
              // строкой; здесь она структурная часть ленты.
              Wrap(spacing: 8, runSpacing: 4, children: [
                Text('${l.cabReadFrom} ', style: AlmaType.meta),
                for (final factor in turn.citedFactors.take(4))
                  Text(factor,
                      style:
                          AlmaType.numeral.copyWith(color: AlmaPalette.gold)),
              ]),
            ],
          ]),
        );
      },
    );
  }

  Widget _composer(L l) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(AlmaMetrics.pad, 8, AlmaMetrics.pad, 10),
      child: Row(children: [
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              border: Border.all(color: AlmaPalette.hairlineGold),
              borderRadius: BorderRadius.circular(24),
            ),
            child: TextField(
              controller: _draft,
              style: AlmaType.body,
              decoration: InputDecoration(
                hintText: l.scrChatPlaceholder,
                hintStyle: AlmaType.meta,
                border: InputBorder.none,
              ),
              onSubmitted: _send,
              textInputAction: TextInputAction.send,
            ),
          ),
        ),
        const SizedBox(width: 10),
        InkResponse(
          onTap: () => _send(_draft.text),
          child: Container(
            width: 44,
            height: 44,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              gradient: AlmaGradient.goldButton,
            ),
            child: const Center(
              child: Text('→',
                  style: TextStyle(
                      color: AlmaPalette.inkOnGold,
                      fontSize: 18,
                      fontWeight: FontWeight.w600)),
            ),
          ),
        ),
      ]),
    );
  }
}
