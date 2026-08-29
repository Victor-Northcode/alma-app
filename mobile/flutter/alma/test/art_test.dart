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

  test('под небом только карты с лицами; предметные — на месте', () {
    // Правило владельца от 29.08.2026: «убрать лица (я сделаю новые
    // картинки), кроме раздела совместимости». Каждый файл просмотрен
    // глазами: лица — на пяти; нумерология (диск с числами), транзиты
    // (армиллярная сфера) и пара остаются со своими картами. Когда художник
    // привезёт новые, вернуть прежний тест: «у всех восьми своя карта».
    const withFaces = {
      SystemSlug.natal, SystemSlug.birthCard, SystemSlug.solarReturn,
      SystemSlug.astrocartography, SystemSlug.synthesis,
    };
    for (final s in SystemSlug.values) {
      if (withFaces.contains(s)) {
        expect(AlmaArt.card(s), AlmaArt.sky,
            reason: 'лицо уходит под небо до новой картинки');
      } else {
        expect(AlmaArt.card(s), contains('card-'),
            reason: 'предметная карта обязана остаться на месте');
      }
    }
    // Файлы художника при этом остаются в бандле — подмена про показ.
    expect(AlmaArt.bundled.where((p) => p.contains('card-')).length,
        SystemSlug.values.length);
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
