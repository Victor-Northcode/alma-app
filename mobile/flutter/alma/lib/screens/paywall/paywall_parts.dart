/// Детали, повторяющиеся на пяти продающих кадрах v3, — ровно один раз.
///
/// Разметка снята с `docs/monetization/SCREENS-V3.md`, раздел за разделом.
/// Числа в этом файле — points кадра 402 × 874 из холста, и «уточнять» их на
/// новом месте нельзя по той же причине, по которой этого нельзя делать с
/// палитрой (`design/palette.dart`): расхождение между экраном и эталоном
/// заводится не решением, а мелкой правкой, которую никто не помнит.
///
/// ## Про золотые канты числом, а не токеном
///
/// Спека называет это прямо: в палитре есть `hairlineGold` — золото на 0.16, —
/// и такой прозрачности на семнадцати кадрах нет **ни разу**. На холсте живут
/// 0.28, 0.30, 0.42, 0.45, 0.50, и каждая встречается один-два раза. Шкала из
/// трёх ступеней («тихий 0.22, обычный 0.30, громкий 0.45») покрыла бы их
/// округлением, то есть перерисовала бы карточку подписки V8 кантом вдвое
/// тише нарисованного. Поэтому прозрачность стоит числом на месте, а рядом —
/// имя кадра, с которого она снята. Тянуться к `hairlineGold` «потому что
/// похоже» нельзя: это и есть то самое незаметное расхождение.
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../billing/alma_store.dart';
import '../../design/close_button.dart';
import '../../design/arrival.dart';
import '../../design/buttons.dart';
import '../../design/gold_texture.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../billing/store_words.dart';

/// Шапка продающего экрана: надзаголовок слева, крестик справа.
///
/// **Крестик обязателен, и это не вкус.** §5 ТЗ, правило 4: любой пейволл
/// закрывается с первого раза, без «точно уверены?». На V6 и V8 он нарисован;
/// на V2, V5 и V7 холст не нарисовал ничего, и спека называет это дырой №6 —
/// поэтому здесь он есть у всех, кто эту шапку берёт.
class PaywallHeader extends StatelessWidget {
  const PaywallHeader({
    super.key,
    this.overline,
    this.centred = false,
    this.leading,
    required this.onClose,
  });

  /// Золотая строка прописными. `null` — шапка без надписи.
  final String? overline;

  /// Надзаголовок стоит по центру, а закрывает экран стрелка слева, — так
  /// устроен V9. Иначе надзаголовок слева, крестик справа (V6, V8).
  final bool centred;

  /// Что нарисовать слева вместо распорки — стрелка «назад» на V9.
  final Widget? leading;

  final VoidCallback onClose;

  /// Поле пальца у крестика. Сам знак — Golos 18, но 18 × 18 не нажимается.
  static const _touch = 44.0;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final label = overline == null
        ? const SizedBox.shrink()
        : Text(
            overline!.toUpperCase(),
            textAlign: centred ? TextAlign.center : TextAlign.start,
            style: centred
                ? AlmaType.readerHead.copyWith(color: AlmaPalette.gold)
                : AlmaType.overline,
          );
    if (!centred) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: label),
          _Close(onTap: onClose, semantics: l.journeyClose),
        ],
      );
    }
    return Row(
      children: [
        SizedBox(
          width: _touch,
          child: leading ?? const SizedBox.shrink(),
        ),
        Expanded(child: label),
        // Распорка ровно в ширину левого элемента: центр обязан быть настоящим
        // центром строки, а не центром остатка (число холста — 18 у знака,
        // здесь 44 у поля пальца).
        const SizedBox(width: _touch),
      ],
    );
  }
}

/// Крестик: знак маленький, цель большая.
class _Close extends StatelessWidget {
  const _Close({required this.onTap, required this.semantics});

  final VoidCallback onTap;
  final String semantics;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: semantics,
        // Единый вид закрытия (24 авг, см. AlmaClose): владелец назвал мелкий
        // текстовый «×» неудобным, и он был единственным непохожим на общий.
        child: AlmaClose(onTap: onTap),
      );
}

