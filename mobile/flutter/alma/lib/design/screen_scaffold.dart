import 'package:flutter/material.dart';

import 'arrival.dart';
import 'metrics.dart';
import 'palette.dart';
import 'sky/night_sky.dart';
import 'typography.dart';

/// Форма, которая есть у каждого экрана кабинета, чтобы ни один не открывал её
/// заново.
///
/// Порт `mobile/ios/Alma/Screens/ScreenScaffold.swift`. Он улаживает три вещи,
/// каждую из которых легко испортить по-своему на каждом экране и невозможно
/// заметить, пока она не испорчена на четырёх по-разному:
///
/// * **прокрутку и боковое поле** — одно `pad`, приложенное один раз;
/// * **верх страницы** — золотой надзаголовок и засечный заголовок, и заголовок
///   никогда не в системной панели;
/// * **низ** — столько места, чтобы последняя строка вышла из-под бара вкладок.
///   Владелец нашёл это на мелком тексте в настройках, который обрывался на
///   полуслове.
///
/// Экрану, которому нужна не прокручиваемая колонка, а что-то другое — карта,
/// беседа, — этот каркас не подходит. **Тогда он обязан нарисовать себе небо
/// сам**: экран без неба это экран плоско-чёрный, и повесить небо выше по
/// дереву негде.
class ScreenScaffold extends StatelessWidget {
  const ScreenScaffold({
    super.key,
    this.eyebrow,
    this.title,
    this.mood = SkyMood.cabinet,
    this.seed = 0x414C4D41,
    this.onOverscroll,
    this.onRefresh,
    this.trailing,
    this.titleStyle,
    this.underTitle,
    required this.children,
  });

  /// Небольшая золотая строка над заголовком. Необязательна: у главы она есть,
  /// у беседы нет.
  final String? eyebrow;
  final String? title;

  /// Что делает небо на этом экране. Чтение его приглушает.
  final SkyMood mood;

  /// Какое небо достаётся экрану. Разные зёрна на двух экранах — это то, что
  /// делает переход между ними видимым переходом; одно и то же зерно на одном
  /// экране — то, что не даёт звёздам перетасоваться при появлении клавиатуры.
  final int seed;

  /// Насколько читатель протянул за последнюю строку, в логических точках.
  /// Ноль везде, кроме одного экрана: тянуть за конец главы — значит открыть
  /// следующую.
  final ValueChanged<double>? onOverscroll;

  final Future<void> Function()? onRefresh;

  /// То, что стоит справа от заголовка, — медальон луны на «Сегодня».
  final Widget? trailing;

  /// Строка, живущая **внутри** заголовочного блока, под самим заголовком и
  /// слева от [trailing].
  ///
  /// На «Сегодня» это фаза луны, и место у неё не декоративное: на нативе она
  /// стоит в той же колонке, что заголовок, в десяти точках под ним
  /// (`TodayScreen.headerText`). Отданная в `children`, она уезжала под
  /// медальон — а медальон высотой 94 точки, — и вместо десяти точек между
  /// заголовком и фазой зияла половина экрана. Найдено сравнением кадров.
  final Widget? underTitle;

  /// Кегль заголовка. По умолчанию — заголовок экрана (29), как у каркаса на
  /// iOS; «Сегодня» просит главный (39) сам, потому что там строка — имя
  /// человека и единственный крупный элемент страницы.
  final TextStyle? titleStyle;

  final List<Widget> children;

  /// Надзаголовок, заголовок и строка под ним — одной колонкой: расстояния
  /// между ними принадлежат им, а не высоте соседнего медальона.
  Widget _headerColumn(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (eyebrow != null) ...[
          const SizedBox(height: 8),
          Text(eyebrow!.toUpperCase(), style: AlmaType.overline),
        ],
        if (title != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text(title!, style: titleStyle ?? AlmaType.displayL),
          ),
        if (underTitle != null) ...[
          const SizedBox(height: 6),
          underTitle!,
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final barHeight = AlmaMetrics.tabBarHeight + MediaQuery.paddingOf(context).bottom;

    Widget list = ListView(
      // **Страница не тянется в пустое небо.**
      //
      // С упругой физикой список уезжает за свой конец, и под ним открывается
      // голая ночь — экран читается как пустой, хотя всё на месте. Отскок
      // оставлен ровно там, где на нём держится жест: глава сообщает о
      // протяжке через `onOverscroll`, и её тянуть можно. Везде остальное
      // список упирается в край, как на нативе.
      // `AlwaysScrollable` там, где есть обновление жестом: иначе короткая
      // страница не даёт себя потянуть и обновить вовсе.
      physics: onOverscroll == null
          ? (onRefresh == null
              ? const ClampingScrollPhysics()
              : const AlwaysScrollableScrollPhysics(parent: ClampingScrollPhysics()))
          : const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
      padding: EdgeInsets.only(
        left: AlmaMetrics.pad,
        right: AlmaMetrics.pad,
        top: 12,
        // Полсекции над баром, а не целая: на скриншоте владельца под последней
        // строкой каждого экрана стояла полоса пустой ночи выше самого бара.
        bottom: AlmaMetrics.gapLarge / 2 + barHeight,
      ),
      children: [
        // Каскад прихода: шапка — ступень 0, каждый следующий блок на 70 мс
        // позже, подъёмом на 16 точек. Те же числа, что в Arrival.swift; вход
        // одноразовый — обновление данных не переигрывает его.
        RiseIn(
          index: 0,
          // **Медальон стоит рядом со всей шапкой, а не рядом с заголовком.**
          //
          // На нативе `header` — это `HStack { headerText; medallion }`, где
          // `headerText` держит и надзаголовок, и имя, и фазу. Здесь надзаголовок
          // сначала жил выше строки с медальоном, и печать съезжала вниз на его
          // высоту: рядом два кадра, и на порте луна висела заметно ниже.
          child: trailing == null
              ? _headerColumn(context)
              : Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: _headerColumn(context)),
                    const SizedBox(width: 12),
                    trailing!,
                  ],
                ),
        ),
        for (final (i, child) in children.indexed)
          RiseIn(index: i + 1, child: child),
      ],
    );

    if (onOverscroll != null) {
      list = NotificationListener<ScrollNotification>(
        onNotification: (notification) {
          final metrics = notification.metrics;
          // **Страница, которой нечего прокручивать, не имеет конца, за
          // который можно тянуть.** Без этой проверки глава, которая ещё
          // пишется — заголовок и рисунок, — докладывала отскок сверху как
          // протяжку снизу, и один смах переворачивал страницу, которую никто
          // не читал. iOS и Android несут ту же защиту.
          if (!metrics.hasContentDimensions || metrics.maxScrollExtent <= 0) {
            onOverscroll!(0);
            return false;
          }
          final past = metrics.pixels - metrics.maxScrollExtent;
          onOverscroll!(past > 0 ? past : 0);
          return false;
        },
        child: list,
      );
    }

    if (onRefresh != null) {
      list = RefreshIndicator(
        onRefresh: onRefresh!,
        color: AlmaPalette.gold,
        backgroundColor: AlmaPalette.night700,
        child: list,
      );
    }

    return NightSky(mood: mood, seed: seed, child: SafeArea(bottom: false, child: list));
  }
}
