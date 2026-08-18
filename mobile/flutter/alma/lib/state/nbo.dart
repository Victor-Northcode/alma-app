/// NBO — какой карточкой встречает главный экран (ТЗ v3 §4).
///
/// Rule-based и целиком на клиенте: §6 Ф2 просит «профиль сигналов на
/// клиенте, веса из remote-config, без ML». Здесь правила; веса, когда
/// появится их источник, лягут параметрами [NboSignals], не меняя формы.
///
/// **Что NBO решает и чего не трогает.** Он упорядочивает карточки главного
/// экрана и содержимое «что дальше» (P3). Контекстные пейволлы всегда продают
/// то, что тапнуто, — их NBO не касается по букве §4.
///
/// Считается чистой функцией от [NboSignals] — ни сети, ни состояния: порядок
/// карточек обязан быть готов в первом кадре экрана и одинаков при пересборке.
library;

/// Карточки главного экрана, которые NBO умеет упорядочивать.
enum NboCard { compatibility, natal, horoscope, astrocartography, synthesis, solar, bundle }

/// Сигналы §4 — голыми значениями, без знания о сессии и моделях.
///
/// Поведенческие сигналы, которых продукт пока не собирает, приходят
/// умолчаниями и честно не участвуют; форма готова принять их без правок
/// вызывающих экранов.
class NboSignals {
  const NboSignals({
    this.interest,
    this.femaleReader = false,
    this.loveChapterReadRecently = false,
    this.freeChaptersReadSystems = 0,
    this.ownsBundle = false,
    this.subscriber = false,
    this.ownsEverything = false,
  });

  /// "love" | "money" | "self" | "future" | null — ответ квиза V0.
  final String? interest;

  /// Тай-брейкер веса совместимости; interest всегда сильнее пола (§4).
  final bool femaleReader;

  /// «Глава про любовь прочитана» — поднимает совместимость на 72 часа.
  /// Окно считает вызывающий: у NBO нет часов, у него есть сигналы.
  final bool loveChapterReadRecently;

  /// В скольких системах прочитаны бесплатные главы.
  final int freeChaptersReadSystems;

  final bool ownsBundle;
  final bool subscriber;

  /// Всё куплено или подписка держит всё: по §4 коммерческие карточки
  /// исчезают целиком, главный экран — только контент.
  final bool ownsEverything;
}

/// Порядок карточек главного экрана по §4 — базовая матрица плюс модификаторы.
List<NboCard> nboOrder(NboSignals signals) {
  // Всё открыто — торговать нечем и незачем: остаётся контент.
  if (signals.ownsEverything) {
    return const [NboCard.horoscope, NboCard.natal, NboCard.compatibility];
  }

  // Базовая матрица приоритетов из §4, строка за строкой.
  var order = switch (signals.interest) {
    'love' => <NboCard>[NboCard.compatibility, NboCard.natal, NboCard.horoscope],
    'money' => <NboCard>[NboCard.natal, NboCard.astrocartography, NboCard.horoscope],
    'self' => <NboCard>[NboCard.natal, NboCard.synthesis, NboCard.horoscope],
    'future' => <NboCard>[NboCard.horoscope, NboCard.solar, NboCard.natal],
    // Интереса нет — универсальный вход, как у первой покупки: натал.
    _ => <NboCard>[NboCard.natal, NboCard.horoscope, NboCard.compatibility],
  };

  // «Глава про любовь прочитана» — совместимость на первую позицию,
  // независимо от interest (§4, сильнейший модификатор).
  if (signals.loveChapterReadRecently) {
    order = [
      NboCard.compatibility,
      ...order.where((card) => card != NboCard.compatibility),
    ];
  } else if (signals.femaleReader &&
      signals.interest != 'love' &&
      order.contains(NboCard.compatibility)) {
    // Пол — тай-брейкер: совместимость на позицию выше, но не выше того,
    // что назвал interest. Мужчинам её не прячут — только ниже приоритетом.
    final at = order.indexOf(NboCard.compatibility);
    if (at > 1) {
      order
        ..removeAt(at)
        ..insert(at - 1, NboCard.compatibility);
    }
  }

  // Бесплатные главы распробованы в трёх системах, набора нет — карточка
  // набора появляется в хвосте: человек уже читает продукт вширь.
  if (signals.freeChaptersReadSystems >= 3 && !signals.ownsBundle) {
    order = [...order, NboCard.bundle];
  }

  return order;
}
