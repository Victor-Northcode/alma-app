import 'dart:async';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import 'palette.dart';
import 'typography.dart';

/// Share-карточка — картинка дня, которую человек уносит в сторис.
///
/// Лучший трюк Co-Star, перенесённый честно (владелец, 01.09.2026: «каждый
/// шэр — бесплатная реклама с нашим именем»): экран «Сегодня» складывается в
/// вертикальную карточку 1080×1350 — ночь, дата, луна, четыре области с
/// глифами их аспектов — и уходит в системный шэр-лист одной кнопкой.
///
/// **На карточке нет ни одного выдуманного слова.** Дата, фаза, области и
/// глифы — ровно то, что стоит на экране: те же данные, тем же тоном
/// (поток золотом, трение красным). Карточка — снимок дня, а не открытка
/// с пожеланием.
class ShareDayCard extends StatelessWidget {
  const ShareDayCard({
    super.key,
    required this.dateLine,
    required this.moonGlyph,
    required this.moonLine,
    required this.rows,
  });

  /// «1 сентября» — уже локализована экраном.
  final String dateLine;

  /// ☽ / ○ — глиф фазы, как на медальоне.
  final String moonGlyph;

  /// «убывающий серп · 7 %» — слова экрана.
  final String moonLine;

  /// Область → (метка, глиф аспекта, тон). Пустой глиф — тихая область.
  final List<ShareDayRow> rows;

  /// Размер сторис-карточки: 4:5, как публикуют оба формата.
  static const size = Size(1080, 1350);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size.width,
      height: size.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF0A0D1C), Color(0xFF101530), Color(0xFF0A0D1C)],
        ),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 96, vertical: 110),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Шапка: словесный знак — то самое имя, ради которого карточка
          // существует.
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('✦ ALMA',
                  style: AlmaType.meta.copyWith(
                    fontSize: 34,
                    letterSpacing: 10,
                    color: AlmaPalette.gold,
                  )),
              Text(dateLine.toUpperCase(),
                  style: AlmaType.meta.copyWith(
                    fontSize: 26,
                    letterSpacing: 4,
                    color: AlmaPalette.body.withValues(alpha: 0.7),
                  )),
            ],
          ),
          const Spacer(),
          // Луна — по центру, крупно: у дня одно небо на всех.
          Center(
            child: Column(children: [
              Text(moonGlyph,
                  style: const TextStyle(
                      fontSize: 150, color: AlmaPalette.inkLight, height: 1)),
              const SizedBox(height: 26),
              Text(moonLine,
                  style: AlmaType.meta.copyWith(
                    fontSize: 28,
                    letterSpacing: 3,
                    color: AlmaPalette.body.withValues(alpha: 0.75),
                  )),
            ]),
          ),
          const Spacer(),
          for (final row in rows) ...[
            Container(
              height: 1,
              color: AlmaPalette.body.withValues(alpha: 0.14),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 30),
              child: Row(children: [
                Text(row.label.toUpperCase(),
                    style: AlmaType.meta.copyWith(
                      fontSize: 30,
                      letterSpacing: 4,
                      color: row.glyph.isEmpty
                          ? AlmaPalette.body.withValues(alpha: 0.5)
                          : AlmaPalette.goldBright,
                    )),
                const Spacer(),
                Text(row.glyph.isEmpty ? '·' : row.glyph,
                    style: TextStyle(fontSize: 40, color: row.tone)),
              ]),
            ),
          ],
          const SizedBox(height: 40),
          Center(
            child: Text('alma.pazl.ai',
                style: AlmaType.meta.copyWith(
                  fontSize: 26,
                  letterSpacing: 3,
                  color: AlmaPalette.body.withValues(alpha: 0.45),
                )),
          ),
        ],
      ),
    );
  }
}

class ShareDayRow {
  const ShareDayRow(this.label, this.glyph, this.tone);

  final String label;
  final String glyph;
  final Color tone;
}

/// Снимает виджет в PNG, не показывая его человеку.
///
/// Карточка вставляется в Overlay за левым краем экрана — нарисованная, но
/// невидимая: `Offstage` не рисует вовсе и `toImage` с него не снять, а
/// сдвиг за экран оставляет слой в дереве рендера честно отрисованным.
/// Кадр ожидается через `endOfFrame`: снимать раньше — получить пустоту.
Future<Uint8List?> captureCard(BuildContext context, Widget card) async {
  final overlay = Overlay.maybeOf(context, rootOverlay: true);
  if (overlay == null) return null;
  final boundaryKey = GlobalKey();
  final entry = OverlayEntry(
    builder: (_) => Positioned(
      left: -ShareDayCard.size.width - 60,
      top: 0,
      child: IgnorePointer(
        child: RepaintBoundary(
          key: boundaryKey,
          child: MediaQuery(
            // Своя плотность: карточка — печатный лист фиксированного
            // размера, и системный масштаб шрифта не должен её ломать.
            data: const MediaQueryData(),
            child: Material(type: MaterialType.transparency, child: card),
          ),
        ),
      ),
    ),
  );
  overlay.insert(entry);
  try {
    await WidgetsBinding.instance.endOfFrame;
    final boundary = boundaryKey.currentContext?.findRenderObject()
        as RenderRepaintBoundary?;
    if (boundary == null) return null;
    final image = await boundary.toImage(pixelRatio: 2);
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    return bytes?.buffer.asUint8List();
  } finally {
    entry.remove();
  }
}
