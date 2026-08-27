import 'dart:io';

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../design/close_button.dart';
import '../../design/layout.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/reading_tally.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
import 'my_pairs_screen.dart';
import 'natal_wheel.dart';
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
/// ровно то, чего её рисунок сказать не может: у натальной карты — Солнце,
/// Луна и Асцендент, у карты рождения — стихия (аркан и имя стоят на самой
/// карте), у соляра — момент возвращения и управитель года, у
/// астрокартографии — место, число линий и число пересечений. Нумерология и
/// синтез не показывают строк вовсе: их числа уже внутри рисунка, и второй раз
/// печатать их значило бы повторяться.
class SystemScreen extends StatefulWidget {
  const SystemScreen({
    super.key,
    required this.system,
    required this.onOpenChapter,
    this.partner,
  });

  final SystemSlug system;

  /// [partner] — кого сравнивать, когда система про пару. Дальше он уходит и в
  /// расчёт колеса, и в главу: рисунок над оглавлением и текст под ним обязаны
  /// быть про одну и ту же пару, иначе экран показывает одно небо, а читает
  /// другое.
  final void Function(SystemSlug system, String chapter, {Profile? partner})
      onOpenChapter;

  /// С кем сравнивать. `null` — «не сказано», и тогда берётся первый
  /// сохранённый: ровно то же правило, по которому выбирает сервер, пока
  /// человек один.
  final Profile? partner;

  @override
  State<SystemScreen> createState() => _SystemScreenState();
}

class _SystemScreenState extends State<SystemScreen> {
  /// Пара этого экрана. Меняется по «Change» — и тогда пересчитывается всё:
  /// колесо, факты и главы, в которые отсюда уходят.
  Profile? _partner;
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

  /* ── только у пары (кадр W3) ────────────────────────────────────────────
     Шапке кадра нужны знаки Солнца обоих — «Pisces and Leo», — а расчёт
     совместимости их не отдаёт: там контакты, наложения и композит, но не
     сами карты двоих. Два натальных расчёта дешевле, чем кажется: сервер
     кэширует их по рождению, и для читателя это тот же ответ, что рисует его
     собственное колесо.                                                     */

  /// Знак Солнца читателя и партнёра — имена движка («Pisces»), на экран
  /// выходят словом каталога. `null` — расчёт не доехал, и шапка честно
  /// показывает имена вместо знаков, а не выдумывает.
  String? _mySign, _theirSign;

  /// Слаги прочитанных глав этой пары — метки «read» в оглавлении.
  Set<String> _read = const {};

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


