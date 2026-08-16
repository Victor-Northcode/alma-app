import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../cabinet_words.dart';

/// Одна реплика беседы — **одна на два экрана**.
///
/// Живая лента и переоткрытая беседа рисуют реплики этим виджетом, и это не
/// экономия строк. На нативе у экрана прошлой беседы была своя копия, и она
/// молча разошлась с лентой: одно и то же сообщение показывало «ответила не из
/// карты» в чате и не показывало в архиве. Одна вью — одно поведение.
class ChatTurnView extends StatelessWidget {
  const ChatTurnView({
    super.key,
    required this.mine,
    required this.body,
    this.citedFactors = const [],
  });

  final bool mine;
  final String body;
  final List<String> citedFactors;

  @override
  Widget build(BuildContext context) {
    if (mine) {
      // Реплика человека — справа и в пузыре, и пузырь никогда не во всю
      // ширину: иначе он перестаёт читаться как чья-то отдельная фраза.
      return Align(
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
      );
    }
    final l = L.of(context);
    return Padding(
      padding: const EdgeInsets.only(top: 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(l.tabAlma.toUpperCase(), style: AlmaType.overline),
          const SizedBox(width: 12),
          Expanded(
            child: Container(
              height: 1,
              decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
            ),
          ),
        ]),
        // **Абзацы — отдельными строками, а не пустой строкой внутри одной.**
        //
        // Тело склеивалось через `\n\n`, и между абзацами вставала пустая
        // строка засечного кегля — почти тридцать точек, вдвое больше, чем на
        // макете, где абзацы идут через 10. Ответ из трёх абзацев из-за этого
        // распадался на три отдельных высказывания.
        for (final paragraph in _paragraphs)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(paragraph, style: AlmaType.voice),
          ),
        if (citedFactors.isNotEmpty) ...[
          const SizedBox(height: 12),
          Citation(factors: citedFactors),
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
          child: Text(
            CabinetWordsMore.factor(l, widget.factors.first),
            // Глазу — глиф, голосу — имя знака: глиф VoiceOver прочесть
            // нечем, а позиция и есть весь смысл этой строки.
            semanticsLabel: CabinetWordsMore.factorSpoken(l, widget.factors.first),
            style: AlmaType.numeral.copyWith(
              color: AlmaPalette.gold,
              fontFamilyFallback: AlmaType.glyphFallback,
            ),
            overflow: TextOverflow.ellipsis,
          ),
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
