import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../design/buttons.dart';
import '../../design/emblem.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../design/wheel.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../systems/writing_art.dart';
import 'push_ask_screen.dart';

/// Путешествие: шесть шагов от имени до церемонии и трёхшаговый хвост за ней.
///
/// Порт `mobile/ios/Alma/Screens/Journey/*`. Порядок шагов тот же — имя, о
/// себе, дата, время, место, церемония, — и обещание под первым вопросом то
/// же: «Пока ничего не сохраняется». Это правда буквально: профиль не
/// создаётся до нажатия «Построить моё небо», и человек, закрывший путешествие
/// на четвёртом шаге, не оставил на сервере ничего.
///
/// ## Хвост: `s37` → `s39` → `s44`
///
/// До 16 августа 2026 церемония звала [onDone] и человек оказывался прямо в
/// кабинете. Три экрана, нарисованные для этой минуты, не показывались никогда —
/// а минута эта единственная в своём роде: числа только что посчитаны, читать
/// ещё нечего, и человек впервые в жизни установки готов слушать про продукт
/// целиком. Порядок восстановлен целиком и точно, ничего не выкинуто:
///
/// * **`s37`, витрина под натальной картой** — *единственный автоматический
///   показ витрины в продукте*. Все остальные продающие экраны человек
///   открывает сам: ткнув в закрытую главу, нажав «Вся Alma», зайдя в
///   настройки. Без этого шага денежный слой стоит на одних стенах — то есть
///   существует только для тех, кто уже упёрся в закрытую дверь;
/// * **`s39`, пред-вопрос про уведомления** — обязателен **до** системного
///   диалога, и это не вежливость. iOS даёт одну попытку на установку; о том,
///   почему её нельзя тратить без пре-аска, подробно в [PushAskScreen];
/// * **`s44`, вход** — пропускаемый, но показывается. Гость должен узнать, что
///   карта может следовать за ним на другой телефон: тот, кто не знал этого в
///   день прихода, узнаёт об этом в день, когда телефон уже поменял, — и узнаёт
///   вместе с тем, что покупки остались на старом.
///
/// **Маршрутами поверх путешествия, а не состоянием внутри него.** Каждый из
/// трёх экранов уже умеет уходить сам — «Skip for now», «Not now», стрелка
/// назад, — и все три зовут `maybePop`. Положенные сюда состоянием, они бы этот
/// выход потеряли: `maybePop` на корневом маршруте не делает ничего.
class JourneyScreen extends StatefulWidget {
  const JourneyScreen({super.key, required this.onDone});

  final VoidCallback onDone;

  @override
  State<JourneyScreen> createState() => _JourneyScreenState();
}

/// Шесть шагов, как на нативе. Церемония — не украшение и не заставка: это
/// единственный экран, где системы действительно считаются, и человек видит,
/// что за него взялись, вместо белого поля с крутилкой.
// Интерес стоит вторым — «шаг II» холста V0. Шагов стало семь, и счётчик
// печатает семь: холст обещал VI, но сам же держал это открытым вопросом
// (сводка №10 — счётчик обещает шесть, нарисовано два). Считать по-настоящему
// честнее, чем подгонять число под рисунок.
enum _Step { name, interest, about, date, time, place, ceremony }

class _JourneyScreenState extends State<JourneyScreen> {
  /// С какого шага открыться. **Вход для проверки, как на нативе**
  /// (`JourneyModel.swift` читает `AlmaJourneyStep` из `UserDefaults`): экраны
  /// анкеты видны один раз в жизни установки, и снять их рядом с нативным
  /// кадром иначе нечем. В обычной сборке константа пуста и шаг первый.
  _Step _step = _Step.values.firstWhere(
    (step) => step.name == const String.fromEnvironment('ALMA_JOURNEY_STEP'),
    orElse: () => _Step.name,
  );

  final _name = TextEditingController();
  String? _gender;

  /// Ответ V0 «что сейчас важнее всего»: love / money / self / future.
  /// Null — пропустил; NBO тогда работает по ветке «понять себя» (А7 №15),
  /// и кнопка «дальше» пропуск разрешает: спрашивать дважды хуже, чем не
  /// узнать.
  String? _interest;

  // **Ничего не предзаполнено.** Колесо, открывшееся на «1 января 2000»,
  // читается как ответ, который уже дан: человек прокручивает мимо и уезжает
  // с чужой датой. `null` значит «не трогали», и первое же движение
  // записывает — как на нативе, где биндинг колеса показывает первое значение
  // и не присваивает его.
  int? _day, _month, _year;
  int? _hour, _minute;
  bool _timeUnknown = false;
  final _placeQuery = TextEditingController();
  List<Place> _places = const [];
  Place? _place;
  bool _saving = false;
  String? _failure;

