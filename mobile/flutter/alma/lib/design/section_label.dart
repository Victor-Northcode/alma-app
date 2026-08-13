import 'package:flutter/material.dart';

import 'palette.dart';
import 'typography.dart';

/// Подпись раздела и волосяная линия за ней — повторяющийся мотив кабинета.
///
/// Порт `SectionLabel` из `mobile/ios/Alma/DesignSystem/Components/Surfaces.swift`,
/// и две вещи в нём стоят того, чтобы жить в одном месте, а не в пяти копиях
/// на пяти экранах.
///
/// **Подпись переносится, линия остаётся у первой строки.** В SwiftUI линия
/// требует бесконечной ширины, поэтому подписи достаётся минимум и «ГОРОСКОП
/// НА СЕГОДНЯ» встаёт в две строки; во Flutter `Expanded` отдаёт линии лишь
/// остаток, и та же подпись шла одной строкой во всю ширину. Рядом два кадра —
/// расхождение видно сразу. Здесь подписи отведена та же доля, что она
/// занимает на нативе, и перенос получается тот же.
///
/// **Линия выровнена по первой строке, а не по середине блока.** На нативе это
/// `alignmentGuide(.firstTextBaseline) { -4 }` с комментарием про немецкий, где
/// подпись длиннее всех: линия, повешенная по центру, оказывается рядом со
/// *второй* строкой, и первая стоит неподчёркнутой.
class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key, this.trailing});

  final String text;

  /// Число или слово у правого конца линии — счётчик глав, например.
  final String? trailing;

  /// Доля ширины, отданная подписи. Снято с нативного кадра: «ГОРОСКОП НА
  /// СЕГОДНЯ» занимает там треть строки и переносится, линия забирает остальное.
  static const _labelShare = 0.305;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ConstrainedBox(
            constraints: BoxConstraints(maxWidth: constraints.maxWidth * _labelShare),
            child: Text(text.toUpperCase(), style: AlmaType.overline),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              // Середина прописной высоты первой строки, а не середина блока.
              padding: const EdgeInsets.only(top: 7),
              child: Container(
                height: 1,
                decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
              ),
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 12),
            Padding(
              padding: const EdgeInsets.only(top: 1),
              child: Text(trailing!,
                  style: AlmaType.numeral.copyWith(color: AlmaPalette.goldBright)),
            ),
          ],
        ],
      ),
    );
  }
}
