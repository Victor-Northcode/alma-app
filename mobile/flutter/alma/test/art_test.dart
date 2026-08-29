import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:alma/design/art.dart';
import 'package:alma/net/models.dart' show SystemSlug;

/// Ассет, которого нет, во Flutter не падает — он рисует пустоту.
///
/// Опечатка в пути живёт до тех пор, пока кто-нибудь не откроет этот экран на
/// устройстве, и выглядит как «дизайнер не дал картинку». Здесь список из
/// `AlmaArt` сверяется с диском: с самим файлом, со всеми тремя масштабами и с
/// записью в манифесте.
void main() {
  final root = Directory.current.path;

  test('каждый путь из AlmaArt существует на диске', () {
    final missing = [
      for (final path in AlmaArt.bundled)
        if (!File('$root/$path').existsSync()) path,
    ];
    expect(missing, isEmpty, reason: 'нет файлов: $missing');
  });

  test('у каждой картинки есть 2x и 3x', () {
    final missing = <String>[];
    for (final path in AlmaArt.bundled) {
      final name = path.split('/').last;
      for (final scale in ['2.0x', '3.0x']) {
        final variant = '$root/assets/img/$scale/$name';
        if (!File(variant).existsSync()) missing.add('$scale/$name');
      }
    }
    expect(missing, isEmpty, reason: 'нет масштабов: $missing');
  });

  test('у всех восьми систем своя карта, и они разные', () {
    // Прежнее правило вернулось словом владельца 29.08.2026 вечером: «там 8
    // картинок должно быть как раньше, красивые» — после дня, когда лица
    // прятались под небо и колода стала «5 почти одинаковых».
    final cards = {for (final s in SystemSlug.values) AlmaArt.card(s)};
    expect(cards.length, SystemSlug.values.length,
        reason: 'две системы делят одну картинку');
  });

  test('манифест объявляет папки с картинками', () {
    final pubspec = File('$root/pubspec.yaml').readAsStringSync();
    for (final line in ['assets/img/', 'assets/img/2.0x/', 'assets/img/3.0x/']) {
      expect(pubspec, contains(line), reason: 'в pubspec.yaml нет $line');
    }
  });

  test('вклейки глав в бандл не попали — кроме той, что продаёт', () {
    // **У сторожа была одна причина, и она перестала быть всеобщей.**
    //
    // Он запрещал вшивать вклейки целиком, потому что «они нужны только при
    // открытии главы, то есть после сети»: сорок картин — половина веса
    // приложения, и носить их с собой незачем. Это по-прежнему верно про
    // сорок.
    //
    // Но `plate-sky` с 17 августа 2026 стоит не в главе, а на экране подписки
    // (`V6`): холст рисует её карточкой, и владелец заметил, что вместо неё
    // подставлен общий фон. На пейволле действует обратное правило, записанное
    // в `pubspec.yaml`: продающий слой вшивается, потому что встречается
    // раньше, чем человек согласится чего-то ждать, — пустая рамка в секунду
    // решения о деньгах стоит дороже двухсот килобайт.
    //
    // Поэтому исключение **одно и названо поимённо**. Тот, кто завтра положит
    // сюда вторую вклейку, всё так же уронит этот тест и будет обязан написать,
    // на каком продающем экране она стоит.
    const sellingPlates = {'plate-sky.webp'};
    final bundled = Directory('$root/assets/img').listSync()
        .whereType<File>()
        .map((f) => f.path.split('/').last)
        .where((n) => n.startsWith('plate-'))
        .where((n) => !sellingPlates.contains(n))
        .toList();
    expect(bundled, isEmpty,
        reason: 'вклейки нужны только при открытии главы, то есть после сети');
  });
}
