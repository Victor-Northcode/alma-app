import 'dart:async';

import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/models.dart';
import '../../state/ask_alma.dart';
import '../cabinet_words.dart';

/// Читалка длинного гороскопа — `today-reading-spec §3` (R2).
///
/// **Чтение — это комната, а не карточка.** До неё гороскоп на две тысячи
/// знаков выливался прямо на «Сегодня» дисплейной антиквой: два экрана
/// прокрутки, полоса вкладок наезжала на текст, а блок областей уезжал за
/// сгиб. Спека разводит это на два места: на «Сегодня» остаётся лид, один
/// абзац и дверь, весь текст живёт здесь.
///
/// Поэтому маршрут отдельный и **полосы вкладок в нём нет**. Вкладка «Сегодня»
/// живёт прямо в корневом навигаторе, так что обычный `push` отсюда и закрывает
/// оболочку целиком — специально ничего прятать не нужно.
class TodayReadingScreen extends StatefulWidget {
  const TodayReadingScreen({
    super.key,
    required this.reading,
    required this.day,
  });

  final Reading reading;

  /// День, за который написан текст. Он же — ключ, под которым запоминается
  /// место чтения: вчерашняя позиция не должна открывать сегодняшний текст с
  /// середины.
  final DateTime day;

  @override
  State<TodayReadingScreen> createState() => _TodayReadingScreenState();
}

class _TodayReadingScreenState extends State<TodayReadingScreen> {
  /// Высота верхней панели с холста.
  static const _panel = 100.0;

  /// Поле колонки: одна мера строки, `§3`.
  static const _column = 22.0;

  static const _sizeKey = 'alma.reading.size';
  static String _placeKey(DateTime day) =>
      'alma.reading.at.${DateFormat('yyyy-MM-dd').format(day)}';

  final _scroll = ScrollController();

  /// Доля прочитанного — для полосы под шапкой и нити справа.
  ///
  /// Одно значение, два рисунка, как велит `§7`. Признаком, а не полем
  /// состояния: прокрутка сообщает о себе каждый кадр, и `setState` на каждый
  /// кадр перестраивал бы всю колонку текста ради двухточечной полоски.
  final ValueNotifier<double> _read = ValueNotifier(0);

