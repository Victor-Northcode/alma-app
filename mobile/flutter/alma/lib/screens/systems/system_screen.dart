import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
import 'natal_wheel.dart';
import 'people_screen.dart';
import 'system_art.dart';
import 'transit_ring.dart';
import 'writing_art.dart';

/// Одна система: её рисунок, её факты и её оглавление.
///
/// Порт `mobile/ios/Alma/Screens/Systems/SystemScreen.swift`, собранный в
/// порядке дизайн-проекта (s4, s19–s25): заголовок, рисунок системы, строки
/// фактов и сразу оглавление. Оглавление здесь главное: это дорога к главе.
///
/// **Факты выбирает макет, а не полнота выдачи.** У каждой системы напечатано
/// ровно то, чего её рисунок сказать не может: у карты рождения — стихия
/// (аркан и имя стоят на самой карте), у соляра — момент возвращения и
/// управитель года, у астрокартографии — место, число линий и число
/// пересечений. Нумерология и синтез не показывают строк вовсе: их числа
/// уже внутри рисунка, и второй раз печатать их значило бы повторяться.
class SystemScreen extends StatefulWidget {
  const SystemScreen({super.key, required this.system, required this.onOpenChapter});

  final SystemSlug system;
  final void Function(SystemSlug system, String chapter) onOpenChapter;

  @override
  State<SystemScreen> createState() => _SystemScreenState();
}

class _SystemScreenState extends State<SystemScreen> {
  ChapterList? _chapters;
  CalcResult? _result;
  AlmaError? _failure;

  /// Отказ **расчёта**, когда оглавление всё же пришло: совместимость без
  /// второго человека, соляр без времени рождения. Он объясняет, почему нет
  /// рисунка, и не отменяет глав.
  AlmaError? _computeFailure;

  /// Совместимость без второго человека — состояние, а не ошибка.
  bool _needsPartner = false;
  bool _loading = true;

  bool _started = false;

