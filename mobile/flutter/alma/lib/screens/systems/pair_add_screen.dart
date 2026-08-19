import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../design/buttons.dart';
import '../../design/emblem.dart';
import '../../design/metrics.dart';
import '../../design/night_sheet.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../design/wheel.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import 'birth_form_parts.dart';

/// W2 · ввод партнёра прямо в совместимости.
///
/// Кадр `W2 Add partner` холста монетизации v3 (`SCREENS-V3.md` §W2): анкетный
/// экран с двумя распорками, как V0, — шапка с оверлайном, заголовок, три
/// пилюльных поля и анкетная кнопка радиусом 15 («ключ, которым продвигаются
/// вперёд, не должен выглядеть как кнопка, которой покупают»).
///
/// **Цены на экране нет ни одной, и это инвариант шага** (`locked-chapter-spec`
/// §1): расчёт бесплатен, платен любой написанный текст, а цену называет
/// следующий экран. Ни `$`, ни слова «подписка» сюда не завозить.
///
/// Оговорка «платить предлагают после первой главы, не до» отсюда снята
/// владельцем 19.08.2026 («мы не даем бесплатно пару никакую все за деньги
/// можно писать только имя»): бесплатной первой главы у пары нет, и сервер не
/// пишет ей даже открывающий абзац. Инвариант это не ослабляет — он про то,
/// что цены нет **здесь**, а не про то, что до неё дают почитать.
///
/// **Экран кончается человеком.** Сохранил — вернул `Profile` тому, кто звал
/// (`Navigator.pop(saved)`): маршрут в главу I знает вызывающий
/// (`main.dart::_openPairChapter`), потому что слаг первой главы — знание
/// сервера, и второй копии этого знания здесь не будет.
///
/// **Четвёртое поле — место — холст не нарисовал, а сервер требует**
/// (`BirthInput.latitude/longitude/timezone` обязательны: без точки на земле
/// нет ни домов, ни часового пояса). Выдумать координаты нельзя — это была бы
/// ошибка до 180°, напечатанная уверенным тоном. Поле стоит той же пилюлей;
/// расхождение с холстом записано в спеке как вопрос владельцу.
class PairAddScreen extends StatefulWidget {
  const PairAddScreen({super.key});

  @override
  State<PairAddScreen> createState() => _PairAddScreenState();
}

class _PairAddScreenState extends State<PairAddScreen> {
  final _name = TextEditingController();
  final _place = TextEditingController();

  /// Дата не выбрана, пока человек её не назвал. Умолчания «1 января 1990»
  /// в пилюле нет намеренно: предзаполненная дата — это дата, которую никто
  /// не называл, готовая уехать на сервер (см. довод у колеса анкеты).
  ///
  /// С 19.08.2026 того же умолчания нет и внутри листа: барабаны открываются
  /// серединой списка и молчат, пока их не повернули, а «Готово» до этого не
  /// горит. Раньше пустота держалась только здесь, а лист подставлял «1 января
  /// 1990» сам — и «Готово», нажатое без прокрутки, делало эту дату ответом.
  int? _day, _month, _year;

  /// Время — необязательное, и «не выбрано» здесь законное конечное
  /// состояние, а не недозаполненность: помета `optional` стоит на самом поле.
  int? _hour, _minute;

  Place? _chosen;
  List<Place> _found = const [];
  bool _saving = false;
  String? _failure;

  @override
  void dispose() {
    _name.dispose();
    _place.dispose();
    super.dispose();
  }

  bool get _ready => _day != null && _chosen != null && !_saving;

  Future<void> _search(String query) async {
    if (query.trim().length < 2) return;
    try {
      final found = await SessionScope.of(context).client.searchPlaces(query);
      if (mounted) setState(() => _found = found.take(5).toList());
    } on AlmaError {
      // Молча: место можно поискать ещё раз.
    }
  }

