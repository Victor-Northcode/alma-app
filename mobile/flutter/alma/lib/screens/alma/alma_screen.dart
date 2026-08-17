import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import '../../design/alma_presence.dart';
import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/tab_bar.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/ask_alma.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
import '../today/today_screen.dart' show openOffer;
import 'chat_turn.dart';
import 'thread_screen.dart';

/// Беседа с Alma.
///
/// Порт `mobile/ios/Alma/Screens/Alma/AlmaScreen.swift`. Вступление собрано из
/// собственной карты человека — «Луна у меня — Дева. Что ей на самом деле
/// нужно?» — потому что чужой вопрос не приглашает, а свой уже наполовину
/// задан. Под каждым ответом стоит цитата позиций: это обещание продукта, и
/// экран без неё нарушал бы то, что сам продукт печатает о себе.
class AlmaScreen extends StatefulWidget {
  const AlmaScreen({super.key, required this.tabs});

  /// Бар вкладок, который на этой одной вкладке живёт оверлеем. Грабер под
  /// композером — единственный способ его позвать; см. [TabsPeek].
  final TabsPeek tabs;

  @override
  State<AlmaScreen> createState() => _AlmaScreenState();
}

class _Turn {
  _Turn({
    required this.mine,
    required this.body,
    this.citedFactors = const [],
    this.arriving = false,
    this.kind,
  });
  final bool mine;
  final String body;
  final List<String> citedFactors;

  /// Какого рода этот ответ: чтение, тихий отказ карты, разговор или забота.
  ///
  /// **Живая лента получила это последней, и потому отдельной строкой.** Разбор
  /// `turn_kind` и правила показа приехали вместе, но архив беседы подключили
  /// сразу, а здесь поле некуда было положить — файл в тот момент правили под
  /// свет. Пока поля не было, тихий ответ рисовался как обычный: `care` — это
  /// проза без цитаты, и приписывать ей «прочитано из» значит обещать
  /// основание там, где Alma намеренно говорит от себя.
  final ChatTurnKind? kind;

  /// Ответ пришёл в эту сессию и ещё не оседал — см. `ChatTurnView.arriving`.
  final bool arriving;
}

