import 'package:flutter/material.dart';

import 'art.dart';
import 'palette.dart';
import 'typography.dart';

/// Золочёная бумага — поверхность, на которой читают главу.
///
/// **Это фотография листа в раме, а не заливка, и отсюда все числа ниже.**
/// Пергамент (`AlmaGradient.parchment`) был градиентом от края до края: текст на
/// нём стоял по общему полю 22, потому что мешать ему было нечему. Здесь под
/// текстом снимок — рваный лист ручной бумаги с золотыми прожилками, лежащий в
/// барочной золочёной раме на тёмном мраморе (`s51`, `s52`). Рама занимает
/// внешнюю пятую часть кадра, и слово, попавшее на её завитки, не читается
/// вовсе. Поэтому у страницы появились поля: содержимое садится в **чистый
/// центр** листа, а не в габарит экрана.
///
/// **Почему поля числами, а не долей высоты.** Картинка кладётся `cover` от
/// верхнего края, то есть её внутренний край плывёт вместе с пропорцией экрана:
/// на 402×874 он проходит по 23 точкам слева и 67 сверху, на 375×812 — по 22 и
/// 62. Разброс — четыре точки на все телефоны, и он тонет в отбивке 52/88,
/// которая взята с холста прямо. Считать эти четыре точки формулой значило бы
/// завести в продукте геометрию, которую никто не сможет проверить глазами.
class GiltPage extends StatelessWidget {
  const GiltPage({super.key});

  /// Боковое поле до чистого центра листа. Общее поле продукта — 22
  /// ([AlmaMetrics.pad]); здесь оно втрое шире, и это не «просторнее ради
  /// красоты»: 52 — ровно та черта, за которой кончаются завитки рамы.
  static const side = 52.0;

  /// Справа на четыре точки больше: у правого края стоит нить прогресса
  /// ([GiltThread]) с вертикальным счётчиком глав, и текст не должен упираться
  /// в её цифры.
  static const sideRight = 56.0;

  /// Верх кнопки возврата — от верхнего края экрана, не от безопасной зоны.
  /// Ниже внутренней кромки рамы (67) на двадцать одну точку.
  static const headTop = 88.0;

  /// Кнопка возврата на бумаге — кружок цвета слоновой кости.
  ///
  /// **Голая стрелка здесь пропадает.** На пергаменте она стояла на ровном
  /// поле; на золочёной бумаге её угол приходится на завитки рамы, и тёмный
  /// глиф на золоте не виден ни на кадре, ни на устройстве. Холст сажает её в
  /// светлый кружок с золотым контуром — это и делает её кнопкой, а не
  /// значком.
  static const chip = 34.0;

  /// Отбивка от кнопки до содержимого: 142 (верх вклейки на холсте) − 88 − 34.
  static const headGap = 20.0;

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        // **Пергамент остался — под фотографией.** Ассет, который не
        // раскодировался, во Flutter не падает: он рисует пустоту, и чернильный
        // текст оказался бы на ночном фоне под ним. Градиент внизу стопки стоит
        // ровно за этим — светлая поверхность есть всегда, даже когда картинки
        // почему-то нет.
        gradient: AlmaGradient.parchment,
        image: DecorationImage(
          image: AssetImage(AlmaArt.giltPaper),
          // `center top/cover` с холста: лист прижат к верхнему краю, лишнее
          // срезается по бокам. Растянуть его целиком нельзя — рама
          // деформируется, и это видно на первом же взгляде.
          fit: BoxFit.cover,
          alignment: Alignment.topCenter,
        ),
      ),
      child: SizedBox.expand(),
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