/// Стрелка «назад» шапки V9 и V4: Golos 18, слоновая кость на 0.7.
class PaywallBack extends StatelessWidget {
  const PaywallBack({super.key, required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Semantics(
      button: true,
      label: l.cabinetBack,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: SizedBox(
          width: PaywallHeader._touch,
          height: PaywallHeader._touch,
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              '←',
              style: AlmaType.button.copyWith(
                fontSize: 18,
                color: AlmaPalette.body.withValues(alpha: 0.7),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Знак-веха над вклейкой: ромб, точка, ромб. Путь холста, 30 × 44.
///
/// **Копия того же знака живёт в `offer_screen.dart` (`_Wand`), и это
/// временно.** Тот файл — прежняя витрина `s8`/`s37`, которую VR приговорил
/// вместе с лестницей; сводить их в одну вещь ради двух недель совместной
/// жизни значит трогать экран, который сейчас работает и закрыт тестом.
/// Умрёт витрина — умрёт и копия.
class PaywallWand extends StatelessWidget {
  const PaywallWand({super.key, required this.width});

  final double width;

  @override
  Widget build(BuildContext context) => CustomPaint(
        size: Size(width, width * 44 / 30),
        painter: const _WandPainter(),
      );
}

class _WandPainter extends CustomPainter {
  const _WandPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 30;
    void lozenge(List<Offset> points, Color color) {
      final path = Path()..moveTo(points.first.dx * k, points.first.dy * k);
      for (final p in points.skip(1)) {
        path.lineTo(p.dx * k, p.dy * k);
      }
      path.close();
      canvas.drawPath(path, Paint()..color = color);
    }

    lozenge(const [
      Offset(15, 0),
      Offset(18, 14),
      Offset(15, 22),
      Offset(12, 14),
    ], AlmaPalette.gold);
    canvas.drawCircle(
        Offset(15 * k, 27 * k), 2.4 * k, Paint()..color = AlmaPalette.starFill);
    lozenge(const [
      Offset(15, 32),
      Offset(16.6, 38),
      Offset(15, 44),
      Offset(13.4, 38),
    ], AlmaPalette.gold.withValues(alpha: 0.6));
  }

  @override
  bool shouldRepaint(_WandPainter oldDelegate) => false;
}

/// Вклейка: картина, скрим, внутренний штрих и подпись по нижнему краю.
///
/// Одна вещь на три кадра, потому что на холсте это одна вещь с разными
/// числами: V2 — 206 × 290 закрытой главы, V6 — полоса 150 живого слоя,
/// V9 — карта 184 × 250 самой читаемой системы. Различаются высота, радиус,
/// плотность канта и подпись; устройство одно и то же, и разведённое по трём
/// экранам оно разойдётся на четвёртом.
class PaywallPlate extends StatelessWidget {
  const PaywallPlate({
    super.key,
    required this.image,
    required this.height,
    this.width,
    this.radius = 16,
    this.edge = 1,
    required this.edgeColor,
    this.innerAlpha = 0.24,
    this.innerInset = 5,
    this.scrimFrom = 0.05,
    this.scrimTo = 0.85,
    this.scrimStart = 0.35,
    this.alignment = const Alignment(0, -0.32),
    this.shadow,
    this.caption,
    this.captionInset = 16,
    this.captionBottom = 12,
  });

  final ImageProvider image;
  final double height;
  final double? width;
  final double radius;

  /// Толщина канта: 1 у полос, 1.5 у карт-героев (V2, V9).
  final double edge;
  final Color edgeColor;

  /// Внутренний штрих цвета `starFill` — он на всех вклейках холста.
  final double innerAlpha;
  final double innerInset;

  /// Скрим: сверху почти прозрачный, к низу плотный — иначе подпись не
  /// читается ни на одной фотографии.
  final double scrimFrom;
  final double scrimTo;
  final double scrimStart;

  /// `object-position` холста: у неба это 34 % высоты, у карт — центр.
  final Alignment alignment;

  final List<BoxShadow>? shadow;

  /// Подпись внутри нижнего края вклейки.
  final Widget? caption;
  final double captionInset;
  final double captionBottom;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: edgeColor, width: edge),
        boxShadow: shadow,
      ),
      child: ClipRRect(
        // Радиус картины на толщину канта меньше рамы: иначе угол картинки
        // вылезает из-под золота светлой ниткой.
        borderRadius: BorderRadius.circular(radius - edge),
        child: Stack(fit: StackFit.expand, children: [
          Image(image: image, fit: BoxFit.cover, alignment: alignment),
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  AlmaPalette.night900.withValues(alpha: scrimFrom),
                  AlmaPalette.night900.withValues(alpha: scrimTo),
                ],
                stops: [scrimStart, 1],
              ),
            ),
          ),
          IgnorePointer(
            child: Padding(
              padding: EdgeInsets.all(innerInset),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(radius - innerInset),
                  border: Border.all(
                      color: AlmaPalette.starFill.withValues(alpha: innerAlpha)),
                ),
              ),
            ),
          ),
          if (caption != null)
            Positioned(
              left: captionInset,
              right: captionInset,
              bottom: captionBottom,
              child: caption!,
            ),
        ]),
      ),
    );
  }
}