  /// Развилка перевода часов, если небо задало встречный вопрос.
  ///
  /// **Это интеррапт церемонии, а не шаг анкеты.** Номера у неё нет: спросить
  /// можно только после «Построить моё небо», когда расчёт упёрся в двойное
  /// 02:30, — но и «V / VI» солгало бы, потому что это не шестая часть анкеты.
  /// Решение владельца: биты церемонии встают на паузу и не сбрасываются,
  /// стрелка ведёт назад на шаг времени.
  AmbiguousBirthTime? _fork;

  /// Какое из двух времён выбрано. Уезжает в профиль и живёт там: без этого
  /// вопрос возвращался бы на каждом расчёте.
  String? _fold;

  /// Начало анкеты сообщается один раз за приход, а не на каждый кадр.
  bool _announced = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_announced) return;
    _announced = true;
    SessionScope.of(context).client.track(FunnelStage.quizStart);
  }

  @override
  void dispose() {
    _name.dispose();
    _placeQuery.dispose();
    super.dispose();
  }

  static int get _thisYear => DateTime.now().year;

  /// Месяц словом, на языке интерфейса. Числом он читается как ещё одна
  /// колонка цифр, и «03» рядом с «03» днём — это две одинаковые колонки.
  static String _monthName(String locale, int month) =>
      DateFormat.MMMM(locale).format(DateTime.utc(2000, month));

  /// Все три колеса тронуты.
  bool get _dateComplete => _day != null && _month != null && _year != null;

  /// Такой даты не бывает. Проверяется тем же способом, что на нативе:
  /// собранная дата обязана вернуть те же день и месяц — 31 февраля молча
  /// становится 2 марта, и молчание здесь недопустимо.
  bool get _dateImpossible {
    if (!_dateComplete) return false;
    final made = DateTime.utc(_year!, _month!, _day!);
    return made.month != _month || made.day != _day;
  }

  /// Время введено наполовину. Пустое время пропускают — это и есть «не
  /// знаю»; половина времени — это опечатка, и с ней дальше не пускают.
  bool get _timeHalfGiven =>
      !_timeUnknown && (_hour == null) != (_minute == null);

  Future<void> _searchPlaces(String query) async {
    if (query.trim().length < 2) return;
    final session = SessionScope.of(context);
    try {
      final places = await session.client
          .searchPlaces(query.trim(), locale: session.locale);
      if (mounted) setState(() => _places = places.take(5).toList());
    } on AlmaError {
      // Пустой список честнее сломанного экрана; строка «ничего не нашлось»
      // появится сама.
    }
  }

  Future<void> _build() async {
    final place = _place;
    if (place == null || _saving) return;
    final session = SessionScope.of(context);
    setState(() {
      _saving = true;
      _failure = null;
    });
    try {
      // **Анкета завершается здесь, а не на портрете.** К этой минуте отвечено
      // на каждый вопрос; портрет — награда, и путать «ответил на всё» с
      // «увидел результат» значит спрятать ровно тех людей, у кого сохранение
      // не прошло.
      await session.client.track(FunnelStage.quizComplete);
      await session.client.saveProfile(BirthInput(
        birthDate: '${_year!.toString().padLeft(4, '0')}-'
            '${_month!.toString().padLeft(2, '0')}-'
            '${_day!.toString().padLeft(2, '0')}',
        birthTime: _timeUnknown || _hour == null || _minute == null
            ? null
            : '${_hour!.toString().padLeft(2, '0')}:'
                '${_minute!.toString().padLeft(2, '0')}',
        latitude: place.latitude,
        longitude: place.longitude,
        timezone: place.timezone,
        placeLabel: place.label,
        placeId: place.id,
        name: _name.text.trim().isEmpty ? null : _name.text.trim(),
        onAmbiguous: _fold,
        // Язык **запроса**, а не аккаунта: сессия принимает язык телефона у
        // себя сразу, а на сервер он уезжает отдельной необязательной записью.
        // Отказ этой ручки обязан прийти на том языке, на котором человек
        // сейчас читает анкету.
      ), locale: session.locale, gender: _gender, interest: _interest);
      if (_name.text.trim().isNotEmpty) {
        await session.client.setDisplayName(_name.text.trim());
      }
      // **Церемония наконец действительно считает.** Докстринг рядом обещал
      // это давно, а на деле она была таймером на восемь ударов: ни сохранение
      // профиля, ни хаб ничего не вычисляют. Натальная карта — расчёт, который
      // человеку всё равно нужен первым, и сервер её кэширует, так что это не
      // лишняя работа, а перенесённая на девять секунд раньше.
      //
      // И только здесь может прийти встречный вопрос про двойное время.
      await session.client.compute(SystemSlug.natal);
      await session.start(force: true);
      if (!mounted) return;
      setState(() => _saving = false);
      // Кто пришёл вторым, тот и уводит.
      if (_ceremonyPlayed) _leave();
    } on AmbiguousBirthTime catch (fork) {
      // Не отказ, а вопрос: церемония замирает и ждёт ответа.
      if (mounted) {
        setState(() {
          _saving = false;
          _fork = fork;
        });
      }
    } on AlmaError catch (error) {
      if (mounted) {
        setState(() {
          _saving = false;
          _failure = error is ServerRefused && error.message.isNotEmpty
              ? error.message
              : L.of(context).stateUnavailable;
        });
      }
    }
  }

  /// Время, которое человек назвал, — в том же виде, в каком его показывают
  /// строки развилки: «02:30».
  String get _wallClock => _hour == null || _minute == null
      ? ''
      : '${_hour!.toString().padLeft(2, '0')}:'
          '${_minute!.toString().padLeft(2, '0')}';

  /// Ответ дан — сохраняем его в профиль и продолжаем расчёт.
  Future<void> _answerFork(String choice) async {
    setState(() {
      _fold = choice;
      _fork = null;
    });
    await _build();
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      // Тело сжимается под клавиатуру (значение по умолчанию, но объявлено явно):
      // прокрутка внутри `Expanded` выше держит кнопку над её кромкой.
      resizeToAvoidBottomInset: true,
      body: NightSky(
        mood: SkyMood.ceremony,
        seed: 0x4A4F5552 + _step.index,
        child: SafeArea(
          child: _step == _Step.ceremony
              ? Stack(children: [
                  // **Развилка ложится поверх церемонии, а не вместо неё.**
                  //
                  // Заменяя сцену, я её размонтировал — а `dispose` ставит
                  // `_stopped`, то есть биты не вставали на паузу, а
                  // сбрасывались, и после ответа отсчёт начинался заново.
                  // Владелец сказал прямо: на паузе, не сбрасываются.
                  _Ceremony(
                  paused: _fork != null,
                  onDone: () {
                    // Церемония доиграла. Уходим, только когда и сохранение
                    // закончилось: сцена, ушедшая раньше ответа сервера,
                    // показала бы пустой кабинет.
                    if (mounted && !_saving) _leave();
                    _ceremonyPlayed = true;
                  },
                ),
                  if (_fork != null)
                    Positioned.fill(
                      child: ColoredBox(
                        // Вопрос закрывает сцену собой: под ним она живёт, но
                        // читать два текста разом нельзя.
                        color: AlmaPalette.night.withValues(alpha: 0.96),
                        child: _Fork(
                          fork: _fork!,
                          time: _wallClock,
                          city: _place?.label ?? '',
                          onChoose: _answerFork,
                          onBack: () => setState(() {
                            _fork = null;
                            _step = _Step.time;
                          }),
                        ),
                      ),
                    ),
                ])
              : Padding(
            padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const SizedBox(height: 12),
              Row(children: [
                // «I / V» — римскими, как на нативных экранах. Знаменатель
                // считается по самому перечислению: жёсткая «VI» обещала
                // шестой шаг, которого в порте нет — церемония ещё не
                // перенесена, — и последний экран анкеты объявлял себя «V / VI»,
                // то есть предпоследним.
                Text(
                  '${_roman(_step.index + 1)} / ${_roman(_Step.values.length)}',
                  style: AlmaType.numeral.copyWith(color: AlmaPalette.gold),
                ),
                const Spacer(),
                if (_step != _Step.name)
                  IconButton(
                    onPressed: () =>
                        setState(() => _step = _Step.values[_step.index - 1]),
                    icon: const Icon(Icons.arrow_back, color: AlmaPalette.gold),
                  ),
              ]),
              // **Тело шага прокручивается, а кнопка держится над клавиатурой.**
              //
              // Здесь был жёсткий столбец с двумя `Spacer`, и на шаге города
              // (VI/VII) клавиатура сжимала тело: заголовок + поле + пять подсказок
              // + кнопка не влезали в остаток высоты, `Spacer` схлопывались в ноль,
              // и «Build my sky» уезжала под клавиатуру — снято на устройстве 22 авг.
              //
              // Теперь тело живёт в `Expanded` с прокруткой: пока места хватает,
              // `minHeight` + центрирование держат шаг ровно как прежде; когда
              // клавиатура его сжимает, содержимое прокручивается, а не переполняется.
              // Кнопка стоит ниже `Expanded` — то есть всегда над кромкой клавиатуры,
              // а не за ней.
              Expanded(
                child: LayoutBuilder(
                  builder: (context, constraints) => SingleChildScrollView(
                    child: ConstrainedBox(
                      constraints: BoxConstraints(minHeight: constraints.maxHeight),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: _stepBody(l),
                      ),
                    ),
                  ),
                ),
              ),
              if (_failure != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Text(_failure!, style: AlmaType.meta),
                ),
              _cta(l),
              const SizedBox(height: 24),
            ]),
          ),
        ),
      ),
    );
  }

  /// Церемония доиграла до конца. Нужно, чтобы уйти в кабинет тому, у кого
  /// сохранение оказалось дольше девяти с половиной секунд.
  bool _ceremonyPlayed = false;

  /// Хвост уже идёт. Позвать его пытаются двое — доигравшая церемония и
  /// закончившееся сохранение, — и кто из них придёт вторым, заранее неизвестно
  /// (в этом весь смысл `_ceremonyPlayed`). Второй зов обязан не сделать
  /// ничего: три экрана, выложенные в стек дважды, человек проходил бы дважды.
  bool _leaving = false;

  /// Конец путешествия — кабинет на «Мои системы». Хвост из трёх экранов (глава,
  /// уведы, вход) убран; почему — в теле метода.
  Future<void> _leave() async {
    if (_leaving) return;
    _leaving = true;
    // **Сразу кабинет, вкладка «Мои системы» (посадку делает main.dart:onDone).**
    // Раньше здесь в стек ложились три экрана: бесплатная глава натала, пред-вопрос
    // про уведомления и вход. Человек падал прямо в чтение, оттуда «выйти», вопрос
    // про уведы, потом регистрация — владелец назвал это «максимально неудобно»
    // (22 авг). Теперь анкета ведёт на восемь карт, где первая глава уже открыта;
    // уведомления — тумблером в настройках, вход — карточкой «Keep your chart» на
    // «Сегодня». Предлагать их проактивно (после активности; после первой покупки)
    // — отдельная волна.
    widget.onDone();
  }

  static String _roman(int n) =>
      const ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'][n - 1];

  List<Widget> _stepBody(L l) => switch (_step) {
        _Step.name => [
            Text(l.journeyNameTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyNameSub, style: AlmaType.meta),
            const SizedBox(height: 24),
            // Плейсхолдера нет намеренно: «София» в поле имени читается как
            // чужая заполненная анкета, а не как подсказка.
            CeremonialField(controller: _name),
            const SizedBox(height: 12),
            // **Под полем, а не под заголовком.** Наверху сказано, что ничего
            // не сохраняется; здесь — где имя вообще будет видно. Это ответ на
            // вопрос, который появляется уже после того, как имя набрали, и в
            // эталоне строка стоит именно под полем (`s13`, y=535 против
            // поля на 470).
            Text(
              l.journeyNameHint,
              style: AlmaType.meta
                  .copyWith(color: AlmaPalette.body.withValues(alpha: 0.55)),
            ),
          ],
        _Step.interest => [
            // Жёсткий перенос холста: «What matters most / right now?».
            Text(l.quizInterestTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.quizInterestNote, style: AlmaType.meta),
            const SizedBox(height: 24),
            for (final (value, glyph, label) in [
              ('love', '♥', l.quizInterestLove),
              ('money', '◈', l.quizInterestMoney),
              ('self', '☾', l.quizInterestSelf),
              ('future', '✦', l.quizInterestFuture),
            ])
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _interestCard(
                  glyph: glyph,
                  label: label,
                  selected: _interest == value,
                  // Повторный тап снимает выбор: пропуск — законный ответ
                  // (А7 №15, NBO без интереса живёт по ветке «понять себя»),
                  // и дорога к нему обязана существовать не только «мимо».
                  onTap: () => setState(
                      () => _interest = _interest == value ? null : value),
                ),
              ),
          ],
        _Step.about => [
            Text(l.journeyAboutTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyAboutSkip, style: AlmaType.meta),
            const SizedBox(height: 24),
            for (final (value, label) in [
              ('female', l.journeyGenderFemale),
              ('male', l.journeyGenderMale),
              (null, l.journeyGenderSkip),
            ])
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _choice(label, selected: _gender == value, onTap: () {
                  setState(() => _gender = value);
                }),
              ),
          ],
        _Step.date => [
            Text(l.journeyDateTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyDateSub, style: AlmaType.meta),
            const SizedBox(height: 24),
            // **Три колеса, а не три поля.** Дату рождения набирают один раз
            // в жизни, и клавиатура здесь — это четыре тапа, проверка на
            // «31 февраля» и всплывающая цифровая панель поверх вопроса. Колесо
            // не даёт ввести невозможное число вовсе.
            Row(children: [
              Expanded(
                child: AlmaWheel(
                  key: const ValueKey('wheel.day'),
                  label: l.journeyCaptureDay,
                  // Подписи над колёсами анкеты нет: над ними стоит вопрос
                  // шага, и «ДЕНЬ · МЕСЯЦ · ГОД» под «Когда вы родились?» —
                  // это форма заявления, а не разговор. Голосу подпись
                  // остаётся.
                  showLabel: false,
                  min: 1,
                  max: 31,
                  value: _day,
                  onChanged: (d) => setState(() => _day = d),
                ),
              ),
              // Месяц — словом, и только ему отдана лишняя ширина: «Сентябрь»
              // в колонку по числу цифр не помещается.
              Expanded(
                flex: 2,
                child: AlmaWheel(
                  key: const ValueKey('wheel.month'),
                  label: l.journeyCaptureMonth,
                  showLabel: false,
                  min: 1,
                  max: 12,
                  value: _month,
                  caption: (m) => _monthName(l.localeName, m),
                  onChanged: (m) => setState(() => _month = m),
                ),
              ),
              Expanded(
                child: AlmaWheel(
                  key: const ValueKey('wheel.year'),
                  label: l.journeyCaptureYear,
                  showLabel: false,
                  // **Годы идут вверх, как в эталоне, а не вниз.**
                  //
                  // Список шёл от «десять лет назад» вниз, и колесо открывалось
                  // на 2016 — то есть на годе, который почти никому не нужен, а
                  // до своего человек крутил полсотни строк. Теперь порядок
                  // естественный, а открывается колесо на тридцати годах назад:
                  // это середина списка и середина взрослой жизни.
                  //
                  // Верхняя граница прежняя — десять лет назад: продукт для
                  // взрослых, и год рождения младенца это строка, которую
                  // прокручивают мимо, а не выбирают.
                  min: _thisYear - 101,
                  max: _thisYear - 10,
                  value: _year,
                  fallback: _thisYear - 30,
                  onChanged: (y) => setState(() => _year = y),
                ),
              ),
            ]),
            // Дата, которой не бывает, названа до нажатия «дальше», а не
            // отказом сервера после.
            if (_dateImpossible)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(l.journeyCaptureImpossibleDate,
                    style: AlmaType.meta.copyWith(color: AlmaPalette.goldBright)),
              ),
          ],
        _Step.time => [
            Text(l.journeyTimeTitle, style: AlmaType.displayL),
            const SizedBox(height: 24),
            // Колёса гаснут и перестают отвечать, когда объявлено незнание:
            // время, набранное под галочкой «не знаю», всё равно не поедет.
            AnimatedOpacity(
              opacity: _timeUnknown ? 0.4 : 1,
              duration: AlmaMotion.ui,
              child: IgnorePointer(
                ignoring: _timeUnknown,
                child: Row(children: [
                  Expanded(
                    child: AlmaWheel(
                      key: const ValueKey('wheel.hour'),
                      label: l.journeyHourLabel,
                      showLabel: false,
                      min: 0,
                      max: 23,
                      value: _hour,
                      caption: (h) => h.toString().padLeft(2, '0'),
                      onChanged: (h) => setState(() => _hour = h),
                    ),
                  ),
                  Expanded(
                    child: AlmaWheel(
                      key: const ValueKey('wheel.minute'),
                      label: l.journeyMinuteLabel,
                      showLabel: false,
                      min: 0,
                      max: 59,
                      value: _minute,
                      caption: (m) => m.toString().padLeft(2, '0'),
                      onChanged: (m) => setState(() => _minute = m),
                    ),
                  ),
                ]),
              ),
            ),
            const SizedBox(height: 18),
            _choice(
              l.journeyCaptureUnknownTime,
              selected: _timeUnknown,
              onTap: () => setState(() => _timeUnknown = !_timeUnknown),
            ),
            const SizedBox(height: 8),
            // Что закрывается без времени — сказано до, а не обнаружено после.
            Text(l.journeyLockedWithoutTime, style: AlmaType.meta),
          ],
        _Step.place => [
            Text(l.journeyPlaceTitle, style: AlmaType.displayL),
            const SizedBox(height: 10),
            Text(l.journeyPlaceSub, style: AlmaType.meta),
            const SizedBox(height: 24),
            CeremonialField(
              controller: _placeQuery,
              hint: l.journeyCaptureSearchPlace,
              onChanged: _searchPlaces,
            ),
            const SizedBox(height: 8),
            for (final (index, place) in _places.indexed)
              _PlaceRow(
                label: place.label,
                best: index == 0,
                selected: _place?.id == place.id,
                onTap: () {
                  // Город выбран — клавиатуру прячем сразу: экран возвращается к
                  // спокойной раскладке, и «Build my sky» видна без прокрутки,
                  // а не остаётся под клавиатурой ждать, пока человек догадается
                  // её закрыть.
                  FocusScope.of(context).unfocus();
                  setState(() {
                    _place = place;
                    _placeQuery.text = place.label;
                    _places = const [];
                  });
                },
              ),
          ],
        // Церемония рисует себя целиком и не пользуется общей рамкой шага:
        // у неё нет ни заголовка, ни кнопки.
        _Step.ceremony => const [],
      };

  Widget _cta(L l) {
    final isLast = _step == _Step.place;
    final enabled = !_saving &&
        (!isLast || _place != null) &&
        !(_step == _Step.date && !_dateComplete) &&
        !(_step == _Step.date && _dateImpossible) &&
        !(_step == _Step.time && _timeHalfGiven);
    // **Кнопка продукта, а не своя.** Здесь стояла плоская золотая заливка с
    // тёмной подписью — ровно та, которую дизайн-система запрещает словом
    // «никогда» (`gold_texture.dart`). В эталоне и эта кнопка тёмная,
    // текстурная, с подписью слоновой костью; отличается она от остальных
    // только формой — 15 вместо пилюли.
    //
    // Выключенное состояние `AlmaButton` берёт на себя: `onTap: null` гасит её
    // до 0.45 и отключает нажатие, — а до этого золото горело всегда, и на
    // шаге даты человек видел горящую кнопку, которая не отвечает.
    return AlmaButton(
      label: isLast ? l.journeyBuildMySky : l.journeyContinueCta,
      radius: AlmaPalette.buttonRadius,
      onTap: enabled
          ? () {
              if (isLast) {
                // Небо строится — ощутимый толчок под пальцем, дальше церемония
                // ведёт свой ритм битами (тактильные там уже есть).
                HapticFeedback.mediumImpact();
                // На церемонию уходят сразу, а сохранение стартует под ней:
                // экран не ждёт сети, чтобы показать, что за человека взялись.
                setState(() => _step = _Step.ceremony);
                _build();
              } else {
                HapticFeedback.selectionClick();
                setState(() => _step = _Step.values[_step.index + 1]);
              }
            }
          : null,
    );
  }


  /// Карточка варианта V0 — по разметке холста: высота 62, радиус 16, глиф
  /// засечной антиквой и подпись Playfair 17.5. Вариант здесь — не пункт
  /// настроек, а имя того, за чем человек пришёл, и антиква ставит его в один
  /// ряд с названиями глав, которые он увидит следом.
  Widget _interestCard({
    required String glyph,
    required String label,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        height: 62,
        padding: const EdgeInsets.symmetric(horizontal: 17),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected
                ? const Color(0xFFE4C48A).withValues(alpha: 0.6)
                : AlmaPalette.body.withValues(alpha: 0.12),
          ),
          gradient: selected
              ? LinearGradient(colors: [
                  AlmaPalette.gold.withValues(alpha: 0.16),
                  AlmaPalette.gold.withValues(alpha: 0.03),
                ])
              : null,
        ),
        child: Row(children: [
          Text(glyph,
              style: AlmaType.displayL.copyWith(
                  fontSize: 17,
                  height: 1,
                  color: selected
                      ? AlmaPalette.goldBright
                      : AlmaPalette.gold.withValues(alpha: 0.7))),
          const SizedBox(width: 13),
          Expanded(
            child: Text(label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AlmaType.displayL.copyWith(
                    fontSize: 17.5,
                    height: 1.2,
                    color: selected
                        ? AlmaPalette.inkLight
                        : const Color(0xFFF6F1E4).withValues(alpha: 0.85))),
          ),
          if (selected)
            Text('✓',
                style: AlmaType.meta
                    .copyWith(fontSize: 13, color: AlmaPalette.gold)),
        ]),
      ),
    );
  }

  Widget _choice(String label,
      {required bool selected, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          border: Border.all(
              color: selected ? AlmaPalette.gold : AlmaPalette.hairline),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label,
            style: AlmaType.body.copyWith(
                color: selected ? AlmaPalette.goldBright : AlmaPalette.body)),
      ),
    );
  }
}