  Future<void> _save() async {
    if (!_ready) return;
    final l = L.of(context);
    final session = SessionScope.of(context);
    setState(() {
      _saving = true;
      _failure = null;
    });
    try {
      final saved = await savePartner(
        session,
        birthDate: '${_year.toString().padLeft(4, '0')}-'
            '${_month.toString().padLeft(2, '0')}-'
            '${_day.toString().padLeft(2, '0')}',
        birthTime: _hour == null
            ? null
            : '${_hour.toString().padLeft(2, '0')}:'
                '${(_minute ?? 0).toString().padLeft(2, '0')}',
        place: _chosen!,
        name: _name.text,
      );
      if (!mounted) return;
      Navigator.of(context).pop(saved);
    } on AlmaError catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        // 402 `partner_limit` приходит на языке аккаунта и показывается
        // дословно; всему остальному — общая строка, а не голое молчание:
        // кнопка, не ответившая ничем, читается как сломанная.
        _failure = error is ServerRefused && error.message.isNotEmpty
            ? error.message
            : l.stateUnavailable;
      });
    }
  }

  /* ── пилюли даты и времени ────────────────────────────────────────────── */

  /// Дата — один лист с тремя барабанами, а не три пилюли, как на экране
  /// людей: холст рисует **одно** поле «Date of birth», и разбивать его на
  /// три значило бы перерисовать кадр.
  ///
  /// **Лист называет то, по чему постучали.** Заголовок — подпись самой
  /// пилюли, а не новое слово: своих строк у листа нет и заводить их незачем.
  Future<void> _pickDate() async {
    // Год открывается не серединой диапазона, а «тридцатью годами назад»: тем
    // же числом и по той же причине, что в анкете. Середина 1900–2026 — это
    // 1963, а середина взрослой жизни тридцать лет назад.
    final lastYear = DateTime.now().year;
    final yearOpensAt = lastYear - 30;
    int? day = _day, month = _month, year = _year;
    final done = await showAlmaSheet<bool>(
      context: context,
      title: L.of(context).paywallV3PairInputDate,
      builder: (context, refresh) {
        // Дней в месяце — сколько есть на самом деле: 30 февраля, уехавшее
        // на сервер, вернулось бы отказом на языке валидатора, а не формы.
        // Пока месяц и год не названы, счёт идёт по тому, на чём стоят их
        // барабаны: в окне видно июль, и список дней обязан кончаться там же,
        // где кончается видимый месяц.
        final days = DateUtils.getDaysInMonth(
            year ?? yearOpensAt, month ?? AlmaWheel.opensAt(1, 12));
        final chosenDay = day;
        if (chosenDay != null && chosenDay > days) day = days;
        return [
          Row(children: [
            _wheel(L.of(context).journeyCaptureDayShort, day, 1, days,
                (v) => refresh(() => day = v)),
            _wheel(L.of(context).journeyCaptureMonthShort, month, 1, 12,
                (v) => refresh(() => month = v)),
            _wheel(L.of(context).journeyCaptureYearShort, year, 1900, lastYear,
                (v) => refresh(() => year = v), fallback: yearOpensAt),
          ]),
          const SizedBox(height: 18),
          // **Золотая, а не контурная.** На листе действие ровно одно, и
          // золото продукта означает именно его. Двух золотых на экране не
          // бывает — но лист и есть отдельная поверхность со своим единственным
          // ключом, ровно как шит двери V2, где золотая кнопка стоит внутри
          // шита. Радиус — пилюля 28 (половина высоты 56): анкетные 15
          // принадлежат кнопке шага, а не двери, которая закрывается.
          AlmaButton(
            label: L.of(context).scrDone,
            // Гаснет, пока все три колонки не названы. Нетронутый барабан —
            // это не ответ, а положение, в котором он открылся: «Готово» над
            // ним закрывало бы лист датой, которой никто не говорил.
            onTap: day == null || month == null || year == null
                ? null
                : () => Navigator.of(context).pop(true),
          ),
        ];
      },
    );
    if (done == true && mounted) {
      setState(() {
        _day = day;
        _month = month;
        _year = year;
      });
    }
  }

  Future<void> _pickTime() async {
    int? hour = _hour, minute = _minute;
    final answer = await showAlmaSheet<String>(
      context: context,
      title: L.of(context).pairInputTime,
      builder: (context, refresh) => [
        Row(children: [
          // Ноль впереди — у часов и минут, как в анкете: «09» рядом с «10»
          // держит колонку ровной, «9» роняет её на пол-цифры.
          _wheel(L.of(context).journeyHourLabel, hour, 0, 23,
              (v) => refresh(() => hour = v), pad: true),
          _wheel(L.of(context).journeyMinuteLabel, minute, 0, 59,
              (v) => refresh(() => minute = v), pad: true),
        ]),
        const SizedBox(height: 18),
        AlmaButton(
          label: L.of(context).scrDone,
          // Время, названное наполовину, — опечатка, а не ответ (то же правило
          // на шаге анкеты). Незнание говорят кнопкой ниже, и она горит всегда:
          // выключить обе значило бы запереть лист.
          onTap: hour == null || minute == null
              ? null
              : () => Navigator.of(context).pop('set'),
        ),
        const SizedBox(height: 8),
        // Обратная дорога: время выбрали, а потом вспомнили, что не знают.
        // Без неё поле `optional` становилось бы необратимым — единственный
        // способ снять значение был бы «выйти и ввести всё заново».
        AlmaButton(
          kind: AlmaButtonKind.veil,
          label: L.of(context).cabUnknownTime,
          onTap: () => Navigator.of(context).pop('clear'),
        ),
      ],
    );
    if (!mounted || answer == null) return;
    setState(() {
      if (answer == 'clear') {
        _hour = null;
        _minute = null;
      } else {
        _hour = hour;
        _minute = minute;
      }
    });
  }

  /// Один барабан листа, обёрнутый распоркой колонки.
  ///
  /// Сам барабан — общий `AlmaWheel` из `design/`: те же 148 точек окна, та же
  /// полоса выбора золотом 0.16 и та же лестница яркости 1 → .55 → .4, что у
  /// колеса анкеты. Здесь остаётся ровно то, что принадлежит этому экрану:
  /// какие колонки и в каком порядке.
  Widget _wheel(String label, int? value, int min, int max,
      ValueChanged<int> onChanged,
      {bool pad = false, int? fallback}) {
    return Expanded(
      child: AlmaWheel(
        label: label,
        min: min,
        max: max,
        value: value,
        fallback: fallback,
        onChanged: onChanged,
        caption: pad ? (v) => v.toString().padLeft(2, '0') : null,
      ),
    );
  }

  /// Пилюля выбора — то же очертание, что у `CeremonialField`: высота 54,
  /// радиус в половину, в покое тёмная плашка с бледным кантом. Выбранное
  /// значение печатается телом, пустое — плейсхолдером на 0.45, как на холсте.
  Widget _pill({
    required String hint,
    String? value,
    String? trailing,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        height: AlmaMetrics.fieldHeight,
        padding: const EdgeInsets.symmetric(horizontal: 18),
        decoration: BoxDecoration(
          color: const Color(0xD90D101C),
          borderRadius: BorderRadius.circular(AlmaMetrics.fieldHeight / 2),
          border: Border.all(color: const Color(0x1FEDE7DA)),
        ),
        child: Row(children: [
          Expanded(
            child: Text(
              value ?? hint,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AlmaType.body.copyWith(
                fontSize: 15.5,
                color: value == null
                    ? AlmaPalette.body.withValues(alpha: 0.45)
                    : AlmaPalette.inkLight,
              ),
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 12),
            // `optional` — Golos 12.5, золото на 0.8: снято с кадра.
            Text(trailing,
                style: AlmaType.meta.copyWith(
                    fontSize: 12.5,
                    color: AlmaPalette.gold.withValues(alpha: 0.8))),
          ],
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final date = _day == null
        ? null
        : DateFormat.yMMMMd(l.localeName)
            .format(DateTime.utc(_year!, _month!, _day!));
    final time = _hour == null
        ? null
        : '${_hour.toString().padLeft(2, '0')}:'
            '${(_minute ?? 0).toString().padLeft(2, '0')}';
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      // Небо экран рисует себе сам: каркас кабинета — прокручиваемая колонка
      // с заголовком, а здесь анкета с распорками и донной кнопкой.
      body: NightSky(
        seed: 0x57325041,
        child: SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
            child: Column(children: [
              const SizedBox(height: 12),
              // Шапка кадра: «←», оверлайн по центру, распорка той же ширины —
              // центр обязан быть настоящим центром строки.
              Row(children: [
                GestureDetector(
                  onTap: () => Navigator.of(context).maybePop(),
                  behavior: HitTestBehavior.opaque,
                  child: SizedBox(
                    width: 44,
                    height: 44,
                    child: Center(
                      child: Text('←',
                          style: AlmaType.body.copyWith(
                              fontSize: 18,
                              color:
                                  AlmaPalette.body.withValues(alpha: 0.7))),
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    l.scrPeopleEyebrow.toUpperCase(),
                    textAlign: TextAlign.center,
                    style:
                        AlmaType.readerHead.copyWith(color: AlmaPalette.gold),
                  ),
                ),
                const SizedBox(width: 44),
              ]),
              Expanded(
                // Колонка с двумя распорками, но готовая к клавиатуре: без
                // прокрутки поле места ныряло бы под неё вместе с находками.
                child: LayoutBuilder(
                  builder: (context, box) => SingleChildScrollView(
                    child: ConstrainedBox(
                      constraints: BoxConstraints(minHeight: box.maxHeight),
                      child: IntrinsicHeight(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Spacer(),
                            Text(l.paywallV3PairInputTitle,
                                style: AlmaType.displayL),
                            const SizedBox(height: 10),
                            Text(l.pairInputNote,
                                style: AlmaType.meta.copyWith(height: 1.5)),
                            const SizedBox(height: 24),
                            // Порядок «имя → дата → время» разговорный, а не
                            // машинный: сначала о ком, потом когда. Имя
                            // необязательно; обязательны дата и место.
                            CeremonialField(
                              controller: _name,
                              hint: l.paywallV3PairInputName,
                            ),
                            const SizedBox(height: 11),
                            _pill(
                              hint: l.paywallV3PairInputDate,
                              value: date,
                              onTap: _pickDate,
                            ),
                            const SizedBox(height: 11),
                            _pill(
                              hint: l.pairInputTime,
                              value: time,
                              trailing: time == null ? l.pairInputOptional : null,
                              onTap: _pickTime,
                            ),
                            const SizedBox(height: 11),
                            CeremonialField(
                              controller: _place,
                              hint: l.pairInputPlace,
                              onChanged: _search,
                            ),
                            PlaceSuggestions(
                              found: _found,
                              onPick: (place) => setState(() {
                                _chosen = place;
                                _place.text = place.label;
                                _found = const [];
                              }),
                            ),
                            const SizedBox(height: 18),
                            // ✦-сноска кадра: бесплатен **расчёт**, платны
                            // главы. Обещание «первую главу читаешь до любых
                            // решений» снято владельцем 19.08.2026 — «мы не
                            // даем бесплатно пару никакую все за деньги можно
                            // писать только имя», — и вместе с ним сервер
                            // перестал писать паре открывающий абзац. Фраза
                            // холста написана про «его» карту, а род партнёра
                            // здесь не спрашивают — в каталоге она
                            // родо-нейтральна.
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Padding(
                                  padding: const EdgeInsets.only(top: 1),
                                  child: Text('✦',
                                      style: AlmaType.numeral
                                          .copyWith(fontSize: 12)),
                                ),
                                const SizedBox(width: 9),
                                Expanded(
                                  child: Text(
                                    l.pairInputFreeNote,
                                    style: AlmaType.meta.copyWith(
                                        fontSize: 12.5,
                                        height: 1.5,
                                        color: AlmaPalette.body
                                            .withValues(alpha: 0.7)),
                                  ),
                                ),
                              ],
                            ),
                            const Spacer(),
                            // **Отказ стоит у кнопки и отличается от пояснения
                            // цветом.**
                            //
                            // Он стоял выше, сразу за ✦-сноской, и тем же серым
                            // мета-стилем. На проверке предел свободного тарифа
                            // («один сохранённый человек») вернулся ровно так и
                            // прочитался вторым абзацем подсказки: нажатие
                            // выглядело не отказом, а полным отсутствием
                            // ответа. Отказ — ответ на нажатие, и стоять ему
                            // рядом с тем, что нажали, тем же цветом, каким во
                            // всём продукте говорят «не вышло».
                            if (_failure != null) ...[
                              Text(_failure!,
                                  style: AlmaType.meta.copyWith(
                                      color: AlmaPalette.disagree,
                                      height: 1.5)),
                              const SizedBox(height: 12),
                            ] else
                              const SizedBox(height: 16),
                            AlmaButton(
                              // Радиус 15 — анкетная форма, как на V0.
                              radius: 15,
                              label:
                                  _saving ? l.scrAddPersonSaving : l.pairInputCta,
                              onTap: _ready ? _save : null,
                            ),
                            // Под кнопкой ничего не стоит, и это осознанно.
                            //
                            // Здесь была фраза «The bought pair report — four
                            // chapters, zero commerce inside». На холсте это
                            // **подпись кадра W3** — пометка дизайнера о том,
                            // что внутри купленного отчёта нет торговли. В
                            // приложении она превращалась в текст о продукте от
                            // третьего лица, который читает человек, набирающий
                            // чужую дату рождения. Обещание этого экрана уже
                            // сказано выше, у ✦: расчёт бесплатный, главы
                            // платные.
                            //
                            // Донная распорка кадра — 44 плюс кромка жеста.
                            SizedBox(
                                height: 44 +
                                    MediaQuery.paddingOf(context).bottom),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
