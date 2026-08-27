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

  // ── страница чтения: тёмная с 25.08.2026 ────────────────────────────────
  // Светлый пергамент прожил два дня после «не все хотят читать на белом
  // ярком экране» и кончился словами владельца «сделай чтоб главы были
  // тёмные, а не светлые». Имена оставлены: их знают четыре файла
  // (gilt_page, chapter, what_next, tab_bar), и переименование стоило бы
  // дороже этих строк. `parchment*` теперь ночные тона страницы — чуть
  // теплее и светлее общей ночи, чтобы страница читалась листом, а не
  // дырой; `ink` — светлые чернила на ней, тон общего body.
  static const parchment = Color(0xFF10141F);
  static const parchmentA = Color(0xFF131826);
  static const parchmentB = Color(0xFF0B0E1D);
  static const ink = Color(0xFFEDE7DA);

  /// Тона ночной продающей поверхности — **одни на карточку и на лист**.
  ///
  /// Карточка оффера (`AlmaGradient.nightCard`) и лист покупки (`AlmaSheet`)
  /// обязаны быть одной семьёй не на словах: пока числа жили в двух местах,
  /// они уже успели разъехаться незамеченными (ревью 27.08.2026). Кто правит
  /// поверхность — правит эти три токена, и обе вещи меняются вместе;
  /// `design_tokens_test.dart` стережёт сами числа.
  static final nightCardTop = night.withValues(alpha: 0.88);
  static final nightCardBottom = night900.withValues(alpha: 0.97);
  static final nightCardEdge = gold.withValues(alpha: 0.30);

  // ── согласие и спор между системами ─────────────────────────────────────
  static const agree = Color(0xFF8FBF9A);
  static const disagree = Color(0xFFE0917F);

  // ── вуали и линии ───────────────────────────────────────────────────────
  static final veil = body.withValues(alpha: 0.07);
  static final veilStrong = body.withValues(alpha: 0.09);
  static final hairline = body.withValues(alpha: 0.10);
  static final hairlineGold = gold.withValues(alpha: 0.16);

  // ── приглушённый текст ──────────────────────────────────────────────────
  // Прозрачности подняты на шаг (было .72/.68/.62): вторичный текст — подписи,
  // подсказки, мета-строки — жаловались на слабый контраст с ночью на реальном
  // экране (22 авг). Это всё ещё «тише основного», но уже читаемо, а не призрак.
  static final muted = body.withValues(alpha: 0.80);
  static final muted2 = body.withValues(alpha: 0.76);
  static final muted3 = body.withValues(alpha: 0.72);
  static final inkMuted = ink.withValues(alpha: 0.80);
  static final inkMuted2 = ink.withValues(alpha: 0.72);

  // ── свечение кнопки ─────────────────────────────────────────────────────
  static const goldGlowRadius = 20.0;
  static final goldGlow = gold.withValues(alpha: 0.16);
  static const buttonRadius = 15.0;
  static final button = const Color(0xFFB4923F).withValues(alpha: 0.38);
}

/// Градиенты — решения компонентов, а не токены, за которыми экран тянется сам.
///
/// Каждый принадлежит одной вещи: знаку, полосе пергамента. Экран, которому
/// понадобился ещё один, почти наверняка рисует то, что уже нарисовано.
///
/// **Заливки кнопки здесь нет и быть не может.** Стояли две — `goldButton` и
/// `goldButtonPressed`, плоское золото `#DCC48A → #A8873C` с тёмной подписью,
/// — и дизайн-система запрещает такую кнопку словом «никогда»: читается она
/// пластиковой наклейкой, а не ключом от двери. Настоящая кнопка тёмная и
/// трёхслойная, её собирает `GoldSurface` в `gold_texture.dart`, и одним
/// градиентом она не выражается в принципе.
class AlmaGradient {
  const AlmaGradient._();

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

  /// Поверхность чтения — с 25.08.2026 ночная (см. `AlmaPalette.parchment*`).
  static const parchment = LinearGradient(
    colors: [
      AlmaPalette.parchmentA,
      Color(0xFF0F1322),
      AlmaPalette.parchmentB,
    ],
    stops: [0.0, 0.6, 1.0],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Продающая карточка на ночной странице — оффер в конце главы, карточки
  /// «Что дальше». Числа листа покупки (`NightSheet`, холст v3): ночь на 0.88
  /// в глубокую ночь на 0.97, то есть **темнее страницы**, а не светлее.
  ///
  /// Карточка до 26.08.2026 была кремовой на 75 % — числа холста V1 для
  /// пергамента, — и на ночной странице (с 25.08) стала серо-голубой плитой со
  /// светлыми чернилами на светлом; владелец: «синие элементы (оплата)
  /// выбиваются визуально». Не `night700`: тот синеет на ночи ровно так же.
  static final nightCard = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [AlmaPalette.nightCardTop, AlmaPalette.nightCardBottom],
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
