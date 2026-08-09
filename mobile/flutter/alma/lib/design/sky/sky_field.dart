import 'dart:ui';

import '../palette.dart';

/// Детерминированный источник случайности и поля звёзд, из него вытянутые.
///
/// Порт `mobile/ios/Alma/DesignSystem/Sky/SkyField.swift`.
///
/// **Почему с зерном, а не обычным random.** Небо пересобирается при каждом
/// изменении геометрии — поворот, клавиатура, лист, меняющий размер экрана
/// позади. С незасеянным источником каждое такое событие молча перетасовывает
/// всё звёздное поле, и это читается как мигание ровно в тот момент, когда
/// интерфейс просит внимания в другом месте. С зерном экран весь сеанс имеет
/// одно и то же небо, а два экрана с разными зёрнами — видимо разные.
///
/// SplitMix64, а не встроенный `Random`: восемь строк, распределение достаточно
/// ровное для рассыпания точек, и нет состояния, о котором надо думать между
/// потоками. Dart не имеет беззнакового 64-битного типа, но `int` здесь и есть
/// 64 бита с обёрткой при переполнении, а сдвиг `>>>` беззнаковый — так что
/// последовательность получается **побитово та же, что на iOS**, и небо на двух
/// платформах совпадает звезда в звезду.
class SkyRandom {
  int _state;

  SkyRandom({int seed = 0x414C4D41})
      // Нулевое зерно заставило бы SplitMix64 выдать постоянную
      // последовательность, поэтому оно сдвигается, а не отвергается: тот, кто
      // передал 0, хочет «небо по умолчанию», а не отказ.
      : _state = seed + 0x9E3779B97F4A7C15;

  int next() {
    _state = _state + 0x9E3779B97F4A7C15;
    var z = _state;
    z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9;
    z = (z ^ (z >>> 27)) * 0x94D049BB133111EB;
    return z ^ (z >>> 31);
  }

  double unit() => (next() >>> 11) * (1.0 / 9007199254740992.0);

  double between(double low, double high) => low + unit() * (high - low);
}

/// Оттенок звезды. Их три, и золотых мало намеренно: чуть больше — и небо
/// начинает выглядеть жёлтым.
enum StarTint {
  /// Почти белый — большинство.
  white(Color(0xFFFFF8E6)),

  /// Состаренный пергамент.
  warm(Color(0xFFE6D9B4)),

  /// Золото, и редко.
  gold(AlmaPalette.gold);

  const StarTint(this.colour);
  final Color colour;
}

/// Одна звезда. Положение — **доля** холста, а не точки, чтобы поле, созданное
/// однажды, пережило любое изменение раскладки без пересоздания.
class SkyStar {
  const SkyStar({
    required this.x,
    required this.y,
    required this.radius,
    required this.phase,
    required this.tint,
  });

  final double x;
  final double y;
  final double radius;

  /// С какого места собственного цикла мерцания эта звезда начинает, 0…1.
  final double phase;
  final StarTint tint;
}

/// Одна плывущая пылинка.
class SkyMote {
  const SkyMote({
    required this.x,
    required this.y,
    required this.size,
    required this.duration,
    required this.delay,
  });

  final double x;

  /// Откуда начинает, долей высоты холста.
  final double y;
  final double size;

  /// Секунд на один подъём. Веб берёт 14; разброс не даёт пылинкам двигаться
  /// группой — а именно это и выдаёт анимацию.
  final double duration;
  final double delay;
}

/// Готовое небо: два слоя звёзд и пылинки, произведённые один раз из зерна.
///
/// Количества взяты из потолка бренд-бука — «не больше трёх пылинок, одна
/// комета на экран, не больше двух пятен ауры». Числа звёзд наши: CSS выражает
/// своё поле девятью вручную расставленными градиентами, а девять звёзд на
/// холсте в 900 точек — это схема неба, а не небо.
class SkyField {
  const SkyField._(this.near, this.far, this.motes);

  final List<SkyStar> near;
  final List<SkyStar> far;
  final List<SkyMote> motes;

  /// - [seed]: что угодно устойчивое для экрана. Значение, выведенное из
  ///   маршрута, — идеально; по умолчанию то же, что у любого фонового неба.
  /// - [density]: 1.0 — обычное поле. Церемония путешествия его поднимает;
  ///   экран чтения опускает, чтобы текст ни с чем не соревновался.
  factory SkyField.generate({int seed = 0x414C4D41, double density = 1.0}) {
    final rng = SkyRandom(seed: seed);

    final nearCount = (64 * density).toInt();
    final farCount = (96 * density).toInt();

    SkyStar star({
      required double minRadius,
      required double maxRadius,
      required double goldChance,
    }) {
      final roll = rng.unit();
      final tint = roll < goldChance
          ? StarTint.gold
          : (roll < 0.34 ? StarTint.warm : StarTint.white);
      return SkyStar(
        x: rng.unit(),
        y: rng.unit(),
        radius: rng.between(minRadius, maxRadius),
        phase: rng.unit(),
        tint: tint,
      );
    }

    // Ближний слой — тот, который читает глаз: меньше числом, крупнее, ярче.
    final near = List<SkyStar>.generate(
      nearCount,
      (_) => star(minRadius: 0.7, maxRadius: 1.05, goldChance: 0.10),
    );
    // Дальний слой — заливка. Мельче и вполсилы, на своих, более медленных и
    // сдвинутых часах, чтобы два слоя никогда не пульсировали вместе.
    final far = List<SkyStar>.generate(
      farCount,
      (_) => star(minRadius: 0.45, maxRadius: 0.62, goldChance: 0.06),
    );

    final motes = List<SkyMote>.generate(
      3,
      (index) => SkyMote(
        x: rng.between(0.06, 0.94),
        y: rng.between(0.45, 0.95),
        size: rng.between(1.6, 2.4),
        duration: rng.between(12, 17),
        delay: index * rng.between(3.0, 6.0),
      ),
    );

    return SkyField._(near, far, motes);
  }
}