/// Найденное место — строка списка, а не кнопка.
///
/// **Раньше это были капсулы с обводкой**, теми же, какими нарисованы «женский
/// / мужской» и «не знаю времени». Разница существенная: там выбор из трёх
/// заранее известных ответов, здесь — список находок, который меняется на
/// каждую набранную букву. Пять обведённых капсул под полем ввода читаются
/// пятью кнопками равного веса, и среди них теряется первая — та, которая в
/// девяти случаях из десяти и есть ответ.
///
/// В эталоне у списка два тихих различителя вместо рамок: метка слева и
/// яркость подписи. Лучшее совпадение помечено золотой звёздочкой и написано
/// светлее (`starFill`), остальные — тусклой точкой и приглушённым текстом.
/// Галочка справа появляется у выбранного.
class _PlaceRow extends StatelessWidget {
  const _PlaceRow({
    required this.label,
    required this.best,
    required this.selected,
    required this.onTap,
  });

  final String label;

  /// Первая находка. Метка ярче и подпись светлее — это подсказка, а не
  /// предвыбор: нажать всё равно нужно.
  final bool best;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        // Высота строки в эталоне 51 при одной строке подписи. Здесь она
        // нижняя граница, а не размер: наши названия длиннее нарисованных —
        // «Berlin Köpenick, State of Berlin, Germany» в одну строку не встаёт,
        // — и обрезать город многоточием значит прятать от человека ровно то,
        // чем одна находка отличается от другой.
        constraints: const BoxConstraints(minHeight: 51),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              best ? '✦' : '·',
              style: AlmaType.meta.copyWith(
                fontSize: 10,
                color: best
                    ? AlmaPalette.gold
                    : AlmaPalette.gold.withValues(alpha: 0.35),
              ),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Text(
                label,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: AlmaType.headingM.copyWith(
                  fontSize: 16,
                  color: best
                      ? AlmaPalette.starFill
                      : AlmaPalette.body.withValues(alpha: 0.85),
                ),
              ),
            ),
            if (selected)
              Text('✓',
                  style: AlmaType.meta
                      .copyWith(fontSize: 13, color: AlmaPalette.gold)),
          ],
        ),
      ),
    );
  }
}

