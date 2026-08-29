import 'package:alma/l10n/alma_l10n.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Плашка «если однажды отменишь» — короткая и одинаково устроенная на всех
/// семи языках.
///
/// Владелец, 29.08.2026: «если однажды отменишь — покороче». Прежняя строка
/// была в полтора раза длиннее и разъезжалась на четыре строки плашки. Три
/// факта обязаны выжить в любом переводе: купленное навсегда остаётся,
/// подписочное закрывается, расчёт бесплатен; зачин до двоеточия красится
/// золотом (`_cancelHonesty`), поэтому двоеточие обязано быть в каждом языке.
void main() {
  testWidgets('плашка отмены короткая, с зачином, на всех языках',
      (tester) async {
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
      final text = l.paywallV3SubCancelHonesty;
      expect(text.length, lessThan(170),
          reason: '$locale: «покороче» — слово владельца, 29.08.2026');
      expect(text.contains(':'), isTrue,
          reason: '$locale: зачин до двоеточия красится золотом');
      if (locale.languageCode == 'fr') {
        expect(text.contains(' :'), isTrue,
            reason: 'французское двоеточие носит узкий неразрывный пробел');
      }
    }
  });
}