  /// Кого сравнивать на этом экране — и только у совместимости.
  ///
  /// Порядок: выбранный руками, потом названный снаружи, потом первый
  /// сохранённый. Человек, которого больше нет — его могли удалить на экране
  /// людей, пока эта страница висела в стеке, — пропускается: расчёт против
  /// исчезнувшего профиля отвечает 404, и экран показывал бы отказ там, где
  /// достаточно взять того, кто остался.
  Profile? _pickPartner(AlmaSession session) {
    if (widget.system != SystemSlug.compatibility) return null;
    for (final candidate in [_partner, widget.partner]) {
      if (candidate == null) continue;
      for (final person in session.people) {
        if (person.id == candidate.id) return person;
      }
    }
    return session.people.firstOrNull;
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
    //
    // **Названный побеждает первого сохранённого.** Первый — это догадка, и
    // она верна ровно до второго человека: с двумя людьми в аккаунте догадка
    // экрана и догадка сервера — разные вещи, и тот, кто пришёл сюда за
    // конкретной парой, читал бы чужую.
    final partner = _pickPartner(session);
    _partner = partner;
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
    // Довесок пары: два знака Солнца для шапки W3 и пометки «прочитано» для
    // оглавления. Падают молча и порознь — шапка без знаков переживёт, а вот
    // оглавление без глав нет, поэтому эти отказы не смешиваются с общими.
    final isPair = widget.system == SystemSlug.compatibility && partner != null;
    final mine = isPair
        ? session.client
            .compute(SystemSlug.natal)
            .then<Object?>((value) => value)
            .catchError((Object error) => error)
        : Future<Object?>.value(null);
    final theirs = isPair
        ? session.client
            .compute(SystemSlug.natal, body: {'profile_id': partner.id})
            .then<Object?>((value) => value)
            .catchError((Object error) => error)
        : Future<Object?>.value(null);
    final read = isPair
        ? ReadingTally.readChapters(SystemSlug.compatibility, partner.id)
        : Future.value(const <String>{});
    final both = await Future.wait([chapters, computed, mine, theirs, read]);
    if (!mounted) return;
    setState(() {
      if (both[0] case final ChapterList list) _chapters = list;
      if (both[1] case final CalcResult result) _result = result;
      // Экран целиком отказывает, только если не пришло вообще ничего.
      final failures = both.take(2).whereType<AlmaError>();
      _failure = _chapters == null && _result == null && failures.isNotEmpty
          ? failures.first
          : null;
      _computeFailure = both[1] is AlmaError ? both[1] as AlmaError : null;
      _mySign = both[2] is CalcResult
          ? (both[2] as CalcResult).data['sun_sign'] as String?
          : null;
      _theirSign = both[3] is CalcResult
          ? (both[3] as CalcResult).data['sun_sign'] as String?
          : null;
      _read = both[4] as Set<String>? ?? const {};
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
            // Заготовка колеса отбивает себя сама нижним полем, как и готовый
            // рисунок; отбивка нужна только там, где над оглавлением пусто.
            : _result == null && !_loading
                ? 10.0
                : 0.0;
    // Кадр W3: у пары с названным партнёром экран собирается иначе —
    // шапка-оверлайн вместо заголовка системы, вклейка со знаками, оглавление
    // с метками «read» и мета-строкой «read from» внизу. Всё остальное —
    // прежний экран системы.
    final pair = widget.system == SystemSlug.compatibility &&
        !_needsPartner &&
        _partner != null;
    return ScreenScaffold(
      seed: 0x53595300 + widget.system.index,
      // Титул кадра W3 живёт на вклейке («Pisces and Leo»), а не над списком:
      // второй заголовок сверху делал бы экран пары непохожим на кадр.
      title: pair ? null : CabinetWordsMore.system(l, widget.system),
      // Единый крестик — и на экране системы: отсюда не было ни стрелки, ни
      // крестика, и человек внутри натальной карты не имел явного «назад»
      // (владелец, 25.08.2026). У пары своя шапка со стрелкой — ей второй
      // выход не нужен.
      trailing: pair
          ? null
          : AlmaClose(onTap: () => Navigator.of(context).maybePop()),
      onRefresh: _load,
      children: [
        if (pair) ...[
          _pairHeader(l),
          const SizedBox(height: 18),
          _pairPlate(context, l),
          _partnerLine(context, l, _partner!),
          if (_computeFailure case final error?)
            Padding(
              padding: const EdgeInsets.only(top: 4, bottom: 6),
              child: Text(
                error is ServerRefused && error.message.isNotEmpty
                    ? error.message
                    : l.stateUnavailable,
                style: AlmaType.meta,
              ),
            ),
          // Колесо остаётся — небо самих отношений; на кадре его нет, но
          // решение владельца прямое: «колесо остаётся». Стоит под вклейкой,
          // чтобы шапка кадра осталась шапкой.
          if (_result?.data case final payload?)
            Padding(
              padding: const EdgeInsets.only(top: 12, bottom: 10),
              child: switch (_relationshipChart(payload)) {
                final chart? => NatalWheel(data: chart),
                _ => const SizedBox.shrink(),
              },
            )
          else if (_loading)
            const Padding(
              padding: EdgeInsets.only(top: 12, bottom: 10),
              child: Center(child: ChartPlaceholder()),
            ),
        ]
        else if (_wheelData case final chart?)
          // Рисунок системы, чертящий себя. Натальная и соляр — настоящее
          // колесо; у остальных своё полотно, по одному на систему.
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
              _ => const SizedBox.shrink(),
            },
          )
        else if (_loading)
          // **Пока система считается, на её месте стоит колесо, а не дыра.**
          // Экран открывался пустым небом с одной строкой «минуту» внизу —
          // ровно тот случай, о котором сказано «эти экраны мы вообще не
          // сделали». В макете (s28) здесь кольцо в масштабе будущего
          // рисунка, и золотая дуга по нему пишется и стирается: видно, что
          // работа идёт. Позиций оно не показывает — их ещё нет, и выдумывать
          // их нельзя.
          const Padding(
            padding: EdgeInsets.only(top: 6, bottom: 10),
            child: Center(child: ChartPlaceholder()),
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
          // Титул над обещанием. Без него экран начинался с оправдания —
          // «нужен второй человек», — и читался поломкой. С ним он говорит,
          // что здесь будет, и приглашение стоит под обещанием, а не вместо.
          Center(
            child: Text(
              l.cabCompatTwoSkies,
              textAlign: TextAlign.center,
              style: AlmaType.displayL.copyWith(fontSize: 22, height: 1.2),
            ),
          ),
          const SizedBox(height: 8),
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
            onTap: _changePartner,
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
          const SizedBox(height: 16),
          // Три пункта — под кнопкой, а не над ней, и это порядок с холста:
          // человек уже согласился или уже отказался к моменту, когда читает
          // подробности, и подробности не должны стоять у него на пути.
          _compatBullet(l.cabCompatBulletContacts),
          const SizedBox(height: 7),
          _compatBullet(l.cabCompatBulletHouses),
          const SizedBox(height: 7),
          _compatBullet(l.cabCompatBulletComposite),
        ]
        else if (!pair) ...[
          // Отказ расчёта у пары уже напечатан в её собственной ветке выше —
          // здесь он остаётся для всех прочих систем.
          if (_computeFailure case final error?)
            Padding(
              padding: const EdgeInsets.only(top: 4, bottom: 6),
              child: Text(
                error is ServerRefused && error.message.isNotEmpty
                    ? error.message
                    : l.stateUnavailable,
                style: AlmaType.meta,
              ),
            ),
        ],
        ...facts,
        SizedBox(height: gap),
        _section(
          l.cabChapters,
          trailing: _chapters?.total.toString(),
          children: [
            if (_loading) ...[
              // «Минуту» стоит там же, где в макете: сразу под линейкой
              // раздела, по центру, с отбивкой 10 сверху и 6 снизу — а под
              // ней три заготовки строк оглавления. Одна фраза посреди
              // сорока точек пустоты не говорила, что грузится именно
              // оглавление; три строки на своих местах говорят.
              Padding(
                padding: const EdgeInsets.only(top: 10, bottom: 6),
                child: Center(
                    child: Text(l.stateLoadingShort, style: AlmaType.meta)),
              ),
              for (var i = 0; i < 3; i++) _waitingRow(i),
            ]
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
        // Мета-строка «read from» кадра W3: первая позиция, из которой пара
        // прочитана, и счётчик остальных. На холсте она донная и абсолютная;
        // в прокручиваемой колонке абсолютного низа нет — стоит последней
        // строкой, той же конструкцией, что на V1 и V4 (`meta-line-spec.md`).
        if (pair && (_result?.factors.isNotEmpty ?? false)) ...[
          const SizedBox(height: 20),
          _readFromLine(l, _result!.factors),
        ],
      ],
    );
  }

  /// Шапка кадра W3: «←», оверлайн «you and marcus» по центру, распорка той
  /// же ширины — центр обязан быть настоящим центром строки.
  Widget _pairHeader(L l) {
    // **Без имени шапка называет раздел, а не человека.**
    //
    // Имя партнёра необязательно, и подстановка сюда общей заглушки давала
    // «YOU AND UNNAMED» — приложение обращалось к человеку словом «без имени».
    // Заглушка законна строкой списка, где она стоит рядом с датой и читается
    // пометой; в обращении она читается грубостью. Нет имени — нет и
    // обращения: остаётся тот же оверлайн раздела, что и на вводе партнёра.
    final theirs = _partner?.name;
    if (theirs == null || theirs.isEmpty) {
      return _plainHeader(l.scrPeopleEyebrow.toUpperCase());
    }
    return _plainHeader(l.pairReportHeader(theirs).toUpperCase());
  }

  /// Шапка кадра с готовой строкой: «←», надпись по центру, распорка той же
  /// ширины — центр обязан быть настоящим центром строки.
  Widget _plainHeader(String title) {
    return Row(children: [
      // «Назад» внутри стека систем — единый кружок со стрелкой слева
      // (правило 24 авг, см. AlmaClose): текстовая «←» 18pt была мелкой.
      AlmaClose(back: true, onTap: () => Navigator.of(context).maybePop()),
      Expanded(
        child: Text(
          title,
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AlmaType.readerHead.copyWith(color: AlmaPalette.gold),
        ),
      ),
      const SizedBox(width: 44),
    ]);
  }

  /// Вклейка пары: `plate-tender` с сервера, знаки обоих титулом и — только у
  /// купленного отчёта — строка «four chapters · yours forever».
  ///
  /// **«yours forever» — подтверждение, а не оффер** (правило 3: внутри
  /// оплаченного ноль коммерции), поэтому строка стоит ровно тогда, когда
  /// доступ уже выдан (`access.allowed`), и никогда — как обещание.
  /// Знаки берутся из двух натальных расчётов; пока их нет, титулом стоят
  /// имена пары — честный недострой вместо выдуманного знака.
  Widget _pairPlate(BuildContext context, L l) {
    final session = SessionScope.of(context);
    final mySign = _mySign, theirSign = _theirSign;
    final title = mySign != null && theirSign != null
        ? l.cabPairJoin(
            CabinetWordsMore.sign(l, mySign), CabinetWordsMore.sign(l, theirSign))
        : (() {
            final mine = session.profile?.name;
            final theirs = _partner?.name?.isNotEmpty == true
                ? _partner!.name!
                : l.scrPeopleUnnamed;
            return mine == null || mine.isEmpty
                ? theirs
                : l.cabPairJoin(mine, theirs);
          })();
    final bought = _result?.access.allowed == true;
    return Container(
      height: 170,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.45)),
      ),
      child: Stack(fit: StackFit.expand, children: [
        FutureBuilder<File?>(
          future: session.plates.file('plate-tender'),
          builder: (context, plate) => plate.data == null
              ? const ColoredBox(color: AlmaPalette.night700)
              : Image.file(
                  plate.data!,
                  fit: BoxFit.cover,
                  // `object-position: center 30%` кадра.
                  alignment: const Alignment(0, -0.4),
                ),
        ),
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              stops: const [0.35, 1],
              colors: [
                AlmaPalette.night900.withValues(alpha: 0.05),
                AlmaPalette.night900.withValues(alpha: 0.88),
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(5),
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                  color: AlmaPalette.starFill.withValues(alpha: 0.26)),
            ),
          ),
        ),
        Positioned(
          left: 16,
          right: 16,
          bottom: 13,
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AlmaType.displayL.copyWith(fontSize: 22, height: 1.14)),
            if (bought) ...[
              const SizedBox(height: 3),
              Text(l.pairReportMeta,
                  style: AlmaType.meta
                      .copyWith(fontSize: 12, color: AlmaPalette.gold)),
            ],
          ]),
        ),
      ]),
    );
  }

  /// Мета-строка «read from»: оверлайн, первая позиция, «+N». Режется только
  /// хвост дома (`AlmaShrink.fitMetaLine`) — тело, градус и знак неделимы.
  Widget _readFromLine(L l, List<String> factors) {
    final rest = factors.length - 1;
    final style = AlmaType.numeral
        .copyWith(fontFamilyFallback: AlmaType.glyphFallback);
    return Row(children: [
      Text(l.cabReadFrom.toUpperCase(), style: AlmaType.readingPart),
      const SizedBox(width: 11),
      Expanded(
        child: LayoutBuilder(
          builder: (context, box) => Text(
            AlmaShrink.fitMetaLine(
              line: CabinetWordsMore.factor(l, factors.first),
              // Стилем, которым рисуется, — см. `AlmaShrink.drawn`.
              style: AlmaShrink.drawn(context, style),
              maxWidth: box.maxWidth,
              scaler: MediaQuery.textScalerOf(context),
            ),
            // Голосу — полная строка с именем знака: у неё нет ширины.
            semanticsLabel: CabinetWordsMore.factorSpoken(l, factors.first),
            style: style,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ),
      if (rest > 0) ...[
        const SizedBox(width: 8),
        Text('+$rest',
            style: AlmaType.numeral
                .copyWith(color: AlmaPalette.gold.withValues(alpha: 0.7))),
      ],
    ]);
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
      case SystemSlug.natal:
        return _positions(l, data);

      case SystemSlug.birthCard:
        final card = data['personality'];
        final element = card is Map ? card['element'] as String? : null;
        final word = element == null ? null : _elementWord(l, element);
        return [if (word != null) _fact(l.cabFactElement, word)];

      case SystemSlug.solarReturn:
        final at = DateTime.tryParse(data['return_at'] as String? ?? '');
        final ruler = data['year_ruler'] as String?;
        return [
          if (at != null) _fact(l.cabFactReturn, _returnMoment(l, at, data)),
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

  /// Три строки под колесом натальной карты: Солнце, Луна, Асцендент.
  ///
  /// **Это те строки, которые делают колесо «моим» до первого тапа.** Колесо
  /// без них — красивая диаграмма чьей-то карты: глифы на нём не подписаны, и
  /// узнать в ней себя нельзя, пока не назван хотя бы один знак. Раньше они
  /// стояли на экране «Мои системы» (в макете — s3, три строки над списком);
  /// когда тот экран стал колодой, строки ушли вместе с ним, и вернуть их
  /// нужно сюда, под сам рисунок, — колода остаётся навигацией, а чтение
  /// начинается здесь.
  ///
  /// Числа и знак — ровно те, что напечатал движок (`formatted`): этот экран
  /// не второе мнение о позиции. Знак остаётся глифом, как в макете; имя
  /// знака уходит в подпись для VoiceOver.
  ///
  /// Асцендент — не тело, а угол: он живёт в `angles`, дома у него нет по
  /// определению, и **без времени рождения его нет вовсе** — горизонта не
  /// существует. Тогда строки просто нет; выдумывать её полуднем значило бы
  /// напечатать ошибку до 180° тем же уверенным тоном, что и правду.
  List<Widget> _positions(L l, Map<String, dynamic> data) {
    final placements = data['placements'];
    final rows = <Widget>[];
    for (final key in const ['sun', 'moon']) {
      final placement = placements is Map ? placements[key] : null;
      if (placement is! Map) continue;
      final formatted = placement['formatted'] as String?;
      if (formatted == null || formatted.isEmpty) continue;
      final house = (placement['house'] as num?)?.toInt();
      // Дом есть только там, где есть дома: без времени рождения `house`
      // приходит пустым, и строка честно кончается знаком.
      final tail = house == null ? '' : ' · ${CabinetWordsMore.house(l, house)}';
      rows.add(_fact(CabinetWords.body(l, key), '$formatted$tail', glyphs: true));
    }
    final angles = data['angles'];
    final formatted = angles is Map ? angles['formatted'] : null;
    final ascendant =
        formatted is Map ? formatted['ascendant'] as String? : null;
    if (ascendant != null && ascendant.isNotEmpty) {
      rows.add(_fact(CabinetWords.body(l, 'ascendant'), ascendant, glyphs: true));
    }
    return rows;
  }

  /// Момент возвращения Солнца — по часам того места, для которого построен
  /// соляр.
  ///
  /// `return_at` — мгновение в UTC, и это всё, что о нём знает движок: Солнце
  /// возвращается одновременно для всех, а часа и дня у мгновения нет, пока не
  /// названы чьи-то часы. Обе половины врут по-своему. Напечатать UTC-час
  /// местным — ошибка до полусуток. Взять из UTC один только день — ошибка на
  /// сутки: возвращение в 01:21 UTC 11 мая в Сан-Паулу это ещё 10 мая, и эта
  /// ложь тише первой, оттого и живёт дольше.
  ///
  /// Чинит обе зона: бэкенд кладёт рядом с мгновением имя зоны места
  /// (`return_tz`) и её смещение **в этот момент** (`return_offset_minutes`).
  /// Смещение приезжает готовым, потому что базы часовых поясов во Flutter
  /// нет, а вывести его из зоны устройства значит вернуться к той же лжи —
  /// человек в Берлине читал бы соляр, построенный для Сан-Паулу, по берлинским
  /// часам. Тем же доводом сервер присылает имена часов на развилке перевода
  /// времени.
  ///
  /// Полей может не быть — сервер старше этой строки, или соляр перенесён в
  /// точку, чью зону назвать некому. Тогда печатается один день, как печатал
  /// натив: это статус-кво, а не потеря.
  String _returnMoment(L l, DateTime at, Map<String, dynamic> data) {
    final zone = data['return_tz'];
    final offset = data['return_offset_minutes'];
    if (zone is! String || zone.isEmpty || offset is! num) {
      return DateFormat.yMMMMd(l.localeName).format(at.toLocal());
    }
    // Стенные часы места: мгновение в UTC, сдвинутое на смещение зоны.
    // `DateFormat` печатает поля того `DateTime`, который ему дали, и никуда
    // их больше не переводит, — поэтому сдвинутое значение и есть то, что
    // должно оказаться на экране.
    final local = at.toUtc().add(Duration(minutes: offset.round()));
    // День — тем же форматом, что и раньше; час — `j`, то есть в том виде,
    // в каком его пишет локаль: 04:12 там, где сутки идут по 24 часа, и
    // 4:12 AM там, где по 12. Руками этот выбор не делается.
    return '${DateFormat.yMMMMd(l.localeName).format(local)}'
        ' · ${DateFormat.jm(l.localeName).format(local)}';
  }

  /// Позвать человека — и вернуться с ним, а не просто «сходить на экран
  /// людей».
  ///
  /// **Строка пары ведёт в «Мои пары» (V5), и экран выбора отдаёт того, на
  /// ком остановились.** Раньше здесь открывался список людей; теперь у пар
  /// есть собственный экран с состоянием каждого отчёта («куплено 12 авг»,
  /// «входит в твой месяц») и дорогой к новому человеку. Контракт тот же:
  /// `pop(Profile)` — и названный человек уходит и в расчёт, и в главы,
  /// открытые с этой страницы. Управление списком (удаление) остаётся на
  /// экране людей — V5 не удаляет никого.
  Future<void> _changePartner() async {
    final chosen = await Navigator.of(context).push<Profile>(
        CupertinoPageRoute(builder: (context) => const MyPairsScreen()));
    if (!mounted) return;
    // Ушли ни с кем — экран всё равно перечитывается: там могли добавить
    // человека, против которого ещё не считали.
    if (chosen != null) _partner = chosen;
    _load();
  }

  /// Строка «с кем считаем» и слово «Изменить» справа.
  ///
  /// Собственное имя читателя ставится первым, когда оно известно, — «Аня и
  /// Маркус» — той же строкой каталога, которой пара названа везде
  /// (`cabPairJoin`). Без имени остаётся один партнёр: выдумывать читателю
  /// обращение ради красивой пары незачем.
  Widget _partnerLine(BuildContext context, L l, Profile partner) {
    final mine = SessionScope.of(context).profile?.name;
    final theirs =
        partner.name?.isNotEmpty == true ? partner.name! : l.scrPeopleUnnamed;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: _changePartner,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
        ),
        child: Row(children: [
          Expanded(
            child: Text(
              mine == null || mine.isEmpty ? theirs : l.cabPairJoin(mine, theirs),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AlmaType.numeral.copyWith(fontSize: 17),
            ),
          ),
          const SizedBox(width: 12),
          // **Строка должна читаться управлением, а не подписью.**
          //
          // Она нажималась и раньше, но выглядела заголовком с пояснением
          // сбоку, и владелец сказал прямо: «в совместимости нет добавления и
          // удаления других людей, вообще нет такой кнопки». Кнопка была —
          // ненаходимая, а это то же самое.
          //
          // Стрелка здесь несёт смысл, а не украшает: в этом продукте «→» стоит
          // на каждом месте, которое куда-то ведёт (карточки систем,
          // «прочитать начало»), и её отсутствие означало «здесь всё, дальше
          // некуда». За строкой — список людей, где добавляют и удаляют.
          Text(l.scrPeopleChange,
              style: AlmaType.meta.copyWith(color: AlmaPalette.goldBright)),
          const SizedBox(width: 6),
          Text('→',
              style: AlmaType.meta.copyWith(color: AlmaPalette.goldBright)),
        ]),
      ),
    );
  }

  /// Пункт списка «что будет посчитано» на S23.
  ///
  /// Точка отбивается сверху на 6, а не центрируется по строке: пункты в две
  /// строки здесь обычное дело в немецком и русском, и кружок, севший на
  /// середину двухстрочного пункта, читается маркером не того абзаца.
  Widget _compatBullet(String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          margin: const EdgeInsets.only(top: 6),
          width: 4,
          height: 4,
          decoration: BoxDecoration(
            color: AlmaPalette.gold.withValues(alpha: 0.7),
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: AlmaType.meta)),
      ],
    );
  }

  /// «стихия — воздух»: подпись слева строчными, значение справа засечным.
  ///
  /// `glyphs` включается там, где в значении стоит знак зодиака. Селектор
  /// начертания U+FE0E Flutter не слушает и берёт цветную эмодзи-плашку,
  /// поэтому вид знака задаётся шрифтом: `AlmaType.glyphFallback` — тот же
  /// список символьных шрифтов, которым подписано колесо, чтобы «♓» под
  /// рисунком и «♓» на самом рисунке были одним знаком. Остальные строки
  /// глифов не несут и остаются на своём засечном запасном списке.
  Widget _fact(String label, String value, {bool glyphs = false}) {
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
              glyphs ? CabinetWordsMore.keepSigns(value) : value,
              textAlign: TextAlign.right,
              // Голосу — имя знака: глиф VoiceOver прочесть нечем, а строка
              // существует ровно затем, чтобы назвать позицию.
              semanticsLabel: glyphs
                  ? CabinetWordsMore.spellSigns(L.of(context), value)
                  : null,
              style: AlmaType.numeral.copyWith(
                fontSize: 17,
                fontFamilyFallback: glyphs ? AlmaType.glyphFallback : null,
              ),
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

  /// Колонка под римскую цифру — одна на оглавление и на его заготовку.
  ///
  /// **40, а не 44.** Холст W3/W5 просит сорок, и число здесь было записано
  /// дважды числом 44 — в живой строке и в заготовке. Согласованность между
  /// ними была настоящей и остаётся: обе берут эту константу, и заготовка
  /// по-прежнему отпускает заголовок ровно туда, где он встанет. Разошлись они
  /// только с холстом — на четыре точки, каждая из которых съедала ширину
  /// колонки текста.
  static const _numeralColumn = 40.0;

  /// Место одной главы, пока оглавление в пути.
  ///
  /// Геометрия и числа — из макета (s28): отбивка 16 сверху и снизу, та же
  /// волосяная черта под строкой, метка 22×14 на месте римской цифры, под
  /// заголовком строка вопроса. Ширины заготовок разные (56/44/60 % и
  /// 78/64/70 %) — ровный частокол одинаковых полос читается как таблица, а
  /// не как оглавление. Блик идёт сверху вниз со сдвигом 0.1 с.
  ///
  /// Колонка под метку — [_numeralColumn], как у настоящей строки: когда
  /// придут заголовки, они встанут ровно туда, где стояли заготовки, и список
  /// не дёрнется.
  Widget _waitingRow(int i) {
    const title = [0.56, 0.44, 0.60];
    const question = [0.78, 0.64, 0.70];
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: _numeralColumn,
            child: WaitingBar(
              height: 14,
              width: 22,
              tone: WaitingTone.gold,
              delay: Duration(milliseconds: i * 300),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                WaitingBar(
                  height: 14,
                  widthFactor: title[i],
                  tone: WaitingTone.strong,
                  delay: Duration(milliseconds: i * 300 + 100),
                ),
                const SizedBox(height: 8),
                WaitingBar(
                  height: 11,
                  widthFactor: question[i],
                  tone: WaitingTone.faint,
                  delay: Duration(milliseconds: i * 300 + 200),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Одна глава: римская цифра засечным, заголовок, вопрос — и ничего про
  /// замок. Закрытая глава честно скажет это внутри, показав заголовок, вопрос
  /// и дверь; прятать её из списка значило бы прятать сам продукт.
  Widget _row(L l, ChapterEntry entry) {
    final partner = _partner;
    // Метка «read» кадра W3 — только у пары: у остальных систем оглавление
    // прочитанности не показывает, и рисовать её там значило бы дорисовать
    // кадр, которого нет.
    final read = widget.system == SystemSlug.compatibility &&
        _read.contains(entry.slug);
    return InkWell(
      // **Глава уходит с именем пары.** Без него сервер угадывает второго и
      // угадывает верно ровно до второго сохранённого человека: при двоих он
      // отвечает 422 `partner_required`, и глава показывала «добавь человека»
      // тому, у кого их уже двое. У остальных систем `_partner` пуст, и поле не
      // уезжает вовсе.
      onTap: () {
        // Пометка ставится на тапе, потому что экран главы трогать нельзя
        // (готовый паттерн C6), — и только по главе, которую сервер назвал
        // открытой: встреча с дверью — не чтение. См. `ReadingTally`.
        if (widget.system == SystemSlug.compatibility &&
            partner != null &&
            entry.open) {
          ReadingTally.noteChapterRead(
              SystemSlug.compatibility, partner.id, entry.slug);
          setState(() => _read = {..._read, entry.slug});
        }
        widget.onOpenChapter(widget.system, entry.slug, partner: _partner);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: _numeralColumn,
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
            if (read) ...[
              const SizedBox(width: 12),
              Padding(
                padding: const EdgeInsets.only(top: 5),
                child: Text(l.pairChapterRead,
                    style: AlmaType.meta.copyWith(
                        fontSize: 12,
                        color: AlmaPalette.gold.withValues(alpha: 0.75))),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
