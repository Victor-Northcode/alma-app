import 'package:flutter/material.dart';

/// Открыта ли сейчас страница на пергаменте.
///
/// Бар вкладок живёт выше главы по дереву и о ней не знает, а стык тёмной
/// полосы со светлой страницей владелец назвал стрёмным. Признак один на
/// приложение: глава поднимает его, пока открыта, бар слушает.
final ValueNotifier<bool> readingNow = ValueNotifier(false);

/// Каждый цвет продукта, ровно один раз.
///
/// Порт `mobile/ios/Alma/DesignSystem/Palette.swift`, значение в значение. Числа
/// не подбирались заново и не «уточнялись»: расхождение между платформами —
/// это то, ради чего затевался переход на один код, и начинать его с новой
/// палитры значило бы воспроизвести ту же болезнь в первый же день.
///
/// **Почему прозрачности здесь, а не на месте применения.** Вуали, волосяные
/// линии и приглушённый текст — это не «тот же цвет, но бледнее», а отдельные
/// решения дизайна: `almaMuted` встречается на двадцати экранах, и если каждый
/// будет писать `withOpacity(0.72)` сам, то через месяц на трёх из них будет
/// 0.7, а на одном 0.75. iOS держит их именованными по той же причине.
class AlmaPalette {
  const AlmaPalette._();

  // ── ночь ────────────────────────────────────────────────────────────────
  static const night = Color(0xFF0A0D1C);
  static const night850 = Color(0xFF090C1A);
  static const night900 = Color(0xFF070A16);
  static const voidDark = Color(0xFF04060E);
  static const night700 = Color(0xFF101636);

  // ── индиго: свечение неба ───────────────────────────────────────────────
  static const indigo = Color(0xFF3A3484);
  static const indigoBright = Color(0xFF604EC4);
  static const indigoDeep = Color(0xFF1E3A96);

  // ── золото ──────────────────────────────────────────────────────────────
  static const gold = Color(0xFFC9AE6B);
  static const goldDeep = Color(0xFFA8873C);
  static const goldBright = Color(0xFFE4D3A2);
  static const starFill = Color(0xFFF6E7BC);

  // ── текст на ночи ───────────────────────────────────────────────────────
  static const inkLight = Color(0xFFF6F1E4);
  static const body = Color(0xFFEDE7DA);
  static const inkOnGold = Color(0xFF141019);

  // ── пергамент: единственная светлая поверхность ─────────────────────────
  static const parchment = Color(0xFFF1E9D6);
  // Приглушён на шаг: «не все хотят читать на белом ярком экране». Это всё
  // ещё бумага, а не серый лист — тон уходит в тёплую тень, не в цвет.
  static const parchmentA = Color(0xFFEDE3CC);
  static const parchmentB = Color(0xFFDFD0AF);
  static const ink = Color(0xFF1C1A17);

  // ── согласие и спор между системами ─────────────────────────────────────
  static const agree = Color(0xFF8FBF9A);
  static const disagree = Color(0xFFE0917F);

  // ── вуали и линии ───────────────────────────────────────────────────────
  static final veil = body.withValues(alpha: 0.07);
  static final veilStrong = body.withValues(alpha: 0.09);
  static final hairline = body.withValues(alpha: 0.10);
  static final hairlineGold = gold.withValues(alpha: 0.16);

  // ── приглушённый текст ──────────────────────────────────────────────────
  static final muted = body.withValues(alpha: 0.72);
  static final muted2 = body.withValues(alpha: 0.68);
  static final muted3 = body.withValues(alpha: 0.62);
  static final inkMuted = ink.withValues(alpha: 0.72);
  static final inkMuted2 = ink.withValues(alpha: 0.62);

  // ── свечение кнопки ─────────────────────────────────────────────────────
  static const goldGlowRadius = 20.0;
  static final goldGlow = gold.withValues(alpha: 0.16);
  static const buttonRadius = 15.0;
  static final button = const Color(0xFFB4923F).withValues(alpha: 0.38);
}

/// Градиенты — решения компонентов, а не токены, за которыми экран тянется сам.
///
/// Их пять, и каждый принадлежит одной вещи: заливке кнопки, знаку, полосе
/// пергамента, линейке между разделами. Экран, которому понадобился шестой,
/// почти наверняка рисует то, что уже нарисовано.
class AlmaGradient {
  const AlmaGradient._();

  /// Единственная заливка кнопки. Свет сверху, чтобы она читалась как чеканный
  /// металл, а не как крашеный прямоугольник.
  static const goldButton = LinearGradient(
    colors: [Color(0xFFDCC48A), Color(0xFFA8873C)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static const goldButtonPressed = LinearGradient(
    colors: [Color(0xFFC6A659), Color(0xFF8F7233)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  /// Заливка знака и всякое золото, которому положено выглядеть состаренным,
  /// а не жёлтым.
  static const goldLeaf = LinearGradient(
    colors: [
      Color(0xFFFBEDC4),
      Color(0xFFE0C077),
      Color(0xFFB3913F),
      Color(0xFF8A6F2E),
    ],
    stops: [0.00, 0.34, 0.70, 1.00],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Единственная светлая поверхность.
  static const parchment = LinearGradient(
    colors: [
      AlmaPalette.parchmentA,
      Color(0xFFEFE3C9),
      AlmaPalette.parchmentB,
    ],
    stops: [0.0, 0.6, 1.0],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Волосяная линия, гаснущая с обоих концов, — линейка между разделами.
  static LinearGradient get fadedRule => LinearGradient(
        colors: [
          Colors.transparent,
          AlmaPalette.gold.withValues(alpha: 0.34),
          Colors.transparent,
        ],
        begin: Alignment.centerLeft,
        end: Alignment.centerRight,
      );
}
