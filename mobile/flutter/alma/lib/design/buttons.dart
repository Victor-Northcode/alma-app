import 'package:flutter/material.dart';

import 'gold_texture.dart';
import 'metrics.dart';
import 'palette.dart';
import 'typography.dart';

/// Четыре кнопки, которые есть у продукта.
///
/// Порт `mobile/ios/Alma/DesignSystem/Components/AlmaButton.swift`. Иерархия
/// держится **высотой не меньше, чем заливкой**: золото 56, обводка 54, вуаль
/// 50. Это не вкусовое: три одинаковых по высоте кнопки читаются как три
/// равных выбора, а витрина — ровно то место, где они равными быть не должны.
enum AlmaButtonKind {
  /// Одно действие экрана. Двух золотых на одном экране не бывает.
  gold,

  /// Обдуманная альтернатива — «не сейчас», «только эту главу».
  outline,

  /// Тихое действие в списке.
  veil,

  /// Удаление аккаунта, отмена плана. Всегда обводкой: красную заливку
  /// нажимают рефлексом.
  danger,
}

class AlmaButton extends StatefulWidget {
  const AlmaButton({
    super.key,
    required this.label,
    required this.onTap,
    this.kind = AlmaButtonKind.gold,
    this.fills = true,
  });

  final String label;

  /// `null` — кнопка выключена: приглушена и не отвечает.
  final VoidCallback? onTap;
  final AlmaButtonKind kind;

  /// Тянется ли кнопка на всю ширину. На телефоне — почти всегда.
  final bool fills;

  @override
  State<AlmaButton> createState() => _AlmaButtonState();
}

class _AlmaButtonState extends State<AlmaButton> {
  bool _pressed = false;

  double get _height => switch (widget.kind) {
        AlmaButtonKind.gold => AlmaMetrics.buttonHeight,
        AlmaButtonKind.outline => AlmaMetrics.buttonHeightOutline,
        AlmaButtonKind.veil => AlmaMetrics.buttonHeightVeil,
        AlmaButtonKind.danger => 44,
      };

  TextStyle get _style => switch (widget.kind) {
        // Слоновая кость, а не чернила: текстурное золото тёмное, и тёмная
        // подпись на нём не читается вовсе.
        AlmaButtonKind.gold =>
          AlmaType.button.copyWith(color: AlmaPalette.inkLight),
        AlmaButtonKind.outline => AlmaType.button
            .copyWith(fontSize: 16, color: AlmaPalette.goldBright),
        AlmaButtonKind.veil =>
          AlmaType.button.copyWith(fontSize: 15, color: AlmaPalette.body),
        AlmaButtonKind.danger =>
          AlmaType.button.copyWith(fontSize: 14.5, color: AlmaPalette.disagree),
      };

  Decoration get _decoration {
    final radius = BorderRadius.circular(_height / 2);
    return switch (widget.kind) {
      // Золото рисует `GoldSurface`: три слоя не складываются в один
      // `BoxDecoration`, который знает про единственный градиент.
      AlmaButtonKind.gold => const BoxDecoration(),
      AlmaButtonKind.veil => BoxDecoration(
          color: AlmaPalette.body.withValues(alpha: _pressed ? 0.13 : 0.07),
          borderRadius: radius,
        ),
      AlmaButtonKind.outline => BoxDecoration(
          color: AlmaPalette.gold.withValues(alpha: _pressed ? 0.14 : 0),
          borderRadius: radius,
          border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.5)),
        ),
      AlmaButtonKind.danger => BoxDecoration(
          borderRadius: radius,
          border: Border.all(
              color: const Color(0xFF8C3A2B).withValues(alpha: 0.5)),
        ),
    };
  }

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onTap != null;
    // Нажатие — оседание на точку, а не масштаб. Золотая кнопка, которая
    // уменьшается, читается как пластик; та, что проседает, — как ключ.
    return GestureDetector(
      onTapDown: enabled ? (_) => setState(() => _pressed = true) : null,
      onTapUp: enabled ? (_) => setState(() => _pressed = false) : null,
      onTapCancel: enabled ? () => setState(() => _pressed = false) : null,
      onTap: widget.onTap,
      behavior: HitTestBehavior.opaque,
      child: AnimatedOpacity(
        opacity: enabled ? 1 : 0.45,
        duration: AlmaMotion.tap,
        child: AnimatedSlide(
          offset: _pressed && widget.kind == AlmaButtonKind.gold
              ? const Offset(0, 0.018)
              : Offset.zero,
          duration: AlmaMotion.tap,
          curve: AlmaMotion.tapCurve,
          child: _wrapGold(Container(
            height: _height,
            padding: const EdgeInsets.symmetric(horizontal: 28),
            decoration: _decoration,
            // **Ширина решается строкой, а не `alignment`.**
            //
            // `Container` с `alignment` растягивается на всё, что ему дали, —
            // и кнопка «Не сейчас», которой велено обнимать свою надпись,
            // выходила во всю ширину рядом с золотой. Разница между ними и
            // есть иерархия: одна занимает строку, вторая — слово.
            child: Row(
              mainAxisSize:
                  widget.fills ? MainAxisSize.max : MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Flexible(
                  child: Text(
                    widget.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: _style,
                  ),
                ),
              ],
            ),
          )),
        ),
      ),
    );
  }

  /// Золотая кнопка одевается в текстуру, остальные три остаются как есть.
  Widget _wrapGold(Widget child) => widget.kind == AlmaButtonKind.gold
      ? GoldSurface(
          radius: BorderRadius.circular(_height / 2),
          dimmed: _pressed,
          child: child,
        )
      : child;
}

/// Строка-действие: слово слева, стрелка справа, ничего вокруг.
///
/// Порт `ActionRow` из `CabinetPieces.swift`. Не кнопка: там, где действие —
/// продолжение текста («открыть гороскоп», «прочесть весь день»), рамка вокруг
/// него была бы вторым акцентом на экране, у которого акцент один.
class AlmaActionRow extends StatelessWidget {
  const AlmaActionRow({super.key, required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Row(children: [
            Expanded(
              child: Text(label,
                  style: AlmaType.body
                      .copyWith(color: AlmaPalette.body.withValues(alpha: 0.85))),
            ),
            const SizedBox(width: 12),
            Text('→',
                style: AlmaType.displayL.copyWith(
                    fontSize: 15,
                    color: AlmaPalette.gold.withValues(alpha: 0.55))),
          ]),
        ),
      );
}

/// Волосяная линия, которой этот продукт разделяет строки. Ни карточек, ни
/// рамок: содержимое стоит на ночи.
class AlmaHairline extends StatelessWidget {
  const AlmaHairline({super.key});

  @override
  Widget build(BuildContext context) =>
      Container(height: 1, color: AlmaPalette.hairline);
}
