import 'dart:io';

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../billing/alma_store.dart';
import '../../billing/ladder.dart';
import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import 'pair_add_screen.dart';

/// V5 · «Мои пары»: каждый оплаченный отчёт и дорога к следующему.
///
/// Кадр `V5 My pairs` холста монетизации v3 (`SCREENS-V3.md` §V5). Экран
/// разовый: продаётся `pair.check` за $4.99, поэтому слов `renew` и абзаца
/// продления здесь нет. Единственная подписочная сущность — карточка кредита,
/// и она законна ровно с защитой `Beyond your monthly check` под ценой:
/// на смеси «включено в твой месяц» и «$4.99 навсегда» рождается жалоба
/// «думала, всё входит в подписку», названная в ТЗ красной линией.
///
/// **Список — из грантов** (`GET /pairs`), а не из истории магазина: Apple не
/// возвращает расходуемые покупки через restore, и «Мои пары» по StoreKit были
/// бы пусты после переустановки у человека, который заплатил за пять отчётов.
/// Люди, сохранённые в профилях, но ещё без отчёта, стоят в том же списке со
/// строкой про бесплатную первую главу — некликабельных строк здесь нет.
///
/// **Экран кончается человеком**, как и W2: тап по паре возвращает `Profile`
/// вызывающему (`Navigator.pop`), и экран системы перечитывает себя как W3
/// этой пары. Сам вести в главы он не вправе — оглавление и права знает экран
/// системы.
class MyPairsScreen extends StatefulWidget {
  const MyPairsScreen({super.key});

  @override
  State<MyPairsScreen> createState() => _MyPairsScreenState();
}

