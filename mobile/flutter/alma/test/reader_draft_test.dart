import 'package:alma/l10n/alma_l10n.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Кнопка «Спросить Alma про X» кладёт в композер вопрос от первого лица.
///
/// Владелец, 29.08.2026: «я на эту кнопку нажимаю — в Альму вставляется
/// сообщение прям „спроси Альму..“» — подпись кнопки уезжала в поле как есть
/// и читалась командой самому себе. Черновик — отдельная строка, и на всех
/// семи языках это вопрос, а не подпись.
void main() {
  testWidgets('черновик вопроса — вопрос, а не подпись кнопки', (tester) async {
    for (final locale in L.supportedLocales) {
      late L l;
      await tester.pumpWidget(MaterialApp(
        locale: locale,
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: Builder(builder: (context) {
          l = L.of(context);
          return const SizedBox.shrink();
        }),
      ));
      final draft = l.readerAskDraft('X');
      expect(draft, isNot(l.readerAskAboutIt('X')),
          reason: '$locale: в поле не должна ложиться подпись кнопки');
      expect(draft.endsWith('?'), isTrue,
          reason: '$locale: черновик — вопрос от первого лица');
    }
  });
}
