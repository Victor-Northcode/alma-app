import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import '../net/models.dart' show SystemSlug;
import 'metrics.dart';
import 'palette.dart';
import 'typography.dart';

/// Какая вклейка открывает какую главу.
///
/// Карта продиктована владельцем 15 августа 2026 и сверена с диском: тридцать
/// пять имён, ни одного лишнего, ни одного отсутствующего. Ключи — слаги из
/// `backend/alma/ai/chapters.py`, единственный источник истины о главах.
///
/// **Доска дизайна была расписана по другим главам.** У художника наталь шла
/// как «The Sun and Its Work», «The Moon and What It Needs» — таких глав в
/// движке нет, а `karmic-axis` и `work-rhythms` остались без картин. Четырнадцать
/// из шестнадцати ложились уверенно, четыре нет, и угадывать их было нельзя:
/// неверная вклейка — это не кривой отступ, а картинка не про то, что человек
/// читает, на платной главе. Спорные решены владельцем и записаны здесь.
///
/// **Шесть дыр помечены `null` честно.** Арт под них ещё не нарисован; до тех
/// пор глава открывается аркой с римской цифрой, а не чужой картинкой и не
/// пустотой. Одна времянка — у `life-path` пока стоит чужая вклейка, и это
/// записано в `plates-map.md` рядом с промптом на замену.
class AlmaPlates {
  const AlmaPlates._();

  static const _map = <SystemSlug, Map<String, String?>>{
    SystemSlug.natal: {
      'core': 'plate-shape',
      'portrait': 'plate-face',
      'love': 'plate-love',
      'money': 'plate-money',
      'career': 'plate-calling',
      'mind': 'plate-speech',
      'shadow': 'plate-depths',
      'roots': 'plate-home',
      'karmic-axis': 'plate-repeats',
      'work-rhythms': 'plate-sun',
      'transformation': 'plate-crisis',
      'freedom': 'plate-freedom',
      'dreams': 'plate-dreams',
      'circle': 'plate-friends',
      'worldview': 'plate-faith',
      'milestones': 'plate-saturn',
    },
    SystemSlug.numerology: {
      // Времянка: чужая вклейка до генерации «дороги». Помечено в plates-map.md.
      'life-path': 'plate-soulurge',
      'birthday-number': null,
      'personal-year': 'plate-year',
      'pinnacles': 'plate-eleven',
      'name': 'plate-expression',
    },
    SystemSlug.birthCard: {
      'personality': 'plate-personality',
      'soul': 'plate-soulcard',
      'year-card': 'plate-yearcard',
    },
    SystemSlug.transits: {
      'active': 'plate-sky',
      'ahead': null,
      'long': null,
    },
    SystemSlug.solarReturn: {
      'year-shape': 'plate-solar',
      'emphasis': 'plate-yeartheme',
      'contacts': 'plate-yearlesson',
    },
    SystemSlug.compatibility: {
      'attraction': 'plate-pull',
      'friction': 'plate-catches',
      'overlays': 'plate-veil',
      'together': 'plate-tender',
    },
    SystemSlug.astrocartography: {
      'lines': 'plate-lines',
      'here': 'plate-whereto',
      'crossings': null,
    },
    // Синтез — система «всё вместе», и одна картина на все четыре главы здесь
    // правило, а не дыра: четыре разных арта под «где системы согласны» и «где
    // расходятся» рассказывали бы про четыре разные вещи вместо одной.
    SystemSlug.synthesis: {
      'agreement': 'plate-synthesis',
      'disagreement': 'plate-synthesis',
      'single': 'plate-synthesis',
      'whole': 'plate-synthesis',
    },
  };

  /// Вклейка ежедневника. Главой не является — стоит на «Сегодня».
  static const today = 'plate-moon';

  static String? name(SystemSlug system, String chapter) =>
      _map[system]?[chapter];

  /// Для теста: вся карта, включая дыры.
  static Map<SystemSlug, Map<String, String?>> get all => _map;
}

/// Скачанная однажды вклейка, лежащая на диске до переустановки.
///
/// Сервер обещает `immutable` на год и отдаёт ETag, но `Image.network` во
/// Flutter не слушает ни того, ни другого: `HttpClient` из `dart:io` кэша не
/// держит вовсе, и картинка ехала бы заново при каждом открытии главы. Сто
/// килобайт на мобильном интернете — это заметно читателю, а не нам.
///
/// Поэтому кэш свой и предельно простой: файл на имя. Имя не переиспользуется —
/// новая картина приезжает новым именем, — так что инвалидация не нужна вовсе,
/// и её отсутствие здесь не упущение, а следствие контракта.
class PlateStore {
  PlateStore({required this.baseUrl, http.Client? client})
      : _http = client ?? http.Client();

  final Uri baseUrl;
  final http.Client _http;

  Directory? _dir;
  final _inflight = <String, Future<File?>>{};

  Future<Directory> _folder() async {
    final cached = _dir;
    if (cached != null) return cached;
    final base = await getApplicationSupportDirectory();
    final dir = Directory('${base.path}/plates');
    if (!dir.existsSync()) dir.createSync(recursive: true);
    return _dir = dir;
  }

