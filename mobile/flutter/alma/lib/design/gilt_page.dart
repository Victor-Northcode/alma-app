import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';

import 'palette.dart';
import 'typography.dart';

/// Страница, на которой читают главу. Тёмная — с 25.08.2026, слово владельца:
/// «сделай чтоб главы были тёмные, а не светлые». Цвета живут в
/// `AlmaPalette.parchment*`/`ink` — имена пережили обе смены поверхности.
///
/// **Снимка золочёной бумаги здесь тоже нет — и это отдельное решение.** Кадры
/// `s51`/`s52` застилали главу фотографией рваного листа в барочной раме, она
/// была построена и проверена на симуляторе, и владелец, посмотрев, попросил
/// вернуть простой чистый фон: «верни главы просто белым цветом, убери фон».
/// Отменена именно поверхность — всё, что на ней стоит, осталось: поля, кружок
/// возврата, нить чтения со счётчиком, знак конца главы.
///
/// **Поля 52/56 пережили снимок намеренно.** Заведены они были под габарит
/// рамы, но держатся собственной причиной: 294 точки — это 45–50 знаков в
/// строке, то есть та ширина, на которой глаз находит начало следующей строки
/// без усилия. Общее поле продукта 22 даёт 358 и на самом длинном чтении
/// приложения читается хуже. Возвращать их к 22 значило бы чинить то, на что
/// никто не жаловался.
///
/// Имя класса осталось прежним: его знают пять экранов, и переименование ради
/// исчезнувшей текстуры стоило бы дороже, чем эта строка объяснения.
class GiltPage extends StatelessWidget {
  const GiltPage({super.key});

  /// Боковое поле до чистого центра листа. Общее поле продукта — 22
  /// (`AlmaMetrics.pad`); здесь оно втрое шире, и это не «просторнее ради
  /// красоты»: 52 — ровно та черта, за которой кончаются завитки рамы.
  static const side = 52.0;

  /// Справа на четыре точки больше: у правого края стоит нить прогресса
  /// ([GiltThread]) с вертикальным счётчиком глав, и текст не должен упираться
  /// в её цифры.
  static const sideRight = 56.0;

  /// Верх кнопки возврата — от верхнего края экрана, не от безопасной зоны.
  /// Ниже внутренней кромки рамы (67) на двадцать одну точку.
  static const headTop = 88.0;

  /// Верх вклейки: с неё начинается содержимое страницы.
  static const contentTop = 142.0;

  /// Кнопка возврата на бумаге — кружок цвета слоновой кости.
  ///
  /// **Голая стрелка здесь пропадает.** На пергаменте она стояла на ровном
  /// поле; на золочёной бумаге её угол приходится на завитки рамы, и тёмный
  /// глиф на золоте не виден ни на кадре, ни на устройстве. Холст сажает её в
  /// светлый кружок с золотым контуром — это и делает её кнопкой, а не
  /// значком.
  static const chip = 34.0;

  /// Кружок нарисован на 34, а нажимается на 44: меньше сорока четырёх точек
  /// в этом продукте не бывает ни одна цель. Разница уходит в прозрачное поле
  /// вокруг кружка — потому отступы ниже считаются от него, а не от кружка.
  static const hit = 44.0;

  /// Отступ до **поля** кнопки, а не до её кружка.
  ///
  /// Считается по вертикали: холст меряет 88 до кружка, а сажается на экран
  /// поле, которое на пять точек выше. По горизонтали кнопка больше не
  /// отмеряется от полей страницы вовсе — она стоит по общему полю продукта
  /// (`AlmaMetrics.pad`), там же, где «←» на всех остальных кадрах; поля 52/56
  /// принадлежат ширине строки чтения, а не шапке.
  static const headPad = (hit - chip) / 2;

  /// Отбивка от кнопки до содержимого. Не число, а разность двух чисел с
  /// холста: где кончается поле кнопки и где начинается вклейка.
  static const headGap = contentTop - (headTop - headPad) - hit;

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(gradient: AlmaGradient.parchment),
      child: SizedBox.expand(),
    );
  }
}

