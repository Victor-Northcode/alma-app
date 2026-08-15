import 'package:alma/design/layout.dart';
import 'package:alma/design/typography.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

/// Подпись кнопки ужимается по правилу владельца, а не «как получится».
///
/// Порядок задан и он не переставляется: спуститься по ступеням кегля до 14 и
/// **только потом** взять короткий вариант строки. Обратный порядок — сначала
/// сократить слово, потом уменьшать — выкидывает половину смысла там, где
/// хватило бы полутора пунктов; бесступенчатое сжатие (`FittedBox`) делает
/// немецкую кнопку рядом с английской похожей на другой шрифт.
void main() {
  const style = AlmaType.button;

  test('влезает как есть — ничего не трогаем', () {
    final fit = AlmaShrink.fitLabel(
      label: 'Continue',
      style: style,
      maxWidth: 300,
    );
    expect(fit.text, 'Continue');
    expect(fit.size, AlmaShrink.buttonSteps.first);
  });

  test('сначала кегль, а короткое слово — только после нижней ступени', () {
    // Ширина подобрана так, чтобы полная подпись села на средней ступени.
    final full = _width('Anmeldelink per E-Mail senden', 15);
    final fit = AlmaShrink.fitLabel(
      label: 'Anmeldelink per E-Mail senden',
      short: 'Link senden',
      style: style,
      maxWidth: full + 1,
    );
    expect(fit.text, 'Anmeldelink per E-Mail senden',
        reason: 'ужать кегль дешевле, чем выкинуть слова');
    expect(fit.size, 15);
  });

  test('когда и 14 не хватает — берётся короткий вариант, снова сверху', () {
    final fit = AlmaShrink.fitLabel(
      label: 'Anmeldelink per E-Mail senden',
      short: 'Link senden',
      style: style,
      maxWidth: _width('Anmeldelink per E-Mail senden', 14) - 20,
    );
    expect(fit.text, 'Link senden');
    expect(fit.size, AlmaShrink.buttonSteps.first,
        reason: 'короткая строка начинает с полного кегля, а не с нижнего');
  });

  test('языку без короткого варианта нижняя ступень — последнее слово', () {
    // «Прислать ссылку для входа» короче не становится, и выдумывать
    // сокращение нельзя: пусть лучше 14 и многоточие, чем изобретённое слово.
    const label = 'Прислать ссылку для входа';
    final fit = AlmaShrink.fitLabel(
      label: label,
      short: label,
      style: style,
      maxWidth: 40,
    );
    expect(fit.text, label);
    expect(fit.size, AlmaShrink.buttonFloor);
  });

  test('без ширины ничего не меряется и не гадается', () {
    final fit = AlmaShrink.fitLabel(
      label: 'Continue',
      style: style,
      maxWidth: double.infinity,
    );
    expect(fit.text, 'Continue');
    expect(fit.size, AlmaShrink.buttonSteps.first);
  });
}

double _width(String text, double size) {
  final painter = TextPainter(
    text: TextSpan(text: text, style: AlmaType.button.copyWith(fontSize: size)),
    maxLines: 1,
    textDirection: TextDirection.ltr,
  )..layout();
  return painter.width;
}