class _AlmaScreenState extends State<AlmaScreen>
    with WidgetsBindingObserver, TickerProviderStateMixin {
  final _draft = TextEditingController();
  final _scroll = ScrollController();

  /// Фокус композера. Нужен не оформлению, а вступительным вопросам: нажатие
  /// на один из них **заполняет поле**, и без фокуса человек остался бы перед
  /// заполненным полем и закрытой клавиатурой, не понимая, отправилось это или
  /// нет.
  final _focus = FocusNode();

  final List<_Turn> _turns = [];
  List<String> _openers = const [];

  /// Что показывает A2. Дома и тела пусты, пока сервер не отдаёт стадию
  /// работы (`{stage, name}` из §8): выдумывать «читаю твой четвёртый дом»
  /// нельзя. Позиции — карта самого человека, и они известны честно.
  ThinkingStage _stage = const ThinkingStage();


  String? _threadId;
  bool _sending = false;

  /// Сколько вопросов осталось. `null` — сервер ещё не говорил, и до первого
  /// ответа лимит не показывается: пустой счётчик над полем — это счётчик,
  /// который врёт.
  int? _left;

  /// Последний отказ — **не реплика Alma**, а то, что сделала система.
  ///
  /// Раньше отказ дописывался в ленту как ответ Alma: «Что-то не работает на
  /// моей стороне» вставало под подписью «ALMA» рядом с цитатой позиций, то
  /// есть системная поломка получала её голос — и оставалась в переписке
  /// навсегда, потому что на сервере её нет и после перезагрузки она исчезала.
  /// Держим отдельно, как `ChatModel.refusal` на нативе.
  AlmaError? _refusal;

  /// Фраза сервера про исчерпанный лимит. Она уже переведена и — в отличие от
  /// нашей — называет, **когда** вопросы вернутся; поэтому стена печатает её, а
  /// свою общую строку оставляет на случай, когда сервер промолчал.
  String? _limitSentence;

  /// Прошлые беседы, свежая первой — то, из чего строится меню «раньше».
  List<ChatThreadRef> _past = const [];
  bool _openersLoaded = false;
  bool _threadLoaded = false;

  /// **Наклон света на отправку.** §1 спеки: «На отправку вопроса свет
  /// „наклоняется“: яркость +15 % за 240 мс»; §4 повторяет длительность в
  /// словаре движения. Это единственная реакция света на действие человека —
  /// всё остальное он делает сам, на своих часах.
  ///
  /// Часы живут на экране, а не в самом свете: наклон обязан пережить и
  /// отправку, и смену приветствия лентой (см. [_presence]).
  late final AnimationController _tilt = AnimationController(
    vsync: this,
    duration: AlmaMotion.ui,
  );

  /// Куда сесть свету в приветствии (A1) и в думании (A2).
  ///
  /// Свет один, а мест два, и живёт он **выше** обоих состояний — см.
  /// [_presence]. Состояния объявляют только место и размер: приветствие —
  /// дырку 64 по центру, думание — дырку в коробку кольца 110.
  final LayerLink _greetingSlot = LayerLink();
  final LayerLink _thinkingSlot = LayerLink();

  @override
  void initState() {
    super.initState();
    // Вопрос, с которым сюда пришли с другого экрана (читалка гороскопа, `R2`).
    // Подставляем в поле и **гасим признак** — он одноразовый: оставленный
    // гореть, он подставлял бы тот же вопрос при каждом возврате на вкладку.
    // Не отправляем: вопросов в день три, и потратить один за человека,
    // который ещё не дочитал предложение, — ловушка, а не услуга.
    almaDraft.addListener(_takeDraft);
    // **И один раз при появлении.** Одной подписки мало: страницы `PageView`
    // строятся по мере приближения, и вкладка Alma — третья, то есть в момент
    // нажатия на карточку в читалке её состояния ещё не существует. Признак
    // ставится, слушать его некому, вопрос теряется — проверено на симуляторе,
    // поле оставалось пустым. Значит забираем и то, что уже лежит.
    //
    // Кадром позже: `setState` из `initState` — построение дерева во время
    // построения дерева.
    WidgetsBinding.instance.addPostFrameCallback((_) => _takeDraft());
    // **Экран смотрит на окно и обязан узнавать, что окно изменилось.**
    //
    // Низ этой вкладки считается от окна, а не от `MediaQuery` тела (почему —
    // в `build`), а `View.of` ни на что не подписывает: без наблюдателя приход
    // клавиатуры не перестраивал бы экран вовсе — грабер оставался бы стоять
    // под клавиатурой, и найти это можно было бы только руками на устройстве.
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeMetrics() => setState(() {});

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // **Вкладка живёт с самого запуска, а сессия к тому моменту ещё грузится.**
    //
    // `IndexedStack` создаёт все четыре экрана сразу, поэтому первый вызов
    // приходит с пустым профилем: беседы у такого «человека» нет по
    // определению, и загрузка молча не делалась. `SessionScope` — это
    // `InheritedNotifier`, он позовёт сюда снова, когда данные придут, и вот
    // тогда есть чему грузиться. Свой флаг, потому что вступительные вопросы
    // и беседа готовы в разные моменты.
    final session = SessionScope.of(context);
    if (!_openersLoaded) {
      _openersLoaded = true;
      _loadOpeners();
    }
    if (!_threadLoaded && session.hasBirthData) {
      _threadLoaded = true;
      _loadLastThread();
    }
  }

  /// **Последняя беседа поднимается с сервера, а не начинается заново.**
  ///
  /// Реплики хранятся на сервере — `/v1/chat/threads` их отдаёт, и натив
  /// открывает вкладку на том, что человек уже спросил. Порт эти эндпоинты не
  /// звал вовсе: после перезапуска приложения вкладка Alma каждый раз
  /// встречала вступлением, будто разговора не было, а ответы, за которые
  /// заплачено, оставались лежать на сервере невидимыми. Сверено кадрами:
  /// натив показывал переписку, порт — «Спроси меня о чём угодно».
  Future<void> _loadLastThread() async {
    final session = SessionScope.of(context);
    if (!session.hasBirthData) return;
    try {
      final threads = await session.client.threads();
      if (mounted) setState(() => _past = threads);
      if (threads.isEmpty) return;
      final turns = await session.client.thread(threads.first.id);
      if (!mounted || turns.isEmpty) return;
      setState(() {
        _threadId = threads.first.id;
        _turns
          ..clear()
          ..addAll(turns.map((t) => _Turn(
                mine: t.mine,
                body: t.body,
                citedFactors: t.citedFactors,
                kind: t.kind,
              )));
      });
      _scrollDown();
    } on AlmaError {
      // Молча: беседа — не то, ради чего экран обязан ругаться. Вступление
      // остаётся на месте, вопрос можно задать заново.
    }
  }

  /// Вступительные вопросы — из натальной карты, с запасом из каталога, когда
  /// карта ещё не посчитана или в ней нет нужной точки.
  Future<void> _loadOpeners() async {
    final session = SessionScope.of(context);
    final l = L.of(context);
    final fallback = [l.scrChatPrompt1, l.scrChatPrompt2, l.scrChatPrompt3];
    if (!session.hasBirthData) {
      setState(() => _openers = fallback);
      return;
    }
    try {
      final natal = await session.client.compute(SystemSlug.natal);
      final data = natal.data;
      final questions = <String>[];
      if (data['moon_sign'] is String) {
        questions.add(l.scrChatPromptMoon(
            CabinetWordsMore.sign(l, data['moon_sign'] as String)));
      }
      if (data['sun_sign'] is String) {
        questions.add(l.scrChatPromptSun(
            CabinetWordsMore.sign(l, data['sun_sign'] as String)));
      }
      if (data['rising_sign'] is String) {
        questions.add(l.scrChatPromptRising(
            CabinetWordsMore.sign(l, data['rising_sign'] as String)));
      }
      for (final extra in fallback) {
        if (questions.length >= 3) break;
        questions.add(extra);
      }
      if (mounted) {
        setState(() {
          _openers = questions.take(3).toList();
          // Позиции под строкой думания — настоящие: две первые из карты,
          // обрезанные до головы мета-строки (тело + градус + знак); дом и
          // достоинство в такой строке лишние. Что именно движок читает в эту
          // секунду, клиент не знает и не выдумывает — см. `ThinkingStage`.
          _stage = ThinkingStage(
            factors: [
              for (final raw in natal.factors.take(2))
                CabinetWordsMore.factor(l, raw).split(' · ').first,
            ],
          );
        });
      }
    } on AlmaError {
      if (mounted) setState(() => _openers = fallback);
    }
  }

  Future<void> _send(String text) async {
    final message = text.trim();
    if (message.isEmpty || _sending) return;
    final session = SessionScope.of(context);
    // Реплика человека встаёт в ленту до похода на сервер: это его собственные
    // слова, тут нечего выдумывать, а вопрос, пропавший на восемь секунд,
    // читается как несостоявшаяся отправка.
    final pending = _Turn(mine: true, body: message);
    setState(() {
      _turns.add(pending);
      _refusal = null;
      _sending = true;
      _draft.clear();
    });
    // Свет откликается на ушедший вопрос — тот же жест, что поворот головы на
    // голос. Наклон держится, пока она не ответила: голова, повернувшаяся на
    // зов и тут же отвернувшаяся, — это не «слушаю», а «дёрнулась».
    _tilt.forward();
    _scrollDown();
    try {
      final reply = await session.client.ask(
        message,
        threadId: _threadId,
        locale: session.locale,
      );
      if (!mounted) return;
      setState(() {
        _threadId = reply.threadId ?? _threadId;
        _left = reply.questionsLeft ?? _left;
        _turns.add(_Turn(
          mine: false,
          body: reply.body,
          citedFactors: reply.citedFactors,
          kind: reply.kind,
          arriving: true,
        ));
      });
    } on AlmaError catch (error) {
      if (!mounted) return;
      setState(() {
        // **Вопрос возвращается в поле, а не теряется.** Тому, кому только что
        // сказали, что вопросы кончились, не хватало ещё набирать свой вопрос
        // заново.
        _turns.remove(pending);
        _draft.text = message;
        if (_isLimit(error)) {
          // Лимит — не сообщение в ленте, а **стена**: она встаёт на место
          // композера и продаёт план (s31). Ноль здесь ставим сами, потому что
          // на отказе `questions_left` уже не приходит, а сервер только что
          // сказал ровно это.
          _left = 0;
          _limitSentence = error is ServerRefused && error.message.isNotEmpty
              ? error.message
              : null;
          // У подписчика стены не будет — звать его купить подписку значит
          // показать, что мы не знаем, кто перед нами. Его месячные тридцать
          // тоже кончаются, и тогда фраза сервера (в ней сказано, когда они
          // вернутся) остаётся единственным, что объясняет молчание.
          if (session.isSubscriber) _refusal = error;
        } else {
          _refusal = error;
        }
      });
    } finally {
      if (mounted) {
        setState(() => _sending = false);
        // Она ответила — свет отпускает наклон и возвращается к своему
        // дыханию.
        _tilt.reverse();
      }
      _scrollDown();
    }
  }

  /// Отказ по исчерпанному лимиту. Коды — те же, что перечислены в
  /// `AlmaClient` как «фраза заведомо переведена»: сервер отвечает на них 503,
  /// и без разбора кода это выглядело бы как поломка на его стороне.
  static bool _isLimit(AlmaError error) =>
      error is ServerRefused && (error.code?.startsWith('question_limit') ?? false);

  /// Отказ, сказанный так, как сказала бы Alma.
  ///
  /// Порт `RefusalView`: код статуса — не голос. Три поломки, которые человек
  /// здесь действительно встречает, имеют по своей фразе в каталоге; фраза
  /// сервера остаётся только там, где она заведомо переведена и говорит
  /// больше нашей.
  String _refusalSentence(L l, AlmaError error) {
    switch (error) {
      case NetworkDown():
        return l.scrChatOffline;
      case ServerRefused(:final status, :final message, :final code):
        if (code == 'answer_refused') return l.scrChatRefused;
        if (message.isNotEmpty) return message;
        return status >= 500 ? l.scrChatUnavailable : l.scrChatWentWrong;
      default:
        return l.scrChatWentWrong;
    }
  }

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: AlmaMotion.ui,
          curve: AlmaMotion.uiCurve,
        );
      }
    });
  }

  /// Вопрос пришёл с другого экрана — подставить в поле.
  void _takeDraft() {
    final question = almaDraft.value;
    if (question == null || !mounted) return;
    almaDraft.value = null;
    setState(() => _draft.text = question);
    _focus.requestFocus();
  }

  @override
  void dispose() {
    almaDraft.removeListener(_takeDraft);
    WidgetsBinding.instance.removeObserver(this);
    _tilt.dispose();
    _draft.dispose();
    _scroll.dispose();
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final session = SessionScope.of(context);
    // **Низ этой вкладки считается от окна, а не от окружения.**
    //
    // Оболочка — `Scaffold(extendBody: true)` с баром в `bottomNavigationBar`,
    // и такой Scaffold кладёт в `MediaQuery` тела полную высоту бара вместе с
    // домашним индикатором: 86 точек там, где у окна 34. На трёх вкладках это
    // ровно то, что нужно, — там бар стоит. Здесь его нет: он уехал за кромку
    // и ждёт зова, а отступ в рост отсутствующего бара оставил бы под
    // композером полосу пустой ночи — ту самую дыру на месте того, чего нет.
    // Окно не зависит от того, что с отступом сделали Scaffold и SafeArea по
    // дороге.
    //
    // **Клавиатуру приходится спрашивать там же.** `resizeToAvoidBottomInset`
    // вычитает её из тела и **стирает** `viewInsets` из его `MediaQuery`:
    // изнутри её высота всегда ноль. Поднимать композер руками поэтому не
    // нужно — тело уже стоит на её кромке; нужен сам факт, что она открыта.
    final view = MediaQueryData.fromView(View.of(context));
    final typing = view.viewInsets.bottom > 0;

    return NightSky(
      mood: SkyMood.reading,
      seed: 0x414C4D43,
      child: SafeArea(
        bottom: false,
        child: Padding(
          // В покое — место домашнего индикатора, и оно **под грабером**:
          // композер с ручкой садятся на индикатор, а не парят над ним.
          // При открытой клавиатуре — только воздух над её кромкой.
          padding: EdgeInsets.only(bottom: typing ? 8 : view.padding.bottom),
          child: Column(children: [
            _header(l),
            Expanded(
              // Свет лежит **поверх** состояния и не входит в его разметку:
              // ниже он не сможет пережить смену приветствия лентой, а пережить
              // обязан — см. [_presence].
              child: Stack(children: [
                Positioned.fill(
                  child: _turns.isEmpty ? _opening(l, session) : _transcript(l),
                ),
                // **Оба ребёнка размещены — иначе стопка мерилась бы по
                // свету.** `Stack` берёт размер у неразмещённого ребёнка, а
                // колонка выше выдаёт ширину свободной (её выравнивание — по
                // центру): беседа получала ровно 64 точки ширины — рост
                // приветственного света — и ответ рассыпался в столбик из
                // одного слова. Свету место здесь безразлично: он всё равно
                // рисуется там, где нашлась его дырка.
                Positioned(left: 0, top: 0, child: _presence()),
              ]),
            ),
            _limitWall(l, session) ?? _composer(l),
            // **Грабер — под композером и только когда не пишут.**
            //
            // Клавиатура забирает низ экрана целиком: ручка над её кромкой
            // предлагала бы уйти с вкладки ровно тому, кто набирает вопрос, и
            // отнимала бы у него строку. Черновик при этом никуда не девается
            // — он живёт в `_draft`, а не в разметке, — и приезд бара, уход
            // бара и появление ручки его не касаются.
            if (!typing) TabsGrabber(peek: widget.tabs),
          ]),
        ),
      ),
    );
  }

  /// **Свет один на всю беседу и живёт выше её состояний.**
  ///
  /// Он принадлежал каждому состоянию отдельно: приветствие рисовало свой свет
  /// 64, думание — свой 70 в кольце. Отправка вопроса меняет приветствие лентой
  /// **в том же кадре**, в котором свет должен наклониться, — и наклонять было
  /// нечего: виджет с часами наклона снимался с дерева прямо посреди анимации.
  /// Поэтому свет вынесен в каркас, а состояния оставили себе только место и
  /// размер: приветствие — дырку по центру, думание — дырку в коробку кольца.
  ///
  /// Место берётся [LayerLink]'ом, а не отступом. Дырка живёт внутри списка и
  /// ездит вместе с ним, а свет висит поверх — связать их числом значит на
  /// каждом кадре мерить чужую прокрутку; `CompositedTransformFollower`
  /// переносит свет туда, где нарисовалась дырка, сам. Слота два, а не один
  /// [LayerLink] на оба: в кадре пересменки старая дырка ещё жива, а новая уже
  /// родилась, и один линк на двоих упал бы утверждением о двух ведущих слоях.
  ///
  /// Заодно это то, ради чего дыхание не перезапускается сменой настроения
  /// (`_AlmaPresenceState._sync`): свет один и тот же, он не рождается заново —
  /// он переходит из ожидания в работу.
  Widget _presence() {
    final thinking = _sending;
    return IgnorePointer(
      child: CompositedTransformFollower(
        link: thinking ? _thinkingSlot : _greetingSlot,
        // Дырки нет — свет не рисуется вовсе. В осевшей ленте своего света у
        // экрана нет: там его место в шапке каждого ответа, и тот принадлежит
        // ответу (§7: «при скролле треда шапочный свет не следует»).
        showWhenUnlinked: false,
        child: AnimatedBuilder(
          animation: _tilt,
          builder: (context, _) => AlmaPresence(
            size: thinking ? AlmaPresence.thinking : AlmaPresence.greeting,
            mood: thinking ? PresenceMood.thinking : PresenceMood.calm,
            tilt: _tilt.value,
          ),
        ),
      ),
    );
  }

  /// «Нужно больше данных» — не отказ, а форма.
  ///
  /// Порт `NeedMore`. Ничего не сломалось: данных ещё не дали, и ответ на это —
  /// то, чем их дают, а не извинение с кнопкой «повторить».
  Widget _needMore(String message, String action, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(message, style: AlmaType.voice),
          const SizedBox(height: 16),
          AlmaButton(
            kind: AlmaButtonKind.outline,
            fills: false,
            label: action,
            onTap: onTap,
          ),
        ],
      ),
    );
  }

  /// Вступление: присутствие, две фразы голосом и три вопроса из карты.
  Widget _opening(L l, AlmaSession session) {
    return ListView(
      controller: _scroll,
      padding: const EdgeInsets.symmetric(
          horizontal: AlmaMetrics.pad, vertical: AlmaMetrics.gapLarge),
      children: [
        // A1: место света 64 по центру — размер спеки. Сам свет живёт в
        // каркасе экрана ([_presence]) и садится сюда; приветствию остаётся
        // объявить, где и какого он тут размера.
        Center(
          child: CompositedTransformTarget(
            link: _greetingSlot,
            child: const SizedBox.square(dimension: AlmaPresence.greeting),
          ),
        ),
        const SizedBox(height: 18),
        Text(
          session.hasBirthData ? l.scrChatOpening : l.scrChatNoChart,
          style: AlmaType.voice,
        ),
        const SizedBox(height: 12),
        // Тихая строка под гаснущим разделителем — из спеки, §2 A1.
        Text(l.chatNotTemplate, style: AlmaType.meta),
        // **Без карты — форма, а не три вопроса.** Вопросы вида «Луна у меня —
        // Дева» человеку без рождения предлагать нечего: они собраны из карты,
        // которой нет. На их месте — то, чем эту карту дают.
        if (!session.hasBirthData)
          _needMore(l.cabNoBirthData, l.cabAddBirthData, () {
            // Анкету открывает оболочка, увидев пустой профиль: своего
            // маршрута к ней у вкладки нет и быть не должно — она полноэкранная
            // церемония, а не страница поверх кабинета.
          }),
        if (session.hasBirthData && _openers.isNotEmpty) ...[
          const SizedBox(height: AlmaMetrics.gapLarge),
          Text(l.scrChatCouldAsk.toUpperCase(), style: AlmaType.overline),
          const SizedBox(height: 10),
          for (final prompt in _openers)
            InkWell(
              // **Нажатие заполняет поле, а не отправляет.** Вопросов в день
              // три; тот, кто ткнул в строку посмотреть, что это, потратил бы
              // на этом треть дневной нормы — это ловушка, а не приглашение.
              // Так же на нативе: `model.draft = prompt; composing = true`.
              onTap: () {
                _draft.text = prompt;
                _focus.requestFocus();
              },
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 14),
                decoration: BoxDecoration(
                  border:
                      Border(bottom: BorderSide(color: AlmaPalette.hairline)),
                ),
                child: Row(children: [
                  Expanded(
                    child: Text(prompt,
                        style: AlmaType.body
                            .copyWith(color: AlmaPalette.body.withValues(alpha: 0.9))),
                  ),
                  // Между строкой и стрелкой на макете 10 (`gap:10px` в s6):
                  // без зазора стрелка прилипала к последнему слову длинного
                  // вопроса и читалась его частью, а не указателем строки.
                  const SizedBox(width: 10),
                  // Стрелка — тем же текстовым шрифтом, что и вопрос, 15
                  // пунктов и **полное** золото: `font:15px 'Golos Text';
                  // color:#C9AE6B`. Без семейства она бралась системным.
                  Text('→',
                      style: AlmaType.body.copyWith(
                          fontSize: 15, color: AlmaPalette.gold)),
                ]),
              ),
            ),
        ],
        // **Отказ виден и на пустом экране.** Первый же вопрос может не уйти —
        // сеть, отказ модели, — и тогда его реплика снимается из ленты, лента
        // снова пуста, и экран возвращается к вступлению. Без этой строки
        // единственное объяснение молчания исчезало вместе с ней: человек
        // видел свой вопрос обратно в поле и ни слова о том, почему.
        if (_refusal != null) _refusalView(l, _refusal!),
      ],
    );
  }

  /// Лента: мои реплики пилюлей справа, ответы Alma — засечным на всю ширину,
  /// с подписью «ALMA» и цитатой позиций под текстом.
  Widget _transcript(L l) {
    // Хвост ленты: пока идёт ответ — строка ожидания, после неудачи — отказ.
    // Одновременно их не бывает, поэтому это одна лишняя позиция, а не две.
    final tail = _sending || _refusal != null ? 1 : 0;
    return ListView.builder(
      controller: _scroll,
      // Лента начинается сразу под линейкой шапки: на макете (s7) у неё
      // `padding:6px 22px 0`, и то же на нативе — `.padding(.top, 6)`.
      // Стояли общие 16 сверху, и первая реплика проваливалась на десять точек
      // ниже, чем на эталоне: разговор начинался с дыры. Снизу — `gapLarge`,
      // чтобы последний ответ не упирался в композер.
      padding: const EdgeInsets.fromLTRB(
          AlmaMetrics.pad, 6, AlmaMetrics.pad, AlmaMetrics.gapLarge),
      itemCount: _turns.length + tail,
      itemBuilder: (context, i) {
        if (i == _turns.length) {
          if (_sending) return ThinkingView(stage: _stage, slot: _thinkingSlot);
          return _refusalView(l, _refusal!);
        }
        final turn = _turns[i];
        return ChatTurnView(
          mine: turn.mine,
          body: turn.body,
          citedFactors: turn.citedFactors,
          kind: turn.kind,
          // Оседает только ответ, пришедший в эту сессию и последним.
          arriving: turn.arriving && i == _turns.length - 1,
        );
      },
    );
  }

  /// Отказ в ленте: фраза телом, без подписи «ALMA» и без цитаты позиций.
  ///
  /// Подпись и цитата — обещание, что ответ прочитан из карты; ставить их над
  /// сообщением о мёртвой сети значит подписывать этим обещанием поломку.
  Widget _refusalView(L l, AlmaError error) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(_refusalSentence(l, error), style: AlmaType.body),
    );
  }

  /// Шапка вкладки: «ALMA», гаснущая линейка и — когда бесед больше одной —
  /// меню «раньше».
  ///
  /// **Меню, а не экран списка.** Бесед всегда единицы, каждая — одна строка,
  /// и отдельный экран, каждая строка которого заголовок, был бы экраном ради
  /// списка из одной вещи. Появляется только со второй беседой: пункт меню,
  /// ведущий на то же, что уже открыто, — это пункт, который нажимают один раз
  /// и больше никогда.
  Widget _header(L l) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(AlmaMetrics.pad, 14, AlmaMetrics.pad, 10),
      child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
        Text(l.tabAlma.toUpperCase(), style: AlmaType.overline),
        const SizedBox(width: 12),
        Expanded(
          child: Container(
            height: 1,
            color: AlmaPalette.gold.withValues(alpha: 0.28),
          ),
        ),
        if (_past.length > 1) ...[
          const SizedBox(width: 12),
          PopupMenuButton<ChatThreadRef>(
            color: AlmaPalette.night700,
            position: PopupMenuPosition.under,
            tooltip: l.scrChatPast,
            onSelected: (thread) => Navigator.of(context, rootNavigator: true).push(
              CupertinoPageRoute(
                builder: (context) =>
                    ThreadScreen(id: thread.id, title: thread.title),
              ),
            ),
            itemBuilder: (context) => [
              for (final thread in _past)
                PopupMenuItem(
                  value: thread,
                  child: Text(
                    thread.title?.isNotEmpty == true
                        ? thread.title!
                        : l.scrChatUntitled,
                    style: AlmaType.body.copyWith(fontSize: 15),
                  ),
                ),
            ],
            // На макете «earlier» — полужирная метка: `600 10.5px`. Вес у
            // вариативного шрифта задаётся осью, а не `fontWeight` (см.
            // `AlmaType`), и без неё слово выходило тоньше стоящей рядом
            // подписи «ALMA» — два надзаголовка одной строки разного веса.
            child: Text(l.scrChatPast.toUpperCase(),
                style: AlmaType.tag.copyWith(
                  color: AlmaPalette.gold,
                  fontWeight: FontWeight.w600,
                  fontVariations: const [FontVariation('wght', 600)],
                )),
          ),
        ],
      ]),
    );
  }

  /// Стена вместо поля, когда вопросы кончились.
  ///
  /// **Стена видна в ту секунду, когда потрачен последний вопрос.** Поле
  /// оставалось открытым на нуле, и отказ приходил только на следующее
  /// нажатие — владелец задал три вопроса и решил, что лимита нет вовсе.
  /// Композер, принимающий текст, который он откажется отправить, — это ложь
  /// вёрсткой; на нуле блок **и есть** стена, и стена продаёт план.
  ///
  /// `null` значит «стены нет» — тогда рисуется поле.
  Widget? _limitWall(L l, AlmaSession session) {
    if (_left != 0 || session.isSubscriber) return null;
    return Padding(
      padding: const EdgeInsets.fromLTRB(AlmaMetrics.pad, 12, AlmaMetrics.pad, 10),
      child: Column(children: [
        // Фраза сервера, когда она есть: она уже переведена и называет, **когда**
        // вопросы вернутся, — числа, которое этот экран иначе выводил бы из
        // тарифа и переврал бы в день, когда тарифы поменяются.
        Text(_limitSentence ?? l.scrChatOutOfQuestions,
            textAlign: TextAlign.center, style: AlmaType.meta),
        const SizedBox(height: 12),
        AlmaButton(
          kind: AlmaButtonKind.outline,
          fills: false,
          label: l.cabPlansCta,
          onTap: () => openOffer(context),
        ),
      ]),
    );
  }

  /// Рост поля и кнопки отправки — 52, скругление 26.
  ///
  /// Это **число композера**, а не общий рост полей продукта (54): на макете
  /// оно стоит дважды, в s6 и в s7 (`height:52px;border-radius:26px` и круг
  /// `52×52`). Композер — не строка анкеты: он живёт на самой кромке экрана,
  /// под ним ручка вкладок, и лишние две точки съедают воздух там, где его
  /// считали по макету.
  static const double _composerHeight = 52.0;

  Widget _composer(L l) {
    // Счётчик виден на последних трёх вопросах, и в этот момент верх у блока
    // **свой**: на макете композер без счётчика имеет `padding:12px 22px 6px`
    // (s6), а со счётчиком — `padding:0 22px 6px` (s7), потому что отступ уже
    // отдан строке счётчика. Одна и та же дюжина в обоих случаях уводила поле
    // вниз ровно тогда, когда над ним появлялась ещё одна строка.
    final counting = _left != null && _left! >= 1 && _left! <= 3;
    return Container(
      padding: EdgeInsets.fromLTRB(
          AlmaMetrics.pad, counting ? 0 : 12, AlmaMetrics.pad, 6),
      // **Композер парит, а не стоит на полке.**
      //
      // Волосяная линия сверху отрезала его от ленты, и поле читалось как блок
      // на подставке — «должен быть в невесомости». Разделителя нет: беседа
      // просто уходит под поле, а само поле держится на своей обводке.
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        // Счётчик появляется на последних трёх и молчит всё остальное время:
        // цифра над каждым вопросом превращает разговор в счётчик такси.
        // Прижат влево, к началу строки поля, — так он на макете (s7); по
        // центру он читался как заголовок композера, а не как примечание.
        if (counting)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(l.cabQuestionsLeft(_left!),
                textAlign: TextAlign.left, style: AlmaType.meta),
          ),
        Row(children: [
        Expanded(
          // **Поле — вся пилюля, а не строка текста внутри неё.**
          //
          // Строка ввода сжата до собственной высоты и стоит по центру
          // пятидесяти двух точек; без этого нажатие в верхнюю или нижнюю
          // треть обводки не попадало никуда — человек видел поле, тыкал в
          // него и не получал ни курсора, ни клавиатуры. Пилюля нарисована как
          // одна цель, и целью обязана быть целиком.
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: _focus.requestFocus,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              height: _composerHeight,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                border: Border.all(color: AlmaPalette.hairline),
                borderRadius: BorderRadius.circular(_composerHeight / 2),
              ),
              child: TextField(
                controller: _draft,
                focusNode: _focus,
                style: AlmaType.body.copyWith(color: AlmaPalette.inkLight),
                // **Поле само по себе ничего не отмеряет.** Высоту держит
                // обводка снаружи (52), и материаловские отступы ввода внутри
                // неё — второй рост: без `isDense` строка приносит свои
                // шестнадцать точек сверху и снизу и распирает пилюлю изнутри.
                decoration: InputDecoration(
                  hintText: l.scrChatPlaceholder,
                  hintStyle: AlmaType.meta,
                  border: InputBorder.none,
                  isDense: true,
                  contentPadding: EdgeInsets.zero,
                ),
                onSubmitted: _send,
                textInputAction: TextInputAction.send,
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        // Круг обведённый, а не залитый золотом: на нативе отправка — тихая
        // кнопка рядом с полем, а золотая заливка принадлежит дверям покупки.
        InkResponse(
          onTap: () => _send(_draft.text),
          child: Container(
            width: _composerHeight,
            height: _composerHeight,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: AlmaPalette.hairline),
            ),
            child: Center(
              // `font:19px 'Golos Text';color:rgba(237,231,218,.85)` — то же
              // семейство, что у остального текста композера; без него стрелка
              // рисовалась системным шрифтом и была другой формы.
              child: Text('→',
                  style: AlmaType.body.copyWith(
                      fontSize: 19,
                      height: 1.0,
                      color: AlmaPalette.body.withValues(alpha: 0.85))),
            ),
          ),
        ),
        ]),
      ]),
    );
  }
}