/// ✦-строка: звёздочка и фраза, которую человек обязан прочесть раньше цены.
///
/// **Порядок «✦-строка → абзац продления → кнопка» переставлять нельзя.** Довод
/// в §7 ТЗ: жалобы «думала, всё входит в подписку» — красная линия проекта, и
/// строка, разделяющая ожидания, обязана стоять **над** ценой, а не под ней и
/// не мелким кеглем. Поэтому она набрана полужирным и светлее окружения: на
/// V6 из трёх строк донного блока она должна читаться первой.
class PaywallSpark extends StatelessWidget {
  const PaywallSpark({super.key, required this.text, this.size = 13});

  final String text;

  /// 13 на V6, 12.5 на V8 — числа кадров.
  final double size;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 1),
            child: Text('✦',
                style: AlmaType.numeral.copyWith(fontSize: 12)),
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              text,
              style: AlmaType.body.copyWith(
                fontSize: size,
                height: 1.45,
                fontWeight: FontWeight.w600,
                // Вариативному шрифту вес задаётся осью — иначе он молча
                // останется обычным. См. `typography.dart`.
                fontVariations: const [FontVariation('wght', 600)],
                color: AlmaPalette.goldBright,
              ),
            ),
          ),
        ],
      );
}

/// Тихая ссылка: поле для пальца, никакой рамки.
///
/// На продающем экране их не больше одной **продающей** — это правило 1 ТЗ.
/// `Restore`, `Terms` и `Privacy` в счёт не идут: они ничего не продают, а
/// требуют их оба магазина.
class PaywallQuietLink extends StatelessWidget {
  const PaywallQuietLink({
    super.key,
    required this.label,
    required this.onTap,
    this.color,
    this.size = 13,
    this.bold = false,
  });

  final String label;
  final VoidCallback? onTap;
  final Color? color;
  final double size;
  final bool bold;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Opacity(
          opacity: onTap == null ? 0.5 : 1,
          child: Padding(
            // 8 × 12 — поле подвала холста; палец мельче 44 не бывает, но
            // ссылки стоят в ряд, и общий рост строки даёт остальное.
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
            child: Text(
              label,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AlmaType.button.copyWith(
                fontSize: size,
                color: color ?? AlmaPalette.gold,
                fontWeight: bold ? FontWeight.w600 : FontWeight.w400,
                fontVariations: [FontVariation('wght', bold ? 600 : 400)],
              ),
            ),
          ),
        ),
      );
}

/// Тёплый ореол под золотой кнопкой.
///
/// На V6 это единственная кнопка холста с золотой тенью
/// (`0 8px 20px rgba(180,146,63,.35)`), и стоит она там не для красоты: это
/// самая дорогая покупка каталога. Свет лежит **за** кнопкой и в нажатии не
/// участвует.
class PaywallHalo extends StatelessWidget {
  const PaywallHalo({super.key, required this.child, this.warm = false});