/// Развилка перевода часов — встречный вопрос неба, а не шаг анкеты.
///
/// **У неё нет номера, и это решение владельца.** «IV / VI» из первой редакции
/// макета обещало бы шаг времени, до которого уже не вернуться; «V / VI»
/// солгало бы иначе — это не шестая часть анкеты. Вопрос возникает после
/// «Построить моё небо», когда расчёт упёрся в двойное 02:30, поэтому сверху
/// стоит оверлайн «о времени рождения», а стрелка ведёт назад на шаг времени.
///
/// Два варианта различаются **не временем** — оно одинаковое, в этом вся
/// суть, — а именем, которое часы носили в ту ночь. Имена приходят с сервера:
/// базы часовых поясов у телефона нет.
class _Fork extends StatelessWidget {
  const _Fork({
    required this.fork,
    required this.time,
    required this.city,
    required this.onChoose,
    required this.onBack,
  });

  final AmbiguousBirthTime fork;
  final String time;
  final String city;
  final ValueChanged<String> onChoose;
  final VoidCallback onBack;

  /// Размер склейки словами. Захардкоженного «часом позже» здесь быть не
  /// может: переводы на полчаса существуют — остров Лорд-Хау и подобные, — и
  /// строка, уверенно называющая час, была бы там просто неправдой.
  String _delta(L l) =>
      (fork.gapHours ?? 1).abs() < 0.75 ? l.dstDeltaHalfHour : l.dstDeltaHour;

