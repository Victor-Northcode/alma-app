import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/design/typography.dart';
import 'package:alma/screens/alma/chat_turn.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

/// **Ответ Alma режется на строки — и каждый кусок обязан остаться строкой.**
///
/// Каскад A4 оседает построчно, поэтому абзац заранее разрезается по
/// `TextPainter.getLineBoundary` и каждая строка рисуется своим `Text`. Всё
/// держится на одном допущении: кусок, вымеренный как одна строка, одной
/// строкой и нарисуется. Стоит промеру разойтись с вёрсткой хоть на долю
/// точки — и ответ ломается на глазах:
///
/// * с `softWrap: false` строка обрезалась по краю и читалась как «Your chiron
///   sits at 18°03′ in Capricorn, in th»;
/// * без него — переносилась, и в середине фразы вставал обрыв: «…still pull
///   four / ways at once».
///
/// Оба снято на устройстве 16 августа 2026. Причина была одна: мерил голым
/// `AlmaType.voice`, а `Text` рисует его слитым с окружающим
/// `DefaultTextStyle`, откуда приходят межбуквенный интервал и запасные
/// семейства.
///
/// Проверка нарочно ставит в окружение стиль с интервалом — при старой ошибке
/// это и был бы разрыв — и меряет каждый кусок двумя способами: высотой
/// относительно `preferredLineHeight` (перенос) и собственной шириной текста
/// против отданной (обрезка). Оба числа от подставного шрифта тестовой среды
/// не зависят: сколько бы кусков ни вышло из промера, каждый обязан быть ровно
/// одной строкой и умещаться в свою ширину.
void main() {
  testWidgets('каждая вымеренная строка ответа рисуется одной строкой',
      (tester) async {
    tester.view.physicalSize = const Size(402, 900) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(MaterialApp(
      locale: const Locale('en'),
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      home: const Scaffold(
        body: DefaultTextStyle(
          // Окружение, которое `Text` подмешает, а промер — нет, если забыть
          // слить стили.
          //
          // Интервал нарочно огромный. С житейскими полутора точками проверка
          // молчала: подставной шрифт тестовой среды моноширинный, и разницу
          // ровно съедал отрезанный хвостовой пробел — строка выходила впритык
          // в свою ширину. Восемь точек ни один шрифт не погасит: при
          // несведённых стилях промер кладёт в строку в полтора раза больше
          // знаков, чем в неё влезает.
          style: TextStyle(letterSpacing: 8),
          child: SingleChildScrollView(
            child: ChatTurnView(
              mine: false,
              body: 'None of this erases the loud part — your moon, Venus, '
                  'Saturn and Pluto still pull four ways at once in that '
                  'grand cross I described before.\n\n'
                  "But the sun's contacts to your ascendant and Saturn are "
                  'the ballast that does not get pulled into the argument.',
            ),
          ),
        ),
      ),
    ));
    // **`pumpAndSettle` здесь не годится:** свет Alma дышит вечно, и ждать,
    // пока анимации кончатся, значит ждать всегда. Кадры отсчитываются руками.
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    final paragraphs = tester
        .renderObjectList<RenderParagraph>(find.byType(RichText))
        .where((p) => p.text.toPlainText().contains(' '))
        .toList();
    expect(paragraphs, isNotEmpty, reason: 'тело ответа не нарисовалось');
    for (final p in paragraphs) {
      final text = p.text.toPlainText();
      expect(p.size.height, lessThan(p.preferredLineHeight * 1.6),
          reason: 'кусок «$text» перенёсся: промер разошёлся с вёрсткой');
      expect(p.getMaxIntrinsicWidth(double.infinity),
          lessThanOrEqualTo(p.size.width + 0.5),
          reason: 'кусок «$text» шире своей строки: обрежется по краю');
    }
  });

  testWidgets('ответ Alma набран ролью чтения, а не курсивным дисплеем',
      (tester) async {
    // **Правило вида, поставленное числом, потому что жалоба была про вид.**
    //
    // Ответ печатался `AlmaType.voice` — Playfair Display, курсив, 18.5/1.5 —
    // и на трёх абзацах курсивная антиква читается тяжело. Роль чтения у
    // продукта уже была, применялась только к главам, и довод в её же
    // документации: у Playfair высокий контраст, на семнадцати точках тонкие
    // штрихи на тёмном пропадают, курсив добавляет наклон и связки.
    //
    // Проверяется нарисованное, а не константа: сравнение `chatVoice` с самим
    // собой не заметило бы, что вью снова печатает `voice`.
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('en'),
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      home: const Scaffold(
        body: SingleChildScrollView(
          child: ChatTurnView(
            mine: false,
            body: 'Saturn in the seventh describes a slowness about '
                'commitment, and not a verdict on it.',
          ),
        ),
      ),
    ));
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    final body = tester
        .renderObjectList<RenderParagraph>(find.byType(RichText))
        .where((p) => p.text.toPlainText().contains('Saturn in the seventh'))
        .toList();
    expect(body, isNotEmpty, reason: 'тело ответа не нарисовалось');
    for (final p in body) {
      final style = p.text.style!;
      expect(style.fontFamily, AlmaType.readingBody().fontFamily,
          reason: 'ответ ушёл с гарнитуры чтения');
      expect(style.fontStyle, isNot(FontStyle.italic),
          reason: 'длинный абзац снова курсивом');
      expect(style.fontSize, AlmaType.readingBody().fontSize);
      expect(style.height, AlmaType.readingBody().height);
    }
  });
}