  final Widget child;

  /// Золотой ореол V6 против общего тёмного свечения остальных кадров.
  final bool warm;

  @override
  Widget build(BuildContext context) => Stack(
        alignment: Alignment.center,
        children: [
          Positioned(
            left: 44,
            right: 44,
            bottom: 0,
            height: 22,
            child: IgnorePointer(
              child: Breathing(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(11),
                    boxShadow: [
                      BoxShadow(
                        color: warm
                            ? const Color(0xFFB4923F).withValues(alpha: 0.35)
                            : GoldTexture.edge.withValues(alpha: 0.5),
                        blurRadius: warm ? 20 : 28,
                        spreadRadius: 4,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          child,
        ],
      );
}

/// Золотая кнопка продающего экрана вместе со всем, что бывает вместо неё.
///
/// **Цена приходит из магазина, и выдумать её нельзя.** `price == null` — это
/// молчащий App Store: кнопки нет, вместо неё строка о том, что купить сейчас
/// нельзя, и попытка спросить магазин ещё раз. Число на кнопке обязано совпасть
/// со списанным; показанное «$4.99» тому, с кого возьмут 590 ₽, — это и отказ
/// ревью, и обман.
class PaywallCta extends StatelessWidget {
  const PaywallCta({
    super.key,
    required this.label,
    required this.store,
    required this.onTap,
    this.warm = false,
  });

  /// Готовая подпись с ценой — или `null`, если цены нет.
  final String? label;
  final AlmaStore store;
  final VoidCallback onTap;
  final bool warm;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final busy = store.busy != null;
    if (label == null) {
      return Column(children: [
        Text(l.storeUnavailable,
            textAlign: TextAlign.center, style: AlmaType.meta),
        const SizedBox(height: 14),
        AlmaButton(
          kind: AlmaButtonKind.outline,
          fills: false,
          label: l.stateRetry,
          onTap: store.load,
        ),
      ]);
    }
    return PaywallHalo(
      warm: warm,
      child: AlmaButton(
        // Пилюля: радиус 28 при высоте 56 — половина высоты, то есть
        // умолчание `AlmaButton`. Прямоугольник со скруглением 15 — форма
        // анкеты, и на продающем экране её быть не должно.
        label: busy ? l.stateLoadingShort : label!,
        onTap: busy || store.restoring ? null : onTap,
      ),
    );
  }
}

/// Строка состояния магазина под кнопкой.
///
/// Ни одна из этих фраз не начинается с извинения и ни из одной не следует,
/// что деньги могли пропасть, — это язык W6: «деньги не теряются никогда».
class PaywallNotice extends StatelessWidget {
  const PaywallNotice({super.key, required this.store, this.centred = true});

  final AlmaStore store;
  final bool centred;

  @override
  Widget build(BuildContext context) {
    final notice = store.notice;
    if (notice == null) return const SizedBox.shrink();
    final l = L.of(context);
    // «Покупка проходит» — карточка W6, а не строка. Оба извещения — это
    // «деньги на месте, право едет»: `verifyLater` — магазин списал, наш
    // `/verify` в эту секунду не ответил; `pending` — магазин ещё ждёт
    // одобрения. Человеку, с которого уже спросили денег, положено видимое
    // усилие (кольцо) и действие (ретрай), а не строчка петитом.
    if (notice.message == StoreMessage.pending ||
        notice.message == StoreMessage.verifyLater) {
      return PaywallProcessingCard(store: store, message: notice.message);
    }
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Text(
        paywallNoticeText(l, notice.message),
        textAlign: centred ? TextAlign.center : TextAlign.start,
        style: AlmaType.meta.copyWith(
          color: switch (notice.tone) {
            StoreTone.good => AlmaPalette.agree,
            StoreTone.waiting => AlmaPalette.gold,
            StoreTone.bad => AlmaPalette.disagree,
          },
        ),
      ),
    );
  }
}

/// Карточка «покупка проходит» — W6, карточка 1.
///
/// Каждый её элемент отвечает на «я заплатила, а где?», и ответ начинается с
/// того, что деньги на месте, а не с извинения: ни «извините», ни слова, из
/// которого следует, что деньги могли пропасть, ни поддержки первым
/// действием — язык кадра.
///
/// **Подпись у двух состояний разная, и это не отступление от W6, а его же
/// правило, прочитанное до конца.** Кадр писан про `verifyLater` — «оплата
/// прошла, `/verify` не ответил», — и его текст «Apple has taken it» правда
/// только там. На `pending` (спросить у родителя, шаг вне приложения) деньги
/// ещё не списаны, и печатать «принял» значило бы сказать о деньгах неправду
/// — худшую из возможных на этой карточке. Заголовок и кольцо общие.
class PaywallProcessingCard extends StatelessWidget {
  const PaywallProcessingCard({
    super.key,
    required this.store,
    required this.message,
  });

  final AlmaStore store;
  final StoreMessage message;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Padding(
      // Отбивка кадра — 16.
      padding: const EdgeInsets.only(top: 16),
      child: Container(
        // Числа W6: паддинг 17 · 17 · 15, кант золота на 0.3, радиус 16,
        // заливка ночи-700 на 0.42.
        padding: const EdgeInsets.fromLTRB(17, 17, 17, 15),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.3)),
          color: AlmaPalette.night700.withValues(alpha: 0.42),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _ProcessingRing(),
            const SizedBox(height: 12),
            Text(
              l.paywallV3StateProcessing,
              style: AlmaType.headingM.copyWith(height: 1.2),
            ),
            const SizedBox(height: 4),
            Text(
              message == StoreMessage.pending
                  ? l.paywallPending
                  : l.paywallV3StateProcessingNote,
              style: AlmaType.meta.copyWith(fontSize: 12.5, height: 1.5),
            ),
            const SizedBox(height: 12),
            AlmaButton(
              kind: AlmaButtonKind.outline,
              // Высота и радиус кадра (46/23) — переопределением параметров, а
              // не правкой метрики: три контурных высоты на холсте — так на
              // холсте, довод в §1 SCREENS-V3.
              height: 46,
              radius: 23,
              label: l.paywallV3StateErrorRetry,
              // Ретрай ускоряет то, что случится и без него: восстановление
              // переспрашивает магазин, тот передоставляет транзакцию, и
              // `/verify` получает второй шанс сейчас, а не через backoff.
              // Кнопка нужна не механике, а человеку: две минуты глядеть на
              // кольцо и не иметь действия — худшее, что можно предложить
              // тому, с кого уже списали.
              onTap: store.restoring ? null : store.restore,
            ),
          ],
        ),
      ),
    );
  }
}