  /// Дата перевода — так, как её пишут в этой локали. Сервер присылает
  /// «1992-09-27»; показывать человеку ISO значит показывать ему машину.
  String _date(L l) {
    final raw = DateTime.tryParse(fork.transitionLocalDate);
    if (raw == null) return fork.transitionLocalDate;
    return DateFormat.yMMMMd(l.localeName).format(raw);
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final delta = _delta(l);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const SizedBox(height: 12),
        Row(children: [
          Text(l.dstOverline.toUpperCase(), style: AlmaType.overline),
          const Spacer(),
          IconButton(
            onPressed: onBack,
            icon: const Icon(Icons.arrow_back, color: AlmaPalette.gold),
          ),
        ]),
        const Spacer(),
        Text(l.dstTitle(time), style: AlmaType.displayL),
        const SizedBox(height: 18),
        Text(l.dstBody(city, _date(l), time), style: AlmaType.meta),
        const SizedBox(height: 26),
        _Choice(
          title: l.dstEarlier,
          note: l.dstEarlierSub(time, fork.earlier?.abbreviation ?? ''),
          onTap: () => onChoose('earlier'),
        ),
        const SizedBox(height: 14),
        _Choice(
          title: l.dstLater,
          note: l.dstLaterSub(time, fork.later?.abbreviation ?? '', delta),
          onTap: () => onChoose('later'),
        ),
        const SizedBox(height: 20),
        // Тому, кто не знает, тоже нужен выход — и честный: разница в час
        // сдвигает дома, а не переписывает карту.
        Text(
          l.dstFooter(delta),
          style: AlmaType.meta.copyWith(
              fontSize: 12, color: AlmaPalette.body.withValues(alpha: 0.5)),
        ),
        const Spacer(),
        const SizedBox(height: 24),
      ]),
    );
  }
}