  /// Файл вклейки, скачивая её при первой надобности.
  ///
  /// `null` — картинки нет и не будет: сервер ответил 404 или сети нет. Оба
  /// случая рисуются одинаково — аркой с римской цифрой, — потому что для
  /// читателя они и есть одно и то же.
  Future<File?> file(String name) {
    return _inflight.putIfAbsent(name, () async {
      try {
        final dir = await _folder();
        final target = File('${dir.path}/$name.webp');
        if (target.existsSync() && target.lengthSync() > 0) return target;

        final response = await _http
            .get(baseUrl.resolve('/static/plates/$name.webp'))
            .timeout(const Duration(seconds: 12));
        if (response.statusCode != 200 || response.bodyBytes.isEmpty) return null;

        // Сначала во временный файл, потом переименование: оборванная загрузка
        // не должна оставить на диске половину картинки, которую следующий
        // запуск примет за целую.
        final partial = File('${target.path}.part');
        await partial.writeAsBytes(response.bodyBytes, flush: true);
        await partial.rename(target.path);
        return target;
      } catch (_) {
        return null;
      } finally {
        _inflight.remove(name);
      }
    });
  }
}

/// Арка-вклейка: картина главы в раме со скруглённым верхом.
///
/// Радиус 85 сверху и 12 снизу, золотой кант и внутренний штрих с отступом —
/// числа из `SKILL.md`. Три состояния, и ни одно из них не пустая дыра:
///
/// * пока грузится — пергаментный шиммер внутри арки, без спиннера: спиннер
///   говорит «жди», а здесь ждать почти не приходится;
/// * не догрузилась — римская цифра главы на пергаменте;
/// * загрузилась — проявление за 260 мс.
class PlateArch extends StatefulWidget {
  const PlateArch({
    super.key,
    required this.store,
    required this.plate,
    required this.numeral,
    this.width = 150,
    this.height = 188,
  });

  /// Откуда брать файл. `null` — сразу запасной вид: так рисуется превью в
  /// тестах и на экранах, где сети нет по устройству.
  final PlateStore? store;

  /// Имя вклейки или `null`, если арт под эту главу ещё не нарисован.
  final String? plate;

  /// Римская цифра главы — то, что стоит в арке вместо картины.
  final String numeral;

  final double width;
  final double height;

  @override
  State<PlateArch> createState() => _PlateArchState();
}

class _PlateArchState extends State<PlateArch> {
  File? _file;
  bool _settled = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(PlateArch old) {
    super.didUpdateWidget(old);
    if (old.plate != widget.plate) {
      _file = null;
      _settled = false;
      _load();
    }
  }

  Future<void> _load() async {
    final store = widget.store;
    final plate = widget.plate;
    if (store == null || plate == null) {
      if (mounted) setState(() => _settled = true);
      return;
    }
    final file = await store.file(plate);
    if (!mounted) return;
    setState(() {
      _file = file;
      _settled = true;
    });
  }

  /// Арка: верх — полукруг ровно в половину ширины, низ едва скруглён.
  /// Эталон (`s5`): рама 153×191 с радиусами 75/75/14/14, картина 150×188
  /// внутри неё, внутренний штрих 140×178 с радиусами на пять меньше.
  static const _radius = BorderRadius.only(
    topLeft: Radius.circular(75),
    topRight: Radius.circular(75),
    bottomLeft: Radius.circular(14),
    bottomRight: Radius.circular(14),
  );

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.width,
      height: widget.height,
      child: Stack(
        fit: StackFit.expand,
        children: [
          ClipRRect(
            borderRadius: _radius,
            child: AnimatedSwitcher(
              duration: AlmaMotion.plateFade,
              child: _inside(),
            ),
          ),
          // Кант и внутренний штрих поверх картины: рама принадлежит арке, а не
          // содержимому, и не должна проявляться вместе с ним.
          IgnorePointer(
            child: DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: _radius,
                border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.5)),
              ),
              child: Padding(
                padding: const EdgeInsets.all(5.5),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: _radius,
                    border: Border.all(
                      color: AlmaPalette.starFill.withValues(alpha: 0.4),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _inside() {
    final file = _file;
    if (file != null) {
      return Image.file(file, key: const ValueKey('art'), fit: BoxFit.cover);
    }
    return _settled
        ? _Numeral(key: const ValueKey('numeral'), numeral: widget.numeral)
        : const _Shimmer(key: ValueKey('shimmer'));
  }
}

/// Запасной вид: римская цифра на пергаменте.
class _Numeral extends StatelessWidget {
  const _Numeral({super.key, required this.numeral});

  final String numeral;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFEDE3CC), Color(0xFFEFE3C9), Color(0xFFDFD0AF)],
          stops: [0, 0.6, 1],
        ),
      ),
      child: Center(
        child: Text(
          numeral,
          style: AlmaType.displayL.copyWith(
            color: AlmaPalette.goldDeep,
            fontSize: 34,
          ),
        ),
      ),
    );
  }
}

/// Пергаментный отблеск, пока картина едет. Без спиннера — он обещает ожидание.
class _Shimmer extends StatefulWidget {
  const _Shimmer({super.key});

  @override
  State<_Shimmer> createState() => _ShimmerState();
}

class _ShimmerState extends State<_Shimmer> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: AlmaMotion.shimmer,
  )..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        final t = _c.value * 2 - 0.5;
        return DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment(t - 0.6, -1),
              end: Alignment(t + 0.6, 1),
              colors: const [
                Color(0xFFE6DCC2),
                Color(0xFFF3E9D2),
                Color(0xFFE6DCC2),
              ],
            ),
          ),
        );
      },
    );
  }
}