/// Кольцо 34 × 34 — единственное быстрое вращение в продукте: 6 секунд на
/// оборот против 60 у эмблемы пары и 80 у медальона Today. Обязано быть
/// быстрым: медленное кольцо читается украшением, а это — работа.
class _ProcessingRing extends StatefulWidget {
  const _ProcessingRing();

  @override
  State<_ProcessingRing> createState() => _ProcessingRingState();
}

class _ProcessingRingState extends State<_ProcessingRing>
    with SingleTickerProviderStateMixin {
  late final AnimationController _spin = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 6),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      // «Меньше движения» оставляет кольцо неподвижным — не замедленным:
      // половина движения читается как подтормаживание.
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (!still) _spin.repeat();
    });
  }

  @override
  void dispose() {
    _spin.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // ClipRect — то же, что делает CSS, обрезая фон по коробке элемента:
    // радиус градиента считается до дальнего угла и без обрезки штрихи
    // вылезали бы за 34 точки.
    return ClipRect(
      child: AnimatedBuilder(
        animation: _spin,
        builder: (context, _) => CustomPaint(
          size: const Size.square(34),
          painter: _ProcessingRingPainter(turn: _spin.value),
        ),
      ),
    );
  }
}

/// Штрихи кольца: 30 через 12°, каждый шириной 3° — это
/// `repeating-conic-gradient(0deg 3deg / 12deg)` кадра, гаснущие с обоих
/// краёв кольцевой маской (радиальный градиент 46–48–78–82 % радиуса до
/// дальнего угла — та же арифметика, что у венца медальона Today).
class _ProcessingRingPainter extends CustomPainter {
  const _ProcessingRingPainter({required this.turn});

