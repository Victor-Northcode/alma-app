import 'package:flutter/material.dart';

import '../../design/alma_presence.dart';
import '../../design/arrival.dart';
import '../../design/layout.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/models.dart' show ChatTurnKind;
import '../cabinet_words.dart';

/// Одна реплика беседы — **одна на два экрана**.
///
/// Живая лента и переоткрытая беседа рисуют реплики этим виджетом, и это не
/// экономия строк. На нативе у экрана прошлой беседы была своя копия, и она
/// молча разошлась с лентой: одно и то же сообщение показывало «ответила не из
/// карты» в чате и не показывало в архиве. Одна вью — одно поведение.
class ChatTurnView extends StatefulWidget {
  const ChatTurnView({
    super.key,
    required this.mine,
    required this.body,
    this.citedFactors = const [],
    this.kind,
    this.arriving = false,
  });

  final bool mine;
  final String body;
  final List<String> citedFactors;

  /// Что это была за реплика — четыре вида таксономии, а не «ответ или нет».
  ///
  /// **Из-за отсутствия этого поля порт терял два вида из четырёх.** Заботливый
  /// ответ (`care`) и молчащая карта (`chart_silent`) рисовались как обычное
  /// чтение: у первого под словами «мне тяжело» вставала строка служебных
  /// пометок, у второй пропадала честная приписка о том, что ответ не из карты.
  /// Правила рисования взяты у нативов буква в букву — `ChatPieces.swift:85`
  /// и `ChatTurnKind.kt:67`.
  ///
  /// `null` — «звавший не сказал»; тогда вид выводится из цитат ровно так же,
  /// как его выводит [ChatTurnKind.of] на старом ответе без `turn_kind`.
  final ChatTurnKind? kind;

  /// Ответ пришёл только что и обязан осесть, а не появиться готовым.
  ///
  /// A3 + A4: сперва шапка и мета-строка «read from» — «она открыла карту,
  /// потом заговорила», — и только после этого строки оседают каскадом.
  /// Перечитанная беседа приходит с `false`: оседать заново тому, что человек
  /// уже читал, — тик, а не жизнь.
  final bool arriving;

  @override
  State<ChatTurnView> createState() => _ChatTurnViewState();
}

