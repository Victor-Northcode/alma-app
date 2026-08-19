import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../design/art.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
import '../onboarding/coach_anchors.dart';

/// Хаб: восемь систем одной колодой.
///
/// **Это полотно, а не список.** Заголовок, счётчик — и сразу восемь карт по
/// две в ряд, четыре ряда, все на одном экране без прокрутки. Разрезать их
/// заголовками разделов («кто я», «прямо сейчас», «в этом году») значило бы
/// вернуть список пунктов меню: полка, с которой берут, читается целиком и
/// сразу, а полка, разложенная по ящикам, читается по одному ящику за раз.
///
/// **Строки Солнца, Луны и Асцендента отсюда ушли.** Они занимали треть
/// экрана — ровно ту треть, в которой теперь стоят четыре карты. Это решение
/// владельца, а не оптимизация по месту; см. отчёт о том, где этим числам
/// теперь жить.
///
/// **Ни одна карта не молчит на тап** (`locked-chapter-spec.md`, §1 и §7, кадр
/// C5). Здесь стояло `onTap: ready ? … : null`, и три состояния из пяти —
/// «добавь человека», «нужно время рождения», «пока нет» — делали карту
/// картинкой. Дороже всех обходилась совместимость: подпись «add a person»
/// называла действие, которого нельзя было совершить, и самый сильный импульс
/// продукта кончался ничем ровно в ту секунду, когда до него дотронулись.
/// Теперь тап есть у всех восьми, а куда он ведёт, решает оболочка.
class SystemsScreen extends StatelessWidget {
  const SystemsScreen({super.key, required this.onOpenSystem});

  final void Function(SystemSlug slug) onOpenSystem;

  /// Порядок колоды. Задан макетом и не выводится из ответа сервера: хаб
  /// присылает слаг и состояние, а очерёдность карт — решение дизайна, и
  /// перестановка на сервере не должна тасовать колоду под рукой у человека.
  static const _order = <SystemSlug>[
    SystemSlug.natal,
    SystemSlug.birthCard,
    SystemSlug.solarReturn,
    SystemSlug.astrocartography,
    SystemSlug.numerology,
    SystemSlug.transits,
    SystemSlug.compatibility,
    SystemSlug.synthesis,
  ];

  /// Номер карты в колоде. Римскими — тем же способом, каким продукт нумерует
  /// шаги пути и главы системы.
  static const _roman = <String>['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'];

  /// Зазор между картами. Он же половина бокового поля: карта у края и карта у
  /// соседки должны отстоять одинаково, иначе полотно косит.
  static const _gap = 12.0;

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final l = L.of(context);
    final hub = session.hub;

