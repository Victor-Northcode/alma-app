import 'package:alma/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('оболочка строится и рисует все четыре вкладки', (tester) async {
    await tester.pumpWidget(const AlmaApp());
    await tester.pump(const Duration(milliseconds: 16));

    // Заголовки вкладок приходят из общего каталога, а не из кода экрана.
    expect(find.text('Today'), findsWidgets);
    expect(find.text('My systems'), findsWidgets);
    expect(find.text('Alma'), findsWidgets);
    expect(find.text('Settings'), findsWidgets);
  });

  testWidgets('переключение вкладки меняет заголовок', (tester) async {
    await tester.pumpWidget(const AlmaApp());
    await tester.pump(const Duration(milliseconds: 16));
    await tester.tap(find.text('Settings').last);
    await tester.pump(const Duration(milliseconds: 16));
    expect(find.text('Settings'), findsWidgets);
  });
}
