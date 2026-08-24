import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

import 'palette.dart';

/// Единые «закрыть» и «назад» — один вид на всё приложение.
///
/// До 24 августа каждый экран рисовал выход по-своему: мелкая стрелка, текстовое
/// «←» в трёх размерах, крестик пейволла, а у треда беседы выхода не было
/// вовсе. Владелец: «крестик маленький и неудобный… то крестик, то стрелочка,
/// то слева, то справа — сделай идентичным». Правило теперь одно:
///
/// * **✕ справа** — у всего, что открыто ПОВЕРХ (читалки, юридика, вход,
///   тред, добавление человека): закрыть и вернуться туда, откуда пришёл;
/// * **← слева** — только у настоящего «назад» внутри стека (глава →
///   оглавление). Его рисует сам экран главы (`GiltBack`/стрелка) — там свои
///   выверенные пергаментные правила.
///
/// Фишка 40 в зоне нажатия 44 — те же числа, что у `GiltBack`, чтобы рука
/// встречала одинаковую цель на светлом и тёмном.
class AlmaClose extends StatelessWidget {
  const AlmaClose({super.key, required this.onTap, this.back = false});

  final VoidCallback onTap;

  /// `true` — стрелка «назад» вместо крестика, тем же кружком: для мест, где
  /// уход — навигация вглубь стека, а не закрытие поверх.
  final bool back;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () {
          HapticFeedback.selectionClick();
          // Клавиатура снимается ДО ухода с экрана: закрытый посреди набора
          // экран оставлял её висеть над следующим — владелец: «клавиатура
          // может зависнуть и остаться» (24 авг). Единая кнопка закрытия —
          // единственное место, где это чинится один раз для всех экранов.
          FocusManager.instance.primaryFocus?.unfocus();
          onTap();
        },
        child: SizedBox(
          width: 44,
          height: 44,
          child: Center(
            child: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: AlmaPalette.veilStrong,
                shape: BoxShape.circle,
                border: Border.all(color: AlmaPalette.hairline),
              ),
              child: Icon(
                back ? Icons.arrow_back : Icons.close,
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