    return ScreenScaffold(
      seed: 0x53595354,
      title: l.tabSystems,
      trailing: _tally(l, hub),
      children: hub == null ? const [] : _deck(context, l, session, hub),
    );
  }

  /// «8/8 рассчитано» — рядом с заголовком, засечным, как на iOS. Слово
  /// счётчика своё, не слово строки: в четырёх языках им нужны разные числа́ —
  /// calculés против calculé, — и одна строка на обе роли уже была ошибкой.
  Widget? _tally(L l, Hub? hub) {
    if (hub == null) return null;
    final ready = hub.systems.where((e) => CabinetWordsMore.isReady(e.status)).length;
    return Padding(
      // Ключ — якорь обучалки, и больше ничего: ни узла в дереве, ни точки в
      // разметке он не прибавляет. Счётчик подсвечивается первым шагом, потому
      // что он и есть доказательство того, что шаг говорит.
      key: CoachAnchors.systemsTally,
      padding: const EdgeInsets.only(top: 18),
      child: Text(
        '$ready/${hub.systems.length} ${l.cabCalculatedWord}',
        style: AlmaType.numeral,
      ),
    );
  }

  /// Колода: четыре ряда по две карты, в порядке [_order].
  ///
  /// Карт **всегда восемь**, даже если хаб прислал меньше: колода с дырой
  /// читается как поломка вёрстки, а система, о которой сервер промолчал,
  /// честнее выглядит приглушённой картой с состоянием «пока нет».
  List<Widget> _deck(BuildContext context, L l, AlmaSession session, Hub hub) {
    final height = _cardHeight(context);
    final entries = [
      for (final slug in _order)
        hub.systems.where((e) => e.slug == slug).firstOrNull ??
            HubEntry(slug: slug, unlocked: false, status: 'not-yet'),
    ];

    return [
      for (var i = 0; i < entries.length; i += 2)
        Padding(
          // Второй якорь обучалки — на первом ряду. Вместе со счётчиком он даёт
          // рамку на всю верхушку экрана: заголовок, «8/8 рассчитано» и первые
          // две карты колоды.
          key: i == 0 ? CoachAnchors.systemsFirstRow : null,
          padding: const EdgeInsets.only(top: _gap),
          child: Row(children: [
            Expanded(child: _card(l, session, entries[i], i, height)),
            const SizedBox(width: _gap),
            Expanded(child: _card(l, session, entries[i + 1], i + 1, height)),
          ]),
        ),
    ];
  }

  /// Высота карты, при которой все восемь помещаются на экран без прокрутки.
  ///
  /// **Пропорция карты — потолок, а не закон.** В дизайн-пакете карта 172×156;
  /// на кадре 402×874 это даёт 173×157, и четыре ряда садятся ровно на кромку
  /// бара вкладок — последний ряд оказывается под его растворяющимся краем.
  /// Поэтому берётся меньшее из двух: пропорции и той высоты, которая
  /// действительно осталась. На кадре 402×874 остаётся 154.25 — карта ниже
  /// эталонной на две с половиной точки, и это цена того, что колода видна
  /// целиком: измерено на симуляторе, нижний ряд кончается на 778 при кромке
  /// бара на 788.
  ///
  /// Считаем от окна, а не от окружения: `ScreenScaffold` уже съел верхний
  /// вырез своим `SafeArea`, а низ у оболочки объявлен `extendBody: true` — то
  /// есть окружение вернуло бы полную высоту бара, посчитанную ещё раз.
  double _cardHeight(BuildContext context) {
    final view = MediaQueryData.fromView(View.of(context));
    final width = (view.size.width - AlmaMetrics.pad * 2 - _gap) / 2;
    final ideal = width * 156 / 172;

    final free = view.size.height -
        view.padding.top -
        // Бар вкладок: своя высота плюс домашний индикатор. Содержимое уходит
        // под него, потому что он растворяется кверху, — но карта под ним уже
        // не видна, и на неё рассчитывать нельзя.
        (AlmaMetrics.tabBarHeight + view.padding.bottom) -
        ScreenScaffold.listTop -
        // Шапка. Не 36.5, как считается из кегля 29 и интерлиньяжа 1.12 плюс
        // нижние 4: измерено на кадре — верх первой карты стоит на 127, то
        // есть шапка занимает 41. Разницу даёт строчный ящик засечного шрифта,
        // и угадать её из чисел стиля нельзя.
        41 -
        _gap * 4 - // отступ первого ряда и три зазора между четырьмя рядами
        // Воздух под последней картой — **тот самый, который кладёт каркас**, а
        // не своё число рядом с ним. Здесь стояла восьмёрка, каркас клал 26, и
        // разница ровно этих точек делала колоду выше экрана: она ездила на
        // семь точек — «my systems дёргается, хотя там некуда листать».
        // Собственное число рядом с чужим всегда однажды разойдётся с ним;
        // теперь оно одно на двоих.
        ScreenScaffold.bottomAir;

    return math.min(ideal, free / 4);
  }

  /// Карта системы: арт, золотой кант, номер сверху, имя и обещание понизу.
  ///
  /// Закрытая система отличается не замком, а тишиной: картина приглушена, а
  /// вместо «рассчитано» стоит своё состояние — «нужно время рождения», «пока
  /// нет». Замок на витрине читается запретом, а здесь всё рассчитано и
  /// бесплатно — закрыт только текст.
  ///
  /// **Совместимость без человека не приглушается, а светится.** По кадру C5 у
  /// неё кант ярче остальных и мягкое сияние: это не «система, которой нет», а
  /// приглашение — единственная карта колоды, зовущая привести кого-то ещё.
  /// Приглушить её значило бы спрятать самый дорогой импульс продукта под тем
  /// же серым, каким помечено отсутствие данных.
  Widget _card(L l, AlmaSession session, HubEntry entry, int ordinal, double height) {
    final invite = _invites(session, entry);
    // Приглушение говорит «данных нет», а не «закрыто»: у приглашения данные и
    // не должны быть — за ними и зовут.
    final dim = !CabinetWordsMore.isReady(entry.status) && !invite;
    final card = SizedBox(
        height: height,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(13),
          child: Stack(fit: StackFit.expand, children: [
            Opacity(
              opacity: dim ? 0.45 : 1,
              child: Image.asset(AlmaArt.card(entry.slug), fit: BoxFit.cover),
            ),
            DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(13),
                border: Border.all(
                    color: invite
                        ? AlmaPalette.goldBright.withValues(alpha: 0.6)
                        : AlmaPalette.gold.withValues(alpha: 0.5)),
                // Имя стоит на своей земле: без затемнения книзу светлая
                // картина съедает подпись целиком.
                //
                // **Затемнение теперь и сверху.** На кадре римские I, II и III
                // пропали совсем: под ними золотое шитьё и светлая кожа, а
                // цифра сама золотая. Номер карты — не украшение, по нему
                // читают порядок колоды, поэтому у него своя земля, как у
                // имени. Нижняя половина градиента прежняя: от середины
                // прозрачной до 0xE6 у низа.
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Color(0xA6070A16),
                    Color(0x00070A16),
                    Color(0x00070A16),
                    Color(0xE6070A16),
                  ],
                  stops: [0, 0.28, 0.5, 1],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(11, 7, 11, 9),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Тень под цифрой, а не только затемнение под ней: у первой
                  // карты под номером золотое шитьё, и одного скрима не
                  // хватило — «I» на кадре читалась хуже остальных семи.
                  Text(
                    _roman[ordinal],
                    style: AlmaType.numeral.copyWith(
                      fontSize: 13,
                      shadows: const [
                        Shadow(color: Color(0xCC070A16), blurRadius: 5),
                      ],
                    ),
                  ),
                  const Spacer(),
                  Text(
                    CabinetWordsMore.system(l, entry.slug),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: AlmaType.headingM
                        .copyWith(fontSize: 16, color: AlmaPalette.starFill),
                  ),
                  const SizedBox(height: 2),
                  // Подпись стоит **всегда**, а не только у закрытой карты: она
                  // и есть то, что человек пришёл увидеть, и молчание на семи
                  // картах из восьми делало счётчик наверху единственным
                  // доказательством расчёта.
                  // Две строки, а не одна: по-английски «needs birth time»
                  // укладывается в ширину карты, а по-французски «heure de
                  // naissance manquante» — нет, и обрезанная причина не
                  // объясняет ничего. Место под вторую строку на карте есть.
                  Text(
                    _caption(l, session, entry),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: AlmaType.meta.copyWith(
                        fontSize: 11.5, color: _captionColor(session, entry)),
                  ),
                ],
              ),
            ),
          ]),
        ),
      );

    return GestureDetector(
      // **Тап есть у каждой карты, без единого исключения** (§7: «в My systems
      // нет ни одной карточки, которая не отвечает на тап»). Куда он ведёт —
      // дело оболочки: у совместимости без человека это ввод человека, у
      // остальных экран системы, который сам объяснит, чего ему не хватает.
      // Экран, объясняющий нехватку, — это ответ; карта, молчащая под пальцем,
      // — поломка.
      onTap: () => onOpenSystem(entry.slug),
      behavior: HitTestBehavior.opaque,
      child: invite
          // Сияние — снаружи `ClipRRect`: обрезка по скруглению срезала бы его
          // вместе с углами, и от приглашения остался бы один кант.
          ? DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(13),
                boxShadow: [
                  BoxShadow(
                      color: AlmaPalette.gold.withValues(alpha: 0.15),
                      blurRadius: 22),
                ],
              ),
              child: card,
            )
          : card,
    );
  }

  /// Карта зовёт привести человека: совместимость, у которой пары ещё нет.
  ///
  /// Считается по сохранённым людям, а не по слову хаба: `status` приезжает с
  /// сервера и запаздывает на один круг после добавления человека, а карта
  /// обязана перестать звать в ту же секунду, в которую человек появился.
  bool _invites(AlmaSession session, HubEntry entry) =>
      entry.slug == SystemSlug.compatibility && session.people.isEmpty;

  /// Подпись под именем системы — обещание, которое карта даёт на тап.
  ///
  /// Три формы, все из спеки (§1, §6):
  /// * «tap to add someone →» — совместимость без человека;
  /// * «N of M open» — там, где главы уже открыты (бесплатная или купленные);
  /// * «read the opening →» — там, где ещё не открыто ничего.
  ///
  /// **Нехватка данных остаётся названной.** «Нужно время рождения» и «пока
  /// нет» — не подписи бездействия, а причина, по которой у карты нет рисунка;
  /// заменить их на «прочитай начало» значило бы пообещать чтение, которое
  /// упрётся в тот же недостающий факт уже внутри. Карта при этом жива: тап
  /// ведёт на экран системы, где причина объяснена и есть, что с ней сделать.
  String _caption(L l, AlmaSession session, HubEntry entry) {
    if (_invites(session, entry)) return '${l.systemsTapToAdd} →';
    if (!CabinetWordsMore.isReady(entry.status)) {
      return CabinetWordsMore.status(l, entry.status);
    }
    final counted = _openChapters(session, entry);
    if (counted != null && counted.$1 > 0) {
      return l.systemsChaptersOpen(counted.$1, counted.$2);
    }
    return '${l.systemsReadOpening} →';
  }

  /// Цвета кадра C5: приглашение самое светлое, счёт открытых глав золотой,
  /// обещание чтения — обычная приглушённая подпись. Разница не декоративная:
  /// на полотне из восьми карт светлым выделено ровно одно место, куда стоит
  /// нажать первым.
  Color _captionColor(AlmaSession session, HubEntry entry) {
    if (_invites(session, entry)) return AlmaPalette.starFill;
    if (!CabinetWordsMore.isReady(entry.status)) return AlmaPalette.gold;
    final counted = _openChapters(session, entry);
    return counted != null && counted.$1 > 0
        ? AlmaPalette.gold
        : AlmaPalette.muted;
  }

  /// Сколько глав системы открыто и сколько их всего — или `null`, если этого
  /// пока никто не знает.
  ///
  /// **Считается по тому, что действительно привозили, а не по правилу в
  /// голове клиента.** Какая глава бесплатна, решает сервер (`free_chapters` в
  /// `chapters.py`), и вписать сюда «у натальной карты открыта первая» значило
  /// бы завести второй источник правды, который однажды разойдётся с первым и
  /// напечатает «1 из 16 открыта» там, где не открыто ничего. Поэтому счёт
  /// берётся из привезённого оглавления (память клиента), а пока оглавления не
  /// привозили — карта обещает начало, а не число.
  ///
  /// Купленная система — исключение, у которого свой источник: право открывает
  /// все главы разом, и спрашивать про это оглавление незачем.
  // TODO(hub): число открытых глав знает сервер, а спрашивают его здесь у
  // памяти клиента — значит, до первого входа в систему карта обещает начало
  // даже там, где бесплатная глава уже открыта. Это честно (лучше не назвать
  // числа, чем назвать неверное), но беднее кадра C5, где натал подписан «1 of
  // 16 open» с первого взгляда. Чинится одним полем в `/v1/systems/hub` рядом
  // со `status`; до тех пор упрощение сознательное.
  (int, int)? _openChapters(AlmaSession session, HubEntry entry) {
    final known =
        session.client.knownChapters(entry.slug, locale: session.locale);
    final total = known?.total ?? entry.slug.chapterCount;
    if (entry.unlocked || session.entitlements.opened(entry.slug)) {
      return (total, total);
    }
    if (known == null) return null;
    return (known.chapters.where((chapter) => chapter.open).length, total);
  }
}