class _MyPairsScreenState extends State<MyPairsScreen> {
  List<PairReportRef>? _reports;
  PairCredit? _credit;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    // Цена на кнопке — только из магазина: в отладочной сборке полку
    // подставляет `_pretendPrices`, и хардкод здесь завёл бы вторую цену.
    if (AlmaStore.shared.state != StoreState.ready) AlmaStore.shared.load();
    _load();
  }

  Future<void> _load() async {
    final session = SessionScope.of(context);
    // Отказы порознь и молча: список пар без карточки кредита — полноценный
    // экран, а карточка без списка не значит ничего. Что не доехало, того
    // просто нет; старые люди из сессии стоят на экране в любом случае.
    try {
      final reports = await session.client.pairs();
      if (mounted) setState(() => _reports = reports);
    } on AlmaError {
      // Список остаётся собранным из сохранённых людей.
    }
    if (!session.isSubscriber) return;
    try {
      final credit = await session.client.pairCredits();
      if (mounted) setState(() => _credit = credit);
    } on AlmaError {
      // Кредит — свойство подписки; без ответа карточки просто нет.
    }
  }

  /// «12 авг» — короткая дата строки и карточки, локалью читателя.
  String _shortDate(L l, String iso) {
    final at = DateTime.tryParse(iso);
    return at == null ? '' : DateFormat.MMMd(l.localeName).format(at.toLocal());
  }

  Future<void> _checkAnother() async {
    final added = await Navigator.of(context).push<Profile>(
        CupertinoPageRoute(builder: (context) => const PairAddScreen()));
    if (added == null || !mounted) return;
    // Новый человек уходит тому, кто открыл «Мои пары»: экран системы
    // перечитает себя как W3 новой пары, и первая глава — в одном тапе.
    Navigator.of(context).pop(added);
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final session = SessionScope.of(context);
    final reports = _reports ?? const <PairReportRef>[];
    final byProfile = {for (final ref in reports) ref.profileId: ref};
    // Осиротевшие гранты — профиль удалён, отчёт оплачен (А7 №12): строка
    // остаётся, но вести ей некуда — расчёт против исчезнувшего рождения
    // отвечает 404. TODO(owner): дорога в такой отчёт не нарисована.
    final orphans = [
      for (final ref in reports)
        if (!session.people.any((p) => p.id == ref.profileId)) ref
    ];
    final credit = session.isSubscriber ? _credit : null;
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: NightSky(
        seed: 0x56355052,
        child: SafeArea(
          bottom: false,
          child: Column(children: [
            Expanded(
              child: ListView(
                physics: const ClampingScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(
                    AlmaMetrics.pad, 12, AlmaMetrics.pad, 16),
                children: [
                  Text(l.paywallV3PairMyPairsTitle, style: AlmaType.displayL),
                  const SizedBox(height: 8),
                  Text(l.pairMyPairsNote,
                      style: AlmaType.meta
                          .copyWith(height: 1.5, color: AlmaPalette.muted2)),
                  const SizedBox(height: 20),
                  for (final person in session.people)
                    _row(
                      l,
                      name: person.name?.isNotEmpty == true
                          ? person.name!
                          : l.scrPeopleUnnamed,
                      note: switch (byProfile[person.id]) {
                        // Подписчику открыты все четыре главы к любому
                        // человеку, пока подписка жива; всем остальным
                        // человек **заведён, но не прочитан**.
                        //
                        // Здесь стояла строка про бесплатную первую главу. Её
                        // сняло решение владельца 19.08.2026 — «мы не даем
                        // бесплатно пару никакую все за деньги можно писать
                        // только имя»: бесплатны расчёт и сама возможность
                        // завести человека, а любой написанный текст пары
                        // платный, и сервер для пары больше не пишет даже
                        // открывающий абзац. Обещать здесь чтение значило бы
                        // звать на экран, где чтения нет.
                        //
                        // Форма хвоста та же, что у остальных трёх веток
                        // («четыре главы · …»): раньше эта строка одна ломала
                        // грамматику списка и расходилась с вклейкой отчёта,
                        // где написано «four chapters».
                        null when session.isSubscriber =>
                          '${l.pairRowChapters} · ${l.paywallV3PairIncludedBadge}',
                        null => '${l.pairRowChapters} · ${l.pairRowNotOpened}',
                        final ref when ref.included =>
                          '${l.pairRowChapters} · ${l.paywallV3PairIncludedBadge}',
                        final ref =>
                          '${l.pairRowChapters} · ${l.pairRowBought(_shortDate(l, ref.purchasedAt))}',
                      },
                      sunSign: person.sunSign,
                      onTap: () => Navigator.of(context).pop(person),
                    ),
                  for (final ref in orphans)
                    _row(
                      l,
                      name: ref.name?.isNotEmpty == true
                          ? ref.name!
                          : l.scrPeopleUnnamed,
                      note: ref.included
                          ? '${l.pairRowChapters} · ${l.paywallV3PairIncludedBadge}'
                          : '${l.pairRowChapters} · ${l.pairRowBought(_shortDate(l, ref.purchasedAt))}',
                      onTap: null,
                    ),
                  if (credit != null && credit.granted > 0) ...[
                    const SizedBox(height: 20),
                    _creditCard(l, credit),
                  ],
                  const SizedBox(height: 18),
                  _hook(l, session),
                ],
              ),
            ),
            // Донный блок кадра: кнопка и подпись природы покупки. Цена
            // спрашивается у магазина на каждую перестройку — полка могла
            // доехать позже экрана.
            ListenableBuilder(
              listenable: AlmaStore.shared,
              builder: (context, _) {
                final price = AlmaStore.shared.price(LadderKey.pairCheck);
                // Кредит не потрачен — кнопка не имеет права обещать $4.99:
                // проверка этого месяца уже оплачена подпиской. Эталонной
                // фразы для этого состояния на холсте нет (§V5) — кнопка
                // говорит то же, но без цены, подпись — бейдж включённости.
                final free = credit != null && credit.remaining > 0;
                final label = free || price == null
                    ? l.pairCheckAnotherPlain
                    : l.paywallV3PairCheckAnother(price);
                // `Beyond your monthly check` стоит под ценой **всегда**,
                // когда цену видит подписчица, — включая ту, чей кредит не
                // доехал: без этой фразы и рождается «думала, всё входит в
                // подписку». Free-тарифу — природа покупки без слова о месяце.
                final note = free
                    ? l.paywallV3PairIncludedBadge
                    : session.isSubscriber
                        ? l.paywallV3PairBeyondCredit
                        : l.paywallV3PairForever;
                return Padding(
                  padding: EdgeInsets.fromLTRB(AlmaMetrics.pad, 0,
                      AlmaMetrics.pad, MediaQuery.paddingOf(context).bottom + 16),
                  child: Column(children: [
                    AlmaButton(label: label, onTap: _checkAnother),
                    const SizedBox(height: 10),
                    Text(
                      note,
                      textAlign: TextAlign.center,
                      style: AlmaType.meta.copyWith(
                          fontSize: 12.5,
                          height: 1.5,
                          color: AlmaPalette.body.withValues(alpha: 0.55)),
                    ),
                  ]),
                );
              },
            ),
          ]),
        ),
      ),
    );
  }

  /// Строка пары: аватар, имя, состояние, «→». Некликабельной остаётся только
  /// осиротевшая — и без стрелки: в этом продукте «→» значит «ведёт дальше».
  /// Глиф знака или `null`, если сервер промолчал либо назвал незнакомое.
  static String? _signGlyph(String? sign) => const {
        'Aries': '♈︎', 'Taurus': '♉︎', 'Gemini': '♊︎', 'Cancer': '♋︎',
        'Leo': '♌︎', 'Virgo': '♍︎', 'Libra': '♎︎', 'Scorpio': '♏︎',
        'Sagittarius': '♐︎', 'Capricorn': '♑︎', 'Aquarius': '♒︎',
        'Pisces': '♓︎',
      }[sign];

  Widget _row(L l,
      {required String name,
      required String note,
      String? sunSign,
      VoidCallback? onTap}) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
        ),
        child: Row(children: [
          Container(
            width: 44,
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                  color: AlmaPalette.gold.withValues(alpha: 0.45)),
            ),
            // Знак зодиака, как на холсте, — сервер считает его по дате и
            // отдаёт полем профиля. Знака нет (день перехода Солнца из знака
            // в знак, часа рождения не спрашивали) — стоит инициал: выдуманный
            // глиф был бы чужим знаком в кружке живого человека.
            //
            // Шрифт назван явно: без 'Apple Symbols' система отдаёт
            // астрологические знаки эмодзи-шрифту, и вместо золотого глифа
            // встаёт фиолетовая наклейка — уже ловили это на медальонах пары.
            child: Text(
              _signGlyph(sunSign) ??
                  (name.isEmpty ? '·' : name.characters.first.toUpperCase()),
              style: AlmaType.numeral.copyWith(
                fontSize: 17,
                color: AlmaPalette.goldBright,
                fontFamily: _signGlyph(sunSign) != null ? 'Apple Symbols' : null,
                fontFamilyFallback: _signGlyph(sunSign) != null
                    ? const ['Segoe UI Symbol', 'Noto Sans Symbols 2', 'serif']
                    : null,
              ),
            ),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AlmaType.headingM),
                const SizedBox(height: 3),
                Text(note,
                    style: AlmaType.meta.copyWith(
                        fontSize: 12.5, color: AlmaPalette.muted3)),
              ],
            ),
          ),
          if (onTap != null) ...[
            const SizedBox(width: 12),
            Icon(Icons.arrow_forward_rounded,
                size: 16,
                color: AlmaPalette.gold.withValues(alpha: 0.75)),
          ],
        ]),
      ),
    );
  }

  /// Карточка «this month» — единственная подписочная вещь экрана.
  Widget _creditCard(L l, PairCredit credit) {
    final next = credit.periodEnd == null
        ? null
        : l.pairCreditNext(_shortDate(l, credit.periodEnd!));
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 17, vertical: 16),
      decoration: BoxDecoration(
        // Числа кадра: кант золота на 0.3, заливка `night700` на 0.42.
        border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.3)),
        borderRadius: BorderRadius.circular(16),
        color: AlmaPalette.night700.withValues(alpha: 0.42),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(l.pairCreditOverline.toUpperCase(),
              style: AlmaType.readerHead.copyWith(
                  letterSpacing: 2, color: AlmaPalette.gold)),
          const SizedBox(width: 10),
          Expanded(
            child: Container(
              height: 1,
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [
                  AlmaPalette.gold.withValues(alpha: 0.35),
                  Colors.transparent,
                ]),
              ),
            ),
          ),
        ]),
        const SizedBox(height: 10),
        Text(l.pairCreditUsed(credit.used, credit.granted),
            style: AlmaType.headingM),
        if (next != null) ...[
          const SizedBox(height: 5),
          Text(next,
              style: AlmaType.meta.copyWith(
                  fontSize: 12.5,
                  height: 1.5,
                  color: AlmaPalette.body.withValues(alpha: 0.7))),
        ],
      ]),
    );
  }

  /// Вклейка-крючок «Anyone else on your mind?» — картина `plate-pull` с
  /// сервера, как все вклейки; не доехала — остаётся ночная плашка со
  /// скримом, подпись читается в любом случае.
  Widget _hook(L l, AlmaSession session) {
    return Container(
      height: 158,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.42)),
      ),
      child: Stack(fit: StackFit.expand, children: [
        FutureBuilder<File?>(
          future: session.plates.file('plate-pull'),
          builder: (context, plate) => plate.data == null
              ? const ColoredBox(color: AlmaPalette.night700)
              : Image.file(
                  plate.data!,
                  fit: BoxFit.cover,
                  // `object-position: center 30%` кадра: взгляд картины чуть
                  // выше середины.
                  alignment: const Alignment(0, -0.4),
                ),
        ),
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              stops: const [0.3, 1],
              colors: [
                AlmaPalette.night900.withValues(alpha: 0.05),
                AlmaPalette.night900.withValues(alpha: 0.88),
              ],
            ),
          ),
        ),
        // Внутренний штрих рамы — inset 5, радиус 12, как у всех вклеек v3.
        Padding(
          padding: const EdgeInsets.all(5),
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: AlmaPalette.starFill.withValues(alpha: 0.24)),
            ),
          ),
        ),
        Positioned(
          left: 16,
          right: 16,
          bottom: 13,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(l.pairHookTitle,
                style: AlmaType.headingM.copyWith(fontSize: 18, height: 1.2)),
            const SizedBox(height: 4),
            Text(l.pairHookNote,
                style: AlmaType.meta.copyWith(
                    fontSize: 12.5,
                    height: 1.45,
                    color: AlmaPalette.body.withValues(alpha: 0.78))),
          ]),
        ),
      ]),
    );
  }
}