class _ChatTurnViewState extends State<ChatTurnView>
    with TickerProviderStateMixin {
  /// Вход шапки: свет 26, «alma», линейка и мета-строка «read from».
  ///
  /// **У источника есть свой вход, и речь начинается после него.** Шапка
  /// появлялась готовой — в том же кадре, что и первая строка ответа, — и
  /// обещание продукта «сперва источник, потом речь» держалось только со
  /// второй строки. 240 мс — из спеки, §4: «A3: мета-строка появляется
  /// 240 мс»; та же длительность у всего, что в этом продукте меняет
  /// состояние ([AlmaMotion.ui]).
  late final AnimationController _dawn = AnimationController(
    vsync: this,
    duration: AlmaMotion.ui,
  );

  late final CurvedAnimation _dawnEased =
      CurvedAnimation(parent: _dawn, curve: AlmaMotion.uiCurve);

  /// Часы каскада. Длительность — 70 мс на строку (§4), и считаются в них все
  /// ступени, включая тление первой строки и опережение ведущей: иначе длинный
  /// ответ проходил бы каскад быстрее короткого.
  late final AnimationController _settle = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: 70 * (_lines + _ahead + _ember)),
  );

  /// Линейка под «alma» дорисовывается последней: 34 % → 100 % за 420 мс.
  late final AnimationController _rule = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 420),
  );

  /// Опережение ведущей строки: пока первая проявилась, третья ещё тлеет.
  static const _ahead = 3;

  /// **Отставание первой строки на старте — то, чем держится «сперва
  /// источник».** Каскад начинался с нуля, а при нулевом отставании строка
  /// рисуется непрозрачной: пауза перед `_settle.forward()` откладывала только
  /// строки со второй, а первая вставала вместе с шапкой в одном кадре с ней.
  /// Две ступени — это A3 «первая строка тлеет», и по лестнице §2 они дают ей
  /// 0.22 (в спеке названо .18; разницу в четыре сотых альфы порт не заводит
  /// вторым числом).
  static const _ember = 2;

  /// Прогресс каскада **в строках**: строке надо знать, на сколько она отстала
  /// от ведущей.
  late final Animation<double> _cascade = _settle.drive(Tween(
    begin: -_ember.toDouble(),
    end: (_lines + _ahead).toDouble(),
  ));

  /// Грубая оценка числа строк — только чтобы назначить длительность. Точную
  /// разбивку делает [_SettlingParagraph] на своей ширине.
  int get _lines => (widget.body.length / 42).ceil().clamp(3, 40);

  bool get mine => widget.mine;
  String get body => widget.body;
  List<String> get citedFactors => widget.citedFactors;

  ChatTurnKind get kind =>
      widget.kind ?? ChatTurnKind.of(null, citedFactors: citedFactors);

  @override
  void initState() {
    super.initState();
    if (!widget.arriving) {
      _dawn.value = 1;
      _settle.value = 1;
      _rule.value = 1;
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      // Reduced motion: каскада нет, всё встаёт готовым.
      if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
        _dawn.value = 1;
        _settle.value = 1;
        _rule.value = 1;
        return;
      }
      // **Порядок и есть обещание.** Шапка с цитатой (240 мс) → строки
      // каскадом (70 мс на строку) → линейка (420 мс). Раньше здесь стояла
      // голая пауза `Future.delayed(240)`: она отмеряла те же 240 мс, но
      // откладывать ей было нечего — шапка всё это время уже стояла готовой.
      _dawn.forward().whenComplete(() {
        if (!mounted) return;
        _settle.forward().whenComplete(() {
          if (mounted) _rule.forward();
        });
      });
    });
  }

  @override
  void dispose() {
    _dawnEased.dispose();
    _dawn.dispose();
    _settle.dispose();
    _rule.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (mine) {
      // **Своя реплика тоже входит, а не возникает рывком.**
      //
      // Вход есть у каждой реплики на нативе, включая собственную:
      // `AlmaScreen.swift:196` вешает `.riseIn(0)` на весь `ForEach`
      // сообщений. Здесь пузырь появлялся в одном кадре готовым — единственное
      // место беседы, где ничего не оседает, и потому самое заметное: человек
      // отпускает кнопку, и его слова щёлкают на экран.
      //
      // Числа не свои: [RiseIn] — уже перенесённый `Arrival.swift` (проявление
      // 0→1 с подъёмом 16 точек кривой `arrive` за 0.55 с). Второго входа с
      // другими числами продукт не заводит — «одна кривая на всё, что
      // приходит».
      //
      // **Спека и натив здесь расходятся, и выбран натив.** `chat-spec.md` §4
      // отмеряет «пузырь оседает 240 мс», `Arrival.swift` — 0.55 с. Взято
      // второе: вход своей реплики ничем не отличается от входа любого другого
      // содержания, и заводить ему собственную длительность значит завести в
      // словаре движения второе «приходящее содержание». Число спеки живёт
      // рядом — те же 240 мс у наклона света и у входа шапки, — так что
      // разойтись им есть куда.
      //
      // Без оглядки на `arriving`: перечитанная беседа входит так же, одним
      // тихим проявлением, — ровно как на нативе, где `.riseIn(0)` стоит и на
      // поднятых с сервера сообщениях.
      return RiseIn(
        // Реплика человека — справа и в пузыре, и пузырь никогда не во всю
        // ширину: иначе он перестаёт читаться как чья-то отдельная фраза.
        child: Align(
          alignment: Alignment.centerRight,
          child: Container(
            margin: const EdgeInsets.only(top: 14, left: 48),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            constraints: const BoxConstraints(maxWidth: 300),
            decoration: BoxDecoration(
              color: AlmaPalette.veilStrong,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Text(body, style: AlmaType.body),
          ),
        ),
      );
    }
    final l = L.of(context);
    return Padding(
      padding: const EdgeInsets.only(top: 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // **A3: источник первым — и у источника есть свой вход.** Шапка со
        // светом 26 и мета-строка «read from» встают ДО текста — «она открыла
        // карту, потом заговорила». Раньше цитата стояла под ответом: человек
        // сперва читал слова, а потом узнавал, откуда они, — порядок обратный
        // обещанию продукта.
        //
        // Шапка и цитата проявляются **одним куском**: это одно высказывание —
        // «вот откуда я читаю», — и разъехавшись на два входа оно перестало бы
        // читаться как одно. Проявление, без подъёма: подъём на 16 точек — то,
        // чем в этот продукт приходит *содержание* ([RiseIn]), а шапка не
        // приходит, она зажигается.
        AnimatedBuilder(
          animation: _dawnEased,
          builder: (context, child) =>
              Opacity(opacity: _dawnEased.value, child: child),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const AlmaPresence(size: AlmaPresence.inHeader),
              const SizedBox(width: 10),
              Text(l.tabAlma.toUpperCase(), style: AlmaType.overline),
              const SizedBox(width: 12),
              Expanded(
                // Линейка дорисовывается последней, когда строки уже осели: это
                // подпись под сказанным, а не полоска загрузки.
                child: AnimatedBuilder(
                  animation: _rule,
                  builder: (context, child) => FractionallySizedBox(
                    alignment: Alignment.centerLeft,
                    widthFactor: 0.34 + 0.66 * _rule.value,
                    child: child,
                  ),
                  child: Container(
                    height: 1,
                    decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
                  ),
                ),
              ),
            ]),
            // **Цитата — там, где есть что цитировать, и только там, где это
            // утверждение.** `conversation` не утверждает ни о ком ничего:
            // приветствие, спасибо, вопрос «что ты умеешь». Позиции, которые
            // такой ответ случайно назвал, — украшение, и подписывать ими
            // «прочитано из» значит выдавать вежливость за чтение карты.
            // Правило нативов дословно: показывается всем видам, кроме беседы,
            // — заботливый ответ, назвавший позицию, утверждение всё-таки
            // сделал.
            if (kind.showsCitations && citedFactors.isNotEmpty) ...[
              const SizedBox(height: 10),
              Citation(factors: citedFactors),
            ],
          ]),
        ),
        // **Абзацы — отдельными строками, а не пустой строкой внутри одной.**
        //
        // Тело склеивалось через `\n\n`, и между абзацами вставала пустая
        // строка засечного кегля — почти тридцать точек, вдвое больше, чем на
        // макете, где абзацы идут через 10. Ответ из трёх абзацев из-за этого
        // распадался на три отдельных высказывания.
        // A4: строки оседают каскадом. Сквозная нумерация по всему ответу —
        // абзацы продолжают друг друга, а не начинают счёт заново. Разметка
        // считается **один раз**: анимация висит на каждой строке отдельно и
        // трогает только прозрачность и сдвиг.
        ...() {
          var line = 0;
          final blocks = <Widget>[];
          for (final paragraph in _paragraphs) {
            blocks.add(Padding(
              padding: const EdgeInsets.only(top: 10),
              child: _SettlingParagraph(
                text: paragraph,
                style: AlmaType.voice,
                progress: _cascade,
                startLine: line,
              ),
            ));
            line += (paragraph.length / 42).ceil().clamp(1, 40);
          }
          return blocks;
        }(),
        // **Честная приписка — фраза, а не бирка.** Только у `chart_silent`:
        // карту она прочла, и карте про это сказать нечего. Прежняя `НЕ ИЗ
        // ТВОЕЙ КАРТЫ» прописными читалась как предупреждение о соответствии,
        // приклеенное к чужому разговору, и вставала в том числе под
        // приветствиями — там она была ещё и неправдой. Здесь её нет вовсе ни у
        // беседы, ни у заботы: тому, кто только что написал, что ему плохо, не
        // выдают строку пометок.
        //
        // Отбивка 12 — как на iOS: 10 стойки плюс собственные 2 у строки
        // (`ChatPieces.swift:149`). Под текстом, а не над ним: это примечание к
        // сказанному, в отличие от цитаты, которая по A3 стоит первой.
        if (kind.showsChartSilentNote) ...[
          const SizedBox(height: 12),
          Text(l.scrChatSilent, style: AlmaType.meta),
        ],
      ]),
    );
  }

  /// Тело, разрезанное по пустой строке. Пустые куски выброшены: сервер иногда
  /// заканчивает ответ переносом, и хвостовой пустой абзац дорисовывал бы под
  /// ответом пустую строку перед цитатой.
  List<String> get _paragraphs {
    final parts = body
        .split('\n\n')
        .map((p) => p.trim())
        .where((p) => p.isNotEmpty)
        .toList();
    return parts.isEmpty ? [body] : parts;
  }
}