/// Один из двух моментов: титул засечным, под ним — чем он отличается.
class _Choice extends StatelessWidget {
  const _Choice({required this.title, required this.note, required this.onTap});

  final String title;
  final String note;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          decoration: BoxDecoration(
            border: Border.all(color: AlmaPalette.hairline),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: AlmaType.headingM.copyWith(fontSize: 17)),
            const SizedBox(height: 4),
            Text(note, style: AlmaType.meta),
          ]),
        ),
      );
}

/// Шестой шаг: восемь ударов, за которые считаются восемь систем.
///
/// Порт `JourneyCeremonyStep.swift`. Числа оттуда же и не округлены: удар
/// первый показывается сразу, каждый следующий через 1150 мс, после восьмого
/// ещё 1400 мс — итого 9,45 секунды. Семь мягких тиков на ударах со второго по
/// восьмой (на первом тика нет: он уже на экране, когда сцена появилась) и
/// один тяжёлый в конце.
///
/// **Кнопки «пропустить» нет, и это решение.** Пропуск прыгал через
/// единственный экран, где системы действительно считаются, — и оставлял
/// человека перед пустым кабинетом, который ещё не успел ничего получить.
class _Ceremony extends StatefulWidget {
  const _Ceremony({required this.onDone, this.paused = false});