  /// Доля оборота, 0…1.
  final double turn;

  static const _ticks = 30;
  static const _width = 3 * math.pi / 180;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = size.center(Offset.zero);
    final reach = size.width * 0.7071;
    final gold = AlmaPalette.gold.withValues(alpha: 0.55);
    final paint = Paint()
      ..shader = RadialGradient(
        radius: 0.7071,
        colors: [
          gold.withValues(alpha: 0),
          gold,
          gold,
          gold.withValues(alpha: 0),
        ],
        stops: const [0.46, 0.48, 0.78, 0.82],
      ).createShader(Offset.zero & size);

    final path = Path();
    for (var i = 0; i < _ticks; i++) {
      final a = turn * 2 * math.pi + i * 2 * math.pi / _ticks;
      path.moveTo(centre.dx, centre.dy);
      path.arcTo(
        Rect.fromCircle(center: centre, radius: reach),
        a - _width / 2,
        _width,
        false,
      );
      path.close();
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _ProcessingRingPainter old) => old.turn != turn;
}

/// Девять состояний магазина словами человека.
String paywallNoticeText(L l, StoreMessage message) => switch (message) {
      StoreMessage.storeSilent => l.storeUnavailable,
      StoreMessage.pending => l.paywallPending,
      StoreMessage.offline => l.paywallOffline,
      StoreMessage.notVerified => l.paywallNotVerified,
      StoreMessage.verifyLater => l.paywallVerifyLater,
      StoreMessage.withdrawn => l.paywallWithdrawn,
      StoreMessage.unlocked => l.paywallRestored,
      StoreMessage.restoring => l.storeRestoring,
      StoreMessage.restored => l.paywallV3StateRestoreDone,
      StoreMessage.restoredNone => l.storeRestoredNone,
    };

/// Подвал: `Restore`, а рядом то, что положено этому кадру.
///
/// `Restore` требуют оба магазина, без него приложение отклоняют, — то есть
/// это не второй продающий зов, а обязательное управление. Правило «не более
/// одной тихой ссылки» читается как «не более одной **продающей**».
class PaywallFooter extends StatelessWidget {
  const PaywallFooter({super.key, required this.store, this.children = const []});

  final AlmaStore store;

  /// Что стоит после `Restore` через точку-разделитель.
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Wrap(
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        PaywallQuietLink(
          label: store.restoring ? l.storeRestoring : l.paywallRestore,
          bold: true,
          color: AlmaPalette.body.withValues(alpha: 0.7),
          onTap: store.restoring || store.busy != null ? null : store.restore,
        ),
        for (final child in children) ...[
          Text('·',
              style: AlmaType.meta
                  .copyWith(color: AlmaPalette.gold.withValues(alpha: 0.4))),
          child,
        ],
      ],
    );
  }
}

/// Донный блок продающего экрана: поля 22 по бокам и воздух под последней
/// строкой.
///
/// На холсте он абсолютный — `left/right 22, bottom 28`. Домашнего индикатора
/// холст не считает, а устройство его имеет, поэтому 28 отсчитываются от
/// безопасной зоны, а не от кромки стекла.
class PaywallBottom extends StatelessWidget {
  const PaywallBottom({super.key, required this.children, this.bottom = AlmaMetrics.gapLarge});

  final List<Widget> children;
  final double bottom;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.fromLTRB(AlmaMetrics.pad, 0, AlmaMetrics.pad,
            bottom + MediaQuery.paddingOf(context).bottom),
        child: Column(mainAxisSize: MainAxisSize.min, children: children),
      );
}