/// Цитата под ответом: подпись, первая позиция и сколько ещё.
///
/// Раскрывается нажатием на «+» — тогда показываются все позиции, из которых
/// прочитан ответ. Свёрнутая по умолчанию, потому что ответ читают, а цитату
/// проверяют: она обязана быть на виду и не обязана занимать треть экрана.
/// Первый порт вываливал все факторы переносом на три строки, и цитата весила
/// больше самого ответа — найдено сравнением с нативным кадром.
class Citation extends StatefulWidget {
  const Citation({super.key, required this.factors});

  final List<String> factors;

  @override
  State<Citation> createState() => CitationState();
}

class CitationState extends State<Citation> {
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
          child: Builder(builder: (context) {
            final style = AlmaType.numeral.copyWith(
              color: AlmaPalette.gold,
              fontFamilyFallback: AlmaType.glyphFallback,
            );
            // Одна строка, и режется только хвост дома — правило 4 спеки
            // мета-строки, целиком в `AlmaShrink.fitMetaLine`. Прежнее
            // многоточие резало по концу ширины и уносило знак.
            return LayoutBuilder(
              builder: (context, box) => Text(
                AlmaShrink.fitMetaLine(
                  line: CabinetWordsMore.factor(l, widget.factors.first),
                  style: style,
                  maxWidth: box.maxWidth,
                  scaler: MediaQuery.textScalerOf(context),
                ),
                // Глазу — глиф, голосу — имя знака: глиф VoiceOver прочесть
                // нечем, а позиция и есть весь смысл этой строки. Вслух
                // называется полная строка, включая целый дом.
                semanticsLabel:
                    CabinetWordsMore.factorSpoken(l, widget.factors.first),
                style: style,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            );
          }),
        ),
        // Строка цитаты набрана одним шагом: на макете (s7) у неё `gap:12px`
        // между всеми четырьмя частями — подписью, позицией, «+N» и знаком.
        // Здесь стояли 8, и счётчик прижимался к позиции ближе, чем подпись к
        // ней же: одна строка выходила набранной двумя разными ритмами.
        if (rest > 0 && !_open) ...[
          const SizedBox(width: 12),
          Text('+$rest',
              style: AlmaType.numeral.copyWith(color: AlmaPalette.goldDeep)),
        ],
        // Восемь плюс четыре собственных отступа кнопки — те же 12. Отступ
        // остаётся её, а не соседа: он и есть площадь нажатия.
        if (rest > 0) const SizedBox(width: 8),
        if (rest > 0)
          // Знак «плюс» — это вся подпись кнопки, и вслух она не говорит
          // ничего. Подпись для голоса есть в каталоге и ровно про это:
          // «показать все позиции, из которых это прочитано».
          Semantics(
            button: true,
            label: l.scrChatReadFromAll,
            child: InkResponse(
              onTap: () => setState(() => _open = !_open),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                child: Text(_open ? '−' : '+',
                    style: AlmaType.numeral
                        .copyWith(color: AlmaPalette.gold, fontSize: 17)),
              ),
            ),
          ),
      ]),
      if (_open)
        for (final factor in widget.factors.skip(1))
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(CabinetWordsMore.factor(l, factor),
                semanticsLabel: CabinetWordsMore.factorSpoken(l, factor),
                style: AlmaType.numeral.copyWith(
                  color: AlmaPalette.gold,
                  fontFamilyFallback: AlmaType.glyphFallback,
                )),
          ),
    ]);
  }
}