  final VoidCallback onDone;

  /// Небо задало встречный вопрос: отсчёт стоит, но ничего не забыто.
  final bool paused;

  @override
  State<_Ceremony> createState() => _CeremonyState();
}

class _CeremonyState extends State<_Ceremony> {
  int _beat = 1;
  bool _stopped = false;

  @override
  void initState() {
    super.initState();
    _play();
  }

  @override
  void dispose() {
    _stopped = true;
    super.dispose();
  }

  Future<void> _play() async {
    for (var next = 2; next <= 8; next++) {
      await Future<void>.delayed(const Duration(milliseconds: 1150));
      if (_stopped || !mounted) return;
      // Пауза — это ожидание, а не выход: удар, до которого дошли, остаётся, и
      // после ответа сцена продолжает с него же.
      while (widget.paused && !_stopped && mounted) {
        await Future<void>.delayed(const Duration(milliseconds: 120));
      }
      if (_stopped || !mounted) return;
      setState(() => _beat = next);
      HapticFeedback.selectionClick();
    }
    await Future<void>.delayed(const Duration(milliseconds: 1400));
    if (_stopped || !mounted) return;
    HapticFeedback.heavyImpact();
    widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(
          AlmaMetrics.pad, 0, AlmaMetrics.pad, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: 360,
            width: double.infinity,
            // Рисунок один на всю церемонию и не меняется с ударом: восемь
            // разных картинок за девять секунд читались бы как мигание.
            child: Center(child: WritingArt(size: 300, seed: 7)),
          ),
          // Резерв под самую длинную из восьми строк: без него рисунок
          // прыгал бы вверх на каждой, что переносится на третью строку.
          ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 116),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_label(l, _beat).toUpperCase(), style: AlmaType.overline),
                const SizedBox(height: 14),
                Text(
                  _line(l, _beat),
                  style: AlmaType.displayL.copyWith(
                      fontSize: 22, fontStyle: FontStyle.italic, height: 1.32),
                ),
              ],
            ),
          ),
          const Spacer(),
          // Восемь полосок: сколько прошло и сколько осталось, без процентов
          // и без вращающегося круга.
          Row(children: [
            for (var i = 1; i <= 8; i++) ...[
              Expanded(
                child: AnimatedContainer(
                  duration: AlmaMotion.ui,
                  height: 2,
                  color: i <= _beat
                      ? AlmaPalette.gold
                      : AlmaPalette.body.withValues(alpha: 0.16),
                ),
              ),
              if (i < 8) const SizedBox(width: 5),
            ],
          ]),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  static String _label(L l, int beat) => switch (beat) {
        1 => l.journeyCeremony1Label,
        2 => l.journeyCeremony2Label,
        3 => l.journeyCeremony3Label,
        4 => l.journeyCeremony4Label,
        5 => l.journeyCeremony5Label,
        6 => l.journeyCeremony6Label,
        7 => l.journeyCeremony7Label,
        _ => l.journeyCeremony8Label,
      };

  static String _line(L l, int beat) => switch (beat) {
        1 => l.journeyCeremony1Line,
        2 => l.journeyCeremony2Line,
        3 => l.journeyCeremony3Line,
        4 => l.journeyCeremony4Line,
        5 => l.journeyCeremony5Line,
        6 => l.journeyCeremony6Line,
        7 => l.journeyCeremony7Line,
        _ => l.journeyCeremony8Line,
      };
}