  /// Ступень «Aa»: 0 мельче, 1 обычно, 2 крупнее.
  int _step = 1;
  bool _restored = false;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
    unawaited(_restore());
  }

  @override
  void dispose() {
    _scroll.removeListener(_onScroll);
    // Место чтения пишется и на уходе: человек может закрыть комнату кнопкой
    // сразу после прокрутки, до того как сработает отложенная запись.
    unawaited(_remember());
    _scroll.dispose();
    _read.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scroll.hasClients) return;
    final max = _scroll.position.maxScrollExtent;
    if (max <= 0) return;
    _read.value = (_scroll.offset / max).clamp(0.0, 1.0);
  }

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final step = prefs.getInt(_sizeKey);
    final at = prefs.getDouble(_placeKey(widget.day));
    if (!mounted) return;
    if (step != null && step >= 0 && step < AlmaType.readingSteps.length) {
      setState(() => _step = step);
    }
    // Возврат на «Сегодня» не сбрасывает место (`§3`). Прыгаем после кадра:
    // до первой раскладки у прокрутки нет ни размеров, ни предела.
    if (at != null && at > 0) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || !_scroll.hasClients) return;
        _scroll.jumpTo(at.clamp(0.0, _scroll.position.maxScrollExtent));
      });
    }
    _restored = true;
  }

  Future<void> _remember() async {
    if (!_restored || !_scroll.hasClients) return;
    final at = _scroll.offset;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_placeKey(widget.day), at);
  }

  Future<void> _cycleSize() async {
    final next = (_step + 1) % AlmaType.readingSteps.length;
    setState(() => _step = next);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_sizeKey, next);
  }

  /// О чём предлагаем спросить: первая позиция, из которой прочитан текст.
  ///
  /// **Переведённая и без хвоста с орбисом.** Сырая строка движка — «transiting
  /// uranus □ natal mercury · orb 0.85°»; вставленная в вопрос как есть, она
  /// давала «Спросить Alma про transiting uranus □ natal mercury · orb 0.85°».
  /// Орбис в 0.85° — довод внутренней кухни, а не то, о чём человек хочет
  /// спросить; отрезаем хвост и оставляем два тела и угол между ними.
  String? _aspect(L l) {
    for (final factor in widget.reading.citedFactors) {
      if (factor.trim().isEmpty) continue;
      final named = CabinetWordsMore.hit(l, factor).trim();
      if (named.isNotEmpty) return named;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final size = AlmaType.readingSteps[_step];
    final head = DateFormat.MMMMd(
      Localizations.localeOf(context).toString(),
    ).format(widget.day);

    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: Stack(
        children: [
          // Настроение «чтение»: поле приглушено и кометы нет — свет, идущий
          // поперёк страницы, мешает словам. То же, что у главы.
          const NightSky(
            mood: SkyMood.reading,
            seed: 0x52454144,
            child: SizedBox.expand(),
          ),
          Column(
            children: [
              _Panel(
                title: l.readerHeader(head).toUpperCase(),
                read: _read,
                onBack: () => Navigator.of(context).maybePop(),
                onSize: _cycleSize,
                sizeLabel: l.readerTextSize,
              ),
              Expanded(
                child: Stack(
                  children: [
                    // Строка уходит под панель, а не режется об неё: под
                    // шапкой оставался ряд половинок букв. То же лечение, что
                    // у верхнего поля главы, и по той же причине.
                    ShaderMask(
                      shaderCallback: (rect) =>
                          const LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [Color(0x00000000), Color(0xFF000000)],
                          ).createShader(
                            Rect.fromLTWH(0, rect.top, rect.width, 18),
                          ),
                      blendMode: BlendMode.dstIn,
                      child: ListView(
                        controller: _scroll,
                        physics: const BouncingScrollPhysics(
                          parent: AlwaysScrollableScrollPhysics(),
                        ),
                        padding: EdgeInsets.fromLTRB(
                          _column,
                          18,
                          // Справа шире на нить с бусиной.
                          _column + 14,
                          AlmaMetrics.gapSection +
                              MediaQueryData.fromView(
                                View.of(context),
                              ).padding.bottom,
                        ),
                        children: [
                          Text(
                            widget.reading.teaser,
                            style: AlmaType.readingLead,
                          ),
                          const SizedBox(height: 18),
                          const _StarRule(),
                          const SizedBox(height: 18),
                          for (final paragraph in widget.reading.body)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 15),
                              child: Text(
                                paragraph,
                                style: AlmaType.readingBody(size),
                              ),
                            ),
                          if (widget.reading.citedFactors.isNotEmpty) ...[
                            const SizedBox(height: 10),
                            _ReadFrom(widget.reading.citedFactors),
                          ],
                          if (_aspect(l) case final aspect?) ...[
                            const SizedBox(height: 18),
                            _AskCard(
                              label: l.readerAskAboutIt(aspect),
                              onTap: () {
                                // Порядок: сперва закрыть комнату, потом отдать
                                // вопрос. Оболочка под нами переключит вкладку,
                                // а экран Alma подставит текст и погасит признак.
                                Navigator.of(context).pop();
                                almaDraft.value = l.readerAskAboutIt(aspect);
                              },
                            ),
                          ],
                        ],
                      ),
                    ),
                    // Нить у правого поля: то же значение, что у полосы под
                    // шапкой, другой рисунок.
                    Positioned(
                      top: 0,
                      bottom: 0,
                      right: 10,
                      child: Center(child: _Thread(read: _read)),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Верхняя панель 100: «←», середина, «Aa». Под ней — полоса прочитанного.
class _Panel extends StatelessWidget {
  const _Panel({
    required this.title,
    required this.read,
    required this.onBack,
    required this.onSize,
    required this.sizeLabel,
  });

  final String title;
  final ValueListenable<double> read;
  final VoidCallback onBack;
  final VoidCallback onSize;
  final String sizeLabel;

  @override
  Widget build(BuildContext context) {
    final safeTop = MediaQuery.paddingOf(context).top;
    return Column(
      children: [
        SizedBox(
          height:
              safeTop + _TodayReadingScreenState._panel - safeTop.clamp(0, 44),
          child: Padding(
            padding: EdgeInsets.only(top: safeTop, left: 8, right: 8),
            child: Row(
              children: [
                IconButton(
                  onPressed: onBack,
                  icon: const Icon(Icons.arrow_back, color: AlmaPalette.gold),
                  // Читалка — комната, и выход из неё обязан быть нащупываемым
                  // без взгляда: 44 — пол касания, ниже него палец промахивается.
                  constraints: const BoxConstraints.tightFor(
                    width: 44,
                    height: 44,
                  ),
                ),
                Expanded(
                  child: Text(
                    title,
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AlmaType.readerHead,
                  ),
                ),
                Semantics(
                  label: sizeLabel,
                  button: true,
                  child: IconButton(
                    onPressed: onSize,
                    constraints: const BoxConstraints.tightFor(
                      width: 44,
                      height: 44,
                    ),
                    icon: Text(
                      'Aa',
                      style: AlmaType.meta.copyWith(color: AlmaPalette.gold),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        // Полоса прочитанного: две точки, золото по заполнению.
        ValueListenableBuilder<double>(
          valueListenable: read,
          builder: (context, value, _) => Align(
            alignment: Alignment.centerLeft,
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: value.clamp(0.0, 1.0),
              child: Container(height: 2, color: AlmaPalette.gold),
            ),
          ),
        ),
      ],
    );
  }
}

/// Нить чтения у правого поля: две точки серым, золото по заполнению, бусина.
class _Thread extends StatelessWidget {
  const _Thread({required this.read});

  static const _height = 150.0;

  final ValueListenable<double> read;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<double>(
      valueListenable: read,
      builder: (context, value, _) {
        final at = (_height * value).clamp(0.0, _height);
        return SizedBox(
          width: 8,
          height: _height,
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned(
                left: 3,
                top: 0,
                child: Container(
                  width: 2,
                  height: _height,
                  decoration: BoxDecoration(
                    color: AlmaPalette.body.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(1),
                  ),
                ),
              ),
              Positioned(
                left: 3,
                top: 0,
                child: Container(
                  width: 2,
                  height: at,
                  decoration: BoxDecoration(
                    color: AlmaPalette.goldDeep,
                    borderRadius: BorderRadius.circular(1),
                  ),
                ),
              ),
              Positioned(
                left: 0.5,
                top: (at - 3.5).clamp(0.0, _height - 7),
                child: Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    color: AlmaPalette.goldDeep,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AlmaPalette.gold.withValues(alpha: 0.6),
                        blurRadius: 6,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// ✦ между двумя гаснущими волосами — тот же знак, что закрывает главу.
class _StarRule extends StatelessWidget {
  const _StarRule();

  @override
  Widget build(BuildContext context) {
    Widget hair(bool toCentre) => Expanded(
      child: Container(
        height: 1,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: toCentre
                ? [Colors.transparent, AlmaPalette.gold.withValues(alpha: 0.5)]
                : [AlmaPalette.gold.withValues(alpha: 0.5), Colors.transparent],
          ),
        ),
      ),
    );
    return Row(
      children: [
        hair(true),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          // Подписью интерфейса, а не гарнитурой чтения: у Lora знака ✦ нет
          // вовсе — проверено по таблице cmap файла, — и на ней он выпал бы
          // пустым квадратом.
          child: Text(
            '✦',
            style: AlmaType.meta.copyWith(color: AlmaPalette.goldDeep),
          ),
        ),
        hair(false),
      ],
    );
  }
}

/// «Прочитано из» — позиции, из которых написан текст.
class _ReadFrom extends StatelessWidget {
  const _ReadFrom(this.factors);

  final List<String> factors;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final rest = factors.length - 1;
    // **Строка, а не список, и не по-английски.**
    //
    // Здесь печатались сырые строки движка — все десять, как есть:
    // «transiting uranus □ natal mercury · orb 0.85°». По-английски в русском
    // приложении, с пустым квадратом вместо знака аспекта (у гарнитуры
    // интерфейса его нет) и с точностью до сотой доли градуса, которая тут
    // никому ничего не говорит. Найдено глазами на симуляторе.
    //
    // Позиции переводит `CabinetWordsMore.factor` — тот же локализатор, что у
    // мета-строки главы, и глифы аспектов он ставит символьным шрифтом. Спека
    // просит **мета-строку**, одну: остальные считаются числом, как в главе.
    final style = AlmaType.numeral.copyWith(
      color: AlmaPalette.muted2,
      fontFamilyFallback: AlmaType.glyphFallback,
    );
    return Row(
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Text(l.cabReadFrom.toUpperCase(), style: AlmaType.overline),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            CabinetWordsMore.hit(l, factors.first),
            semanticsLabel: CabinetWordsMore.factorSpoken(l, factors.first),
            style: style,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (rest > 0) ...[
          const SizedBox(width: 8),
          Text('+$rest', style: style),
        ],
      ],
    );
  }
}

/// Карточка «Спросить Alma про …» — уводит в разговор с готовым вопросом.
class _AskCard extends StatelessWidget {
  const _AskCard({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AlmaPalette.hairlineGold),
          color: AlmaPalette.veil,
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                label,
                style: AlmaType.body.copyWith(color: AlmaPalette.gold),
              ),
            ),
            const SizedBox(width: 10),
            const Icon(Icons.arrow_forward, size: 16, color: AlmaPalette.gold),
          ],
        ),
      ),
    );
  }
}