/* ── A2: думание ─────────────────────────────────────────────────────────── */

/// Что Alma читает прямо сейчас.
///
/// **Показывается только с настоящими данными.** §6 спеки: «"reading your …"
/// показывается только с настоящими данными запроса; если движок не отдал
/// контекст — нейтральное `reading your chart…`, никаких выдуманных домов».
/// Поэтому [house] и [body] приходят сверху и по умолчанию пусты: потока
/// `{stage, name}` от движка ещё нет, и правдоподобный «четвёртый дом» здесь
/// был бы враньём ровно там, где продукт обещает не выдумывать.
class ThinkingStage {
  const ThinkingStage({this.house, this.body, this.factors = const []});

  /// Порядковое имя дома словами каталога — «fourth», «4-й».
  final String? house;

  /// Имя тела словами каталога — «Saturn», «Сатурн».
  final String? body;

  /// Позиции под строкой. Это карта **самого человека**, посчитанная сервером
  /// и известная клиенту честно, — в отличие от того, что именно движок читает
  /// в эту секунду.
  final List<String> factors;
}

/// A2 — думание: свет в кольце лучей, тлеющая строка, позиции под ней.
class ThinkingView extends StatefulWidget {
  const ThinkingView({super.key, this.stage = const ThinkingStage(), this.slot});