  // Не initState: `SessionScope.of` зависит от наследуемого виджета, а
  // зависеть от него в initState нельзя — исключение уходит в невозвращённое
  // будущее, и экран молча стоит на «Секунду» вечно. Найдено в браузере:
  // запрос глав просто не уходил в сеть.
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      _load();
    }
  }


  /// Карта отношений для колеса.
  ///
  /// Дэвисон несёт свои углы верхним уровнем, а колесо ждёт их под `angles`.
  /// Без обоих времён рождения Дэвисона нет, и остаётся `composite` — голые
  /// средние долготы, которым здесь выдаётся та же глифовая нотация, что
  /// движок печатает везде: это правописание, а не выдумывание.
  Map<String, dynamic>? _relationshipChart(Map<String, dynamic> data) {
    final davison = data['davison'];
    if (davison is Map && davison['placements'] is Map) {
      return {
        'placements': davison['placements'],
        'angles': {
          if (davison['ascendant'] != null) 'ascendant': davison['ascendant'],
          if (davison['midheaven'] != null) 'midheaven': davison['midheaven'],
        },
      };
    }
    final composite = data['composite'];
    if (composite is! Map) return null;
    const glyphs = {
      'sun': '☉', 'moon': '☽', 'mercury': '☿', 'venus': '♀', 'mars': '♂',
      'jupiter': '♃', 'saturn': '♄', 'uranus': '♅', 'neptune': '♆',
      'pluto': '♇', 'true_node': '☊', 'lilith': '⚸', 'chiron': '⚷',
    };
    final placements = <String, dynamic>{};
    composite.forEach((name, value) {
      final glyph = glyphs[name];
      if (glyph == null || value is! num) return;
      placements[name as String] = {'longitude': value.toDouble(), 'glyph': glyph};
    });
    return placements.isEmpty ? null : {'placements': placements};
  }

  /// Сколько человеку лет сегодня — для засечки на кольце нумерологии.
  /// Неизвестен, пока профиль не пришёл: тогда засечки просто нет.
  int? _age(BuildContext context) {
    final born = DateTime.tryParse(
        SessionScope.of(context).profile?.birthDate ?? '');
    if (born == null) return null;
    final now = DateTime.now();
    var years = now.year - born.year;
    if (now.month < born.month ||
        (now.month == born.month && now.day < born.day)) {
      years -= 1;
    }
    return years;
  }

  Future<void> _load() async {
    final session = SessionScope.of(context);
    setState(() {
      _loading = true;
      _failure = null;
      _computeFailure = null;
    });
    // Расчёт и оглавление одновременно: рисунок системы и её главы — две
    // независимые вещи, и ждать их по очереди значит удвоить пустой экран.
    //
    // **И падают они тоже порознь.** Раньше оба стояли в одном `Future.wait`
    // внутри одного `try`, а отказ расчёта — вещь совершенно обычная:
    // совместимость без второго человека, соляр и дома без времени рождения.
    // Одна такая ошибка забирала с собой и оглавление, и человек видел пустой
    // экран с сообщением вместо списка глав, которые прекрасно существуют и
    // читаются. Ошибка расчёта теперь остаётся ошибкой расчёта.
    final chapters = session.client
        .chapters(widget.system, locale: session.locale)
        .then<Object?>((value) => value)
        .catchError((Object error) => error);
    // **Совместимость считается против второго человека.**
    //
    // Сервер отвечает «compatibility needs a second person — send `other` or
    // `other_profile_id`», и порт эту строку показывал как есть: экран просил
    // какой-то id. Партнёр берётся из профилей аккаунта; когда его нет,
    // запрос не отправляется вовсе — просить нечего.
    final partner = widget.system == SystemSlug.compatibility
        ? session.people.firstOrNull
        : null;
    final needsPartner =
        widget.system == SystemSlug.compatibility && partner == null;
    final computed = needsPartner
        ? Future<Object?>.value(null)
        : session.client
            .compute(
              widget.system,
              body: partner == null ? const {} : {'other_profile_id': partner.id},
            )
        .then<Object?>((value) => value)
        .catchError((Object error) => error);
    final both = await Future.wait([chapters, computed]);
    if (!mounted) return;
    setState(() {
      if (both[0] case final ChapterList list) _chapters = list;
      if (both[1] case final CalcResult result) _result = result;
      // Экран целиком отказывает, только если не пришло вообще ничего.
      final failures = both.whereType<AlmaError>();
      _failure = _chapters == null && _result == null && failures.isNotEmpty
          ? failures.first
          : null;
      _computeFailure = both[1] is AlmaError ? both[1] as AlmaError : null;
      _needsPartner = needsPartner;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final facts = _facts(context, l);
    // Отбивка до оглавления — из макета: 26 точек после блока «добавьте
    // человека», 22 после строк фактов, и ни одной под самим рисунком — он
    // отбивает себя сам нижним полем. Без рисунка отбивка снова нужна.
    final gap = _needsPartner
        ? 26.0
        : facts.isNotEmpty
            ? 22.0
            : _result == null
                ? 10.0
                : 0.0;
    return ScreenScaffold(
      seed: 0x53595300 + widget.system.index,
      title: CabinetWordsMore.system(l, widget.system),
      onRefresh: _load,
      children: [
        // Рисунок системы, чертящий себя. Натальная и соляр — настоящее
        // колесо; у остальных своё полотно, по одному на систему.
        if (_wheelData case final chart?)
          Padding(
            padding: const EdgeInsets.only(top: 6, bottom: 10),
            child: NatalWheel(data: chart),
          )
        else if (_result?.data case final payload?)
          // По диаграмме на систему: каждая читает свой payload и рисует
          // только то, что в нём есть.
          Padding(
            padding: const EdgeInsets.only(top: 6, bottom: 10),
            child: switch (widget.system) {
              SystemSlug.transits => TransitYearRing(data: payload),
              SystemSlug.numerology => NumerologyRing(data: payload, age: _age(context)),
              SystemSlug.astrocartography => LinesMapArt(data: payload),
              // Имя аркана стоит на самой карте, как в макете: «XVII» и
              // «Звезда» — одна вещь, и разлучать их строкой ниже незачем.
              SystemSlug.birthCard =>
                BirthCardArt(data: payload, name: _arcanaName(l, payload)),
              SystemSlug.synthesis => SynthesisStar(data: payload),
              // Совместимость — это тоже карта: небо самих отношений.
              SystemSlug.compatibility => switch (_relationshipChart(payload)) {
                  final chart? => NatalWheel(data: chart),
                  _ => const SizedBox.shrink(),
                },
              _ => const SizedBox.shrink(),
            },
          ),
        if (_needsPartner) ...[
          // Колесо отношений рисовать не из чего, пока второго человека нет,
          // и выдумывать его нельзя. Но пустое небо над кнопкой читается как
          // недоделанный экран, поэтому здесь стоит рисунок, который ничего
          // не утверждает: две орбиты, которые ещё не встретились.
          // Зерно 0 — орбиты, а не решётка: у совместимости своё зерно даёт
          // сетку, и пустая сетка на экране «второго человека нет» читается
          // как пустая таблица. Здесь нужен рисунок, который ничего не
          // утверждает: две дуги, которые ещё не встретились.
          const Center(child: WritingArt(size: 220, seed: 0)),
          const SizedBox(height: 10),
          // По центру и в колонку шириной 300 — как в макете: это обещание
          // системы, а не примечание под рисунком.
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 300),
              child: Text(l.cabCompatNeedsPerson,
                  textAlign: TextAlign.center, style: AlmaType.meta),
            ),
          ),
          const SizedBox(height: 14),
          InkWell(
            onTap: () async {
              await Navigator.of(context).push(CupertinoPageRoute(
                  builder: (context) => const PeopleScreen()));
              if (mounted) _load();
            },
            child: Container(
              height: 54,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                border:
                    Border.all(color: AlmaPalette.gold.withValues(alpha: 0.55)),
                borderRadius: BorderRadius.circular(28),
              ),
              child: Text(L.of(context).cabPeopleAdd,
                  style: AlmaType.button.copyWith(color: AlmaPalette.goldBright)),
            ),
          ),
        ]
        else if (_computeFailure case final error?)
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 6),
            child: Text(
              error is ServerRefused && error.message.isNotEmpty
                  ? error.message
                  : l.stateUnavailable,
              style: AlmaType.meta,
            ),
          ),
        ...facts,
        SizedBox(height: gap),
        _section(
          l.cabChapters,
          trailing: _chapters?.total.toString(),
          children: [
            if (_loading)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 40),
                child: Center(
                    child: Text(l.stateLoadingShort, style: AlmaType.meta)),
              )
            else if (_failure != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Text(
                  _failure is ServerRefused &&
                          (_failure! as ServerRefused).message.isNotEmpty
                      ? (_failure! as ServerRefused).message
                      : l.stateUnavailable,
                  style: AlmaType.meta,
                ),
              )
            else if (_chapters != null)
              for (final entry in _chapters!.chapters) _row(l, entry),
          ],
        ),
      ],
    );
  }

  /// Данные для колеса. Натальная карта — она сама; соляр — карта возвращения:
  /// то же колесо, небо этого года.
  Map<String, dynamic>? get _wheelData {
    final data = _result?.data;
    if (data == null) return null;
    if (widget.system == SystemSlug.natal) return data;
    if (widget.system == SystemSlug.solarReturn) {
      final chart = data['chart'];
      return chart is Map ? chart.cast<String, dynamic>() : null;
    }
    return null;
  }

  /// Строки фактов между рисунком и оглавлением — у каждой системы свой
  /// состав, продиктованный макетом; почему именно такой, см. у класса.
  ///
  /// Ни одной выдуманной строки: подпись берётся из каталога, значение — из
  /// payload, и факт, которого в выдаче нет, просто не появляется. Это тот же
  /// закон, по которому рисунок не чертит штриха без данных.
  List<Widget> _facts(BuildContext context, L l) {
    final data = _result?.data;
    if (data == null) return const [];
    switch (widget.system) {
      case SystemSlug.birthCard:
        final card = data['personality'];
        final element = card is Map ? card['element'] as String? : null;
        final word = element == null ? null : _elementWord(l, element);
        return [if (word != null) _fact(l.cabFactElement, word)];

      case SystemSlug.solarReturn:
        // Момент возвращения приезжает мгновением в UTC, а печатается днём:
        // час без часового пояса — это час, который врёт на полсуток, и натив
        // отрезает его по той же причине.
        final at = DateTime.tryParse(data['return_at'] as String? ?? '');
        final ruler = data['year_ruler'] as String?;
        return [
          if (at != null)
            _fact(l.cabFactReturn,
                DateFormat.yMMMMd(l.localeName).format(at.toLocal())),
          if (ruler != null && ruler.isNotEmpty)
            _fact(l.cabFactYearRuler, CabinetWords.body(l, ruler.toLowerCase())),
        ];

      case SystemSlug.astrocartography:
        // Название места живёт в профиле, а не в расчёте: движок под ключом
        // `birthplace` держит прозу о линиях над этой точкой, а макет просит
        // здесь именно «Берлин, Германия».
        final place = SessionScope.of(context).profile?.placeLabel;
        final lines = (data['lines'] as List?)?.length ?? 0;
        final parans = (data['parans'] as List?)?.length ?? 0;
        return [
          if (place != null && place.isNotEmpty) _fact(l.cabFactBirthplace, place),
          if (lines > 0) _fact(l.cabFactLines, '$lines'),
          if (parans > 0) _fact(l.cabFactCrossings, '$parans'),
        ];

      case SystemSlug.transits:
        return _activeNow(l);

      default:
        return const [];
    }
  }

  /// «стихия — воздух»: подпись слева строчными, значение справа засечным.
  Widget _fact(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Доля 4/6, как во всех парах «подпись — значение» продукта: место
          // рождения бывает длиннее своей половины.
          Expanded(flex: 4, child: Text(label, style: AlmaType.meta)),
          const SizedBox(width: 12),
          Expanded(
            flex: 6,
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: AlmaType.numeral.copyWith(fontSize: 17),
            ),
          ),
        ],
      ),
    );
  }

  /// «Сейчас активно» — контакты, уже стоящие в орбе, с датой точности.
  ///
  /// У транзитов рисунок показывает дуги, но не называет их; макет ставит под
  /// кольцом именно этот список. Напряжённый аспект берёт красный — тот же,
  /// которым его дуга нарисована выше, чтобы строка и дуга читались как одно.
  List<Widget> _activeNow(L l) {
    final rows = ((_result?.data['active'] as List?) ?? const [])
        .whereType<Map>()
        .take(5)
        .toList();
    return [
      _section(
        l.cabActiveNow,
        children: [
          if (rows.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 13),
              child: Text(l.cabNoneActive, style: AlmaType.meta),
            )
          else
            for (final row in rows) _contact(l, row),
        ],
      ),
    ];
  }

  Widget _contact(L l, Map<dynamic, dynamic> row) {
    final aspect = row['aspect'] as String? ?? '';
    final tense = aspect == 'square' || aspect == 'opposition';
    final exact = DateTime.tryParse(row['exact'] as String? ?? '');
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 13),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              CabinetWords.contact(
                l,
                transiting: row['transiting'] as String? ?? '',
                aspect: aspect,
                natal: row['natal'] as String? ?? '',
              ),
              style: AlmaType.meta,
            ),
          ),
          if (exact != null) ...[
            const SizedBox(width: 12),
            Text(
              DateFormat.MMMd(l.localeName).format(exact.toLocal()),
              style: tense
                  ? AlmaType.numeral.copyWith(color: AlmaPalette.disagree)
                  : AlmaType.numeral,
            ),
          ],
        ],
      ),
    );
  }

  /// Имя аркана на языке читателя. Движок называет карту по-английски — это
  /// идентификатор, — а на карту выходит слово из каталога.
  String? _arcanaName(L l, Map<String, dynamic> data) {
    final card = data['personality'];
    final name = card is Map ? card['name'] as String? : null;
    return switch (name) {
      'Death' => l.cabArcanaDeath,
      'Judgement' => l.cabArcanaJudgement,
      'Justice' => l.cabArcanaJustice,
      'Strength' => l.cabArcanaStrength,
      'Temperance' => l.cabArcanaTemperance,
      'The Chariot' => l.cabArcanaTheChariot,
      'The Devil' => l.cabArcanaTheDevil,
      'The Emperor' => l.cabArcanaTheEmperor,
      'The Empress' => l.cabArcanaTheEmpress,
      'The Fool' => l.cabArcanaTheFool,
      'The Hanged Man' => l.cabArcanaTheHangedMan,
      'The Hermit' => l.cabArcanaTheHermit,
      'The Hierophant' => l.cabArcanaTheHierophant,
      'The High Priestess' => l.cabArcanaTheHighPriestess,
      'The Lovers' => l.cabArcanaTheLovers,
      'The Magician' => l.cabArcanaTheMagician,
      'The Moon' => l.cabArcanaTheMoon,
      'The Star' => l.cabArcanaTheStar,
      'The Sun' => l.cabArcanaTheSun,
      'The Tower' => l.cabArcanaTheTower,
      'The World' => l.cabArcanaTheWorld,
      'Wheel of Fortune' => l.cabArcanaWheelOfFortune,
      // Незнакомая карта печатается собственным именем движка, а не пропадает:
      // тот же договор, что у имён планет в `CabinetWords`.
      _ => name,
    };
  }

  String? _elementWord(L l, String element) => switch (element.toLowerCase()) {
        'air' => l.cabElementAir,
        'earth' => l.cabElementEarth,
        'fire' => l.cabElementFire,
        'water' => l.cabElementWater,
        _ => element,
      };

  Widget _section(String label, {String? trailing, required List<Widget> children}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Text(label.toUpperCase(), style: AlmaType.overline),
          const SizedBox(width: 12),
          Expanded(
            child: Container(
              height: 1,
              decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 12),
            Text(trailing, style: AlmaType.numeral),
          ],
        ]),
        ...children,
      ],
    );
  }

  /// Одна глава: римская цифра засечным, заголовок, вопрос — и ничего про
  /// замок. Закрытая глава честно скажет это внутри, показав заголовок, вопрос
  /// и дверь; прятать её из списка значило бы прятать сам продукт.
  Widget _row(L l, ChapterEntry entry) {
    return InkWell(
      onTap: () => widget.onOpenChapter(widget.system, entry.slug),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 44,
              child: Padding(
                padding: const EdgeInsets.only(top: 3),
                child: Text(entry.numeral, style: AlmaType.numeral),
              ),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(entry.title, style: AlmaType.headingM),
                  if (entry.question.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(entry.question, style: AlmaType.meta),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
