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
  bool _threadLoaded = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // **Вкладка живёт с самого запуска, а сессия к тому моменту ещё грузится.**
    //
    // `IndexedStack` создаёт все четыре экрана сразу, поэтому первый вызов
    // приходит с пустым профилем: беседы у такого «человека» нет по
    // определению, и загрузка молча не делалась. `SessionScope` — это
    // `InheritedNotifier`, он позовёт сюда снова, когда данные придут, и вот
    // тогда есть чему грузиться. Свой флаг, потому что вступительные вопросы
    // и беседа готовы в разные моменты.
    final session = SessionScope.of(context);
    if (!_openersLoaded) {
      _openersLoaded = true;
      _loadOpeners();
    }
    if (!_threadLoaded && session.hasBirthData) {
      _threadLoaded = true;
      _loadLastThread();
    }
  }

  /// **Последняя беседа поднимается с сервера, а не начинается заново.**
  ///
  /// Реплики хранятся на сервере — `/v1/chat/threads` их отдаёт, и натив
  /// открывает вкладку на том, что человек уже спросил. Порт эти эндпоинты не
  /// звал вовсе: после перезапуска приложения вкладка Alma каждый раз
  /// встречала вступлением, будто разговора не было, а ответы, за которые
  /// заплачено, оставались лежать на сервере невидимыми. Сверено кадрами:
  /// натив показывал переписку, порт — «Спроси меня о чём угодно».
  Future<void> _loadLastThread() async {
    final session = SessionScope.of(context);
    if (!session.hasBirthData) return;
    try {
      final threads = await session.client.threads();
      if (threads.isEmpty) return;
      final turns = await session.client.thread(threads.first.id);
      if (!mounted || turns.isEmpty) return;
      setState(() {
        _threadId = threads.first.id;
        _turns
          ..clear()
          ..addAll(turns.map((t) => _Turn(
                mine: t.mine,
                body: t.body,
                citedFactors: t.citedFactors,
              )));
      });
      _scrollDown();
    } on AlmaError {
      // Молча: беседа — не то, ради чего экран обязан ругаться. Вступление
      // остаётся на месте, вопрос можно задать заново.
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
            Text(turn.body, style: AlmaType.voice),
            if (turn.citedFactors.isNotEmpty) ...[
              const SizedBox(height: 12),
              // Цитата под ответом — обещание продукта, и она **одна строка**:
              // подпись, первая позиция засечным золотом, «+N» о том, сколько
              // ещё, и знак раскрытия справа. Первый порт вываливал все
              // факторы переносом на три строки — цитата весила больше ответа.
              _Citation(factors: turn.citedFactors),
            ],
          ]),
        );
      },
    );
  }

  Widget _composer(L l) {
    return Container(
      padding: const EdgeInsets.fromLTRB(AlmaMetrics.pad, 12, AlmaMetrics.pad, 10),
      // Волосяная линия отделяет композер от ленты, как на нативе: без неё
      // поле ввода висит в тексте, а не стоит на своей полке.
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(children: [
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            height: 52,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              border: Border.all(color: AlmaPalette.hairline),
              borderRadius: BorderRadius.circular(26),
            ),
            child: TextField(
              controller: _draft,
              style: AlmaType.body.copyWith(fontSize: 16),
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
        // Круг обведённый, а не залитый золотом: на нативе отправка — тихая
        // кнопка рядом с полем, а золотая заливка принадлежит дверям покупки.
        InkResponse(
          onTap: () => _send(_draft.text),
          child: Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: AlmaPalette.hairline),
            ),
            child: Center(
              child: Text('→',
                  style: TextStyle(
                      color: AlmaPalette.body.withValues(alpha: 0.85),
                      fontSize: 19)),
            ),
          ),
        ),
      ]),
    );
  }
}

/// Цитата под ответом: подпись, первая позиция и сколько ещё.
///
/// Раскрывается нажатием на «+» — тогда показываются все позиции, из которых
/// прочитан ответ. Свёрнутая по умолчанию, потому что ответ читают, а цитату
/// проверяют: она обязана быть на виду и не обязана занимать треть экрана.
/// Первый порт вываливал все факторы переносом на три строки, и цитата весила
/// больше самого ответа — найдено сравнением с нативным кадром.
class _Citation extends StatefulWidget {
  const _Citation({required this.factors});

  final List<String> factors;

  @override
  State<_Citation> createState() => _CitationState();
}

class _CitationState extends State<_Citation> {
  bool _open = false;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final rest = widget.factors.length - 1;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
        Text(l.cabReadFrom.toUpperCase(), style: AlmaType.overline),
        const SizedBox(width: 12),
        // **Позиция получает место, а не остаток от него.** `Flexible` рядом
        // со `Spacer` уступал: распорка забирала всю свободную ширину, и
        // «ascendant 12°03′ ♌» — строка, которая помещается целиком, —
        // печаталась как «ascendant …». На нативе цитата читается полностью;
        // она и есть обещание продукта, что ответ прочитан из карты.
        Expanded(
          child: Text(
            widget.factors.first,
            style: AlmaType.numeral.copyWith(
              color: AlmaPalette.gold,
              fontFamilyFallback: AlmaType.glyphFallback,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (rest > 0 && !_open) ...[
          const SizedBox(width: 8),
          Text('+$rest',
              style: AlmaType.numeral.copyWith(color: AlmaPalette.goldDeep)),
        ],
        if (rest > 0)
          InkResponse(
            onTap: () => setState(() => _open = !_open),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
              child: Text(_open ? '−' : '+',
                  style: AlmaType.numeral
                      .copyWith(color: AlmaPalette.gold, fontSize: 17)),
            ),
          ),
      ]),
      if (_open)
        for (final factor in widget.factors.skip(1))
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(factor,
                style: AlmaType.numeral.copyWith(
                  color: AlmaPalette.gold,
                  fontFamilyFallback: AlmaType.glyphFallback,
                )),
          ),
    ]);
  }
}