  final ThinkingStage stage;

  /// Место, куда садится **чужой** свет — тот, что живёт в каркасе экрана.
  ///
  /// Свет один на всю беседу и переживает смену приветствия лентой (см.
  /// `AlmaScreen`), поэтому думание не заводит свой, а только объявляет, где и
  /// какого размера ему стоять. `null` — свет ничей и рисуется свой: так вью
  /// остаётся собранной и вне экрана чата.
  final LayerLink? slot;

  @override
  State<ThinkingView> createState() => _ThinkingViewState();
}

class _ThinkingViewState extends State<ThinkingView>
    with SingleTickerProviderStateMixin {
  /// `glowPulse` эталона — 2.4 секунды на цикл, половина в одну сторону.
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (!(MediaQuery.maybeDisableAnimationsOf(context) ?? false)) {
        _pulse.repeat(reverse: true);
      }
    });
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final stage = widget.stage;
    final line = stage.house != null
        ? l.chatReadingHouse(stage.house!)
        : stage.body != null
            ? l.chatOpeningBody(stage.body!)
            : l.scrChatThinking;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 18),
      child: Column(
        children: [
          Center(
            child: widget.slot == null
                ? const AlmaPresence(
                    size: AlmaPresence.thinking,
                    mood: PresenceMood.thinking,
                  )
                // Дырка ровно в коробку кольца: свет каркаса садится в неё
                // левым верхним углом, и разъехаться им нечем.
                : CompositedTransformTarget(
                    link: widget.slot!,
                    child: const SizedBox.square(
                        dimension: AlmaPresence.thinkingRing),
                  ),
          ),
          const SizedBox(height: 14),
          // Строка тлеет, а не мигает: пульс ходит между .55 и 1. Анимация
          // обёрнута вокруг **готового** ребёнка — он строится один раз, и по
          // кадрам меняется только прозрачность, то есть отрисовка.
          AnimatedBuilder(
            animation: _pulse,
            builder: (context, child) => Opacity(
              opacity: 0.55 + 0.45 * Curves.easeInOut.transform(_pulse.value),
              child: child,
            ),
            child: Text(
              line,
              textAlign: TextAlign.center,
              style: AlmaType.meta.copyWith(color: AlmaPalette.goldBright),
            ),
          ),
          if (stage.factors.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              stage.factors.take(2).join('  ·  '),
              textAlign: TextAlign.center,
              style: AlmaType.numeral.copyWith(
                fontSize: 12.5,
                color: AlmaPalette.gold.withValues(alpha: 0.7),
                fontFamilyFallback: AlmaType.glyphFallback,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Абзац, оседающий строками вёрстки.
///
/// **По строкам, а не по словам и не по буквам.** §2 A4: «строки ответа
/// оседают каскадом: fade + подъём 4–8 pt, 70 мс на строку; строка N =
/// opacity 1, N+1 = .55, N+2 = .22. Никакого посимвольного тайпрайтера».
/// Посимвольный набор изображает печатающего бота — ровно то, чем Alma не
/// является; каскад по строкам изображает проступающие чернила.
///
/// Разбивка — `TextPainter.getLineBoundary`, то есть **настоящие** строки
/// вёрстки на этой ширине. Их границы зависят от шрифта, кегля и ширины
/// колонки, и другого способа узнать их нет.
class _SettlingParagraph extends StatelessWidget {
  const _SettlingParagraph({
    required this.text,
    required this.style,
    required this.progress,
    required this.startLine,
  });

  final String text;
  final TextStyle style;

  /// Сколько строк уже проявилось, дробью.
  ///
  /// **Анимацией, а не числом.** Числом каскад перестраивал бы весь абзац на
  /// каждом кадре: `LayoutBuilder` заново мерил бы строки и помечал разметку
  /// грязной — внутри ленивого списка, пока тот сам себя раскладывает. Флаттер
  /// ловит это утверждением `!_doingMountOrUpdate` в `viewport.dart`.
  final Animation<double> progress;

  /// Номер первой строки этого абзаца в сквозной нумерации ответа.
  final int startLine;

  /// Ступени эталона: N = 1, N+1 = .55, N+2 = .22, дальше не видно.
  static double opacityFor(double lead) {
    if (lead <= 0) return 1;
    if (lead >= 3) return 0;
    if (lead <= 1) return 1 - lead * 0.45;
    if (lead <= 2) return 0.55 - (lead - 1) * 0.33;
    return 0.22 * (3 - lead);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        // **Мерить надо ровно тем стилем, каким `Text` потом рисует.**
        //
        // `Text` со стилем-наследником сливает его с окружающим
        // `DefaultTextStyle`, и всё, чего в `AlmaType.voice` не задано —
        // интервал, запасные семейства, — приходит оттуда и делает строку
        // шире промера. Мерил голым стилем — и вымеренная строка на экране
        // переносилась: «…still pull four / ways at once». Слитый стиль
        // отдаётся и рисовальщику, и `Text`.
        final effective = style.inherit
            ? DefaultTextStyle.of(context).style.merge(style)
            : style;
        final painter = TextPainter(
          text: TextSpan(text: text, style: effective),
          textDirection: Directionality.of(context),
          textScaler: MediaQuery.textScalerOf(context),
        )..layout(maxWidth: box.maxWidth);
        final lines = <String>[];
        var offset = 0;
        while (offset < text.length) {
          final range = painter.getLineBoundary(TextPosition(offset: offset));
          if (range.end <= offset) break;
          // Хвостовой пробел уносим: он не виден, но входит в ширину, и
          // строка, померенная с ним, при повторной вёрстке уже не влезает.
          lines.add(text.substring(range.start, range.end).trimRight());
          offset = range.end;
        }
        if (lines.isEmpty) lines.add(text);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final (i, line) in lines.indexed)
              AnimatedBuilder(
                animation: progress,
                builder: (context, child) {
                  final o = opacityFor((startLine + i) - progress.value);
                  return Opacity(
                    opacity: o,
                    // Подъём 4–8 pt: строка приходит снизу и садится на место.
                    child: Transform.translate(
                      offset: Offset(0, 8 * (1 - o).clamp(0.0, 1.0)),
                      child: child,
                    ),
                  );
                },
                // **Без `softWrap: false`.** С ним строка, вымеренная по
                // `getLineBoundary`, при повторной вёрстке выходила на
                // доли точки шире своей ширины и обрезалась по краю: ответ
                // читался как «Your chiron sits at 18°03′ in Capricorn, in th».
                // Найдено на устройстве. Перенос здесь и не случится — кусок
                // по построению ровно на одну строку, — а вот запас на
                // округление нужен.
                child: Text(line, style: effective),
              ),
          ],
        );
      },
    );
  }
}