/// Кнопка возврата на золочёной бумаге — стрелка в кружке слоновой кости.
///
/// Живёт здесь, а не на экране главы: она принадлежит поверхности. Стрелка без
/// кружка на этом фоне не кнопка, а царапина на золоте, и всякий, кто положит
/// на бумагу второй экран, получит её вместе с листом.
class GiltBack extends StatelessWidget {
  const GiltBack({super.key, required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      child: GestureDetector(
        onTap: onTap,
        // Поле вокруг кружка ловит палец наравне с ним: невидимое, но нажатие
        // считает своим — иначе цель была бы 34 точки вместо сорока четырёх.
        behavior: HitTestBehavior.opaque,
        child: SizedBox(
          width: GiltPage.hit,
          height: GiltPage.hit,
          child: Center(
            child: Container(
              // Крупнее дефолтной фишки (34): на светлой теме «назад» была заметно
              // мельче золотой стрелки тёмной темы, палец промахивался (владелец,
              // 22 авг). Растёт сама кнопка; `GiltPage.chip` (разметка шапки) не
              // трогаем — фишка (40) по-прежнему сидит по центру зоны нажатия (44).
              width: 40,
              height: 40,
              // Страница тёмная с 25.08.2026 — кружок слоновой кости на ней
              // светил фонарём. Теперь это ночная фишка с золотым кантом, той
              // же семьи, что единый крестик (AlmaClose): одна логика закрытия
              // — один вид ручки.
              decoration: BoxDecoration(
                color: AlmaPalette.night700.withValues(alpha: 0.85),
                shape: BoxShape.circle,
                border: Border.all(
                  color: AlmaPalette.goldDeep.withValues(alpha: 0.5),
                ),
              ),
              child: Icon(
                Icons.arrow_back,
                size: 22,
                color: AlmaPalette.inkLight.withValues(alpha: 0.9),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Нить прогресса у правого поля: сколько главы прочитано и какая она по счёту.
///
/// **Считает прочитанное, а не главы.** На холсте нить стоит на обоих кадрах
/// главы и отличается только наливом — 28 точек из 150 на открытии (`s51`) и 64
/// на чтении (`s52`), при одном и том же «3 / 16» под ней. То есть длинная
/// золотая часть — это положение в тексте, а цифры — положение в системе.
///
/// Начальный обрубок в 28 точек не обнуляется: страница, только что открытая,
/// уже начата, и пустая нить читалась бы как «ничего не загрузилось».
class GiltThread extends StatelessWidget {
  const GiltThread({super.key, required this.read, required this.counter});

  /// Доля прочитанного, 0…1.
  final ValueListenable<double> read;

  /// «3 / 16» — номер главы и сколько их всего.
  final String counter;

  static const _height = 150.0;
  static const _least = 28.0 / _height;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Align(
        alignment: Alignment.centerRight,
        child: Padding(
          padding: const EdgeInsets.only(right: 36),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ValueListenableBuilder<double>(
                valueListenable: read,
                builder: (context, value, _) {
                  final filled =
                      _height * value.clamp(_least, 1.0);
                  return SizedBox(
                    width: 7,
                    height: _height,
                    child: Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Positioned(
                          left: 2.5,
                          top: 0,
                          child: Container(
                            width: 2,
                            height: _height,
                            decoration: BoxDecoration(
                              color: AlmaPalette.ink.withValues(alpha: 0.14),
                              borderRadius: BorderRadius.circular(1),
                            ),
                          ),
                        ),
                        Positioned(
                          left: 2.5,
                          top: 0,
                          child: Container(
                            width: 2,
                            height: filled,
                            decoration: BoxDecoration(
                              color: AlmaPalette.goldDeep,
                              borderRadius: BorderRadius.circular(1),
                            ),
                          ),
                        ),
                        // Головка нити стоит на конце налива, а не под ним:
                        // это она отмечает место, до которого дочитано.
                        Positioned(
                          left: 0,
                          top: filled - 4,
                          child: Container(
                            width: 7,
                            height: 7,
                            decoration: BoxDecoration(
                              color: AlmaPalette.goldDeep,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: AlmaPalette.goldDeep
                                      .withValues(alpha: 0.6),
                                  blurRadius: 6,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
              const SizedBox(height: 8),
              // Счётчик стоит вдоль нити, а не поперёк: поперёк он занял бы
              // ширину, которой у правого поля нет, и полез бы под текст.
              RotatedBox(
                quarterTurns: 1,
                child: Text(
                  counter,
                  style: AlmaType.numeral.copyWith(
                    fontSize: 12,
                    color: AlmaPalette.goldDeep,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
