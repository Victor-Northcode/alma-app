import '../l10n/alma_l10n.dart';

/// Слова кабинета, выбираемые по строке из данных движка.
///
/// Порт рантайм-половины `CabinetCopy.swift` и `DailyL10n.swift`: движок
/// называет планеты, аспекты и области по-английски в данных — это
/// идентификаторы, их проверяет валидатор, — а на экран они выходят на языке
/// человека. Перевод происходит в последний момент перед показом, чтобы данные
/// под ним не дрейфовали.
///
/// Ключ, которого словарь не знает, **печатается как есть**, а не пропадает:
/// незнакомое слово честнее пустого места. Это тот же договор, что в
/// `bodyName` на iOS — и та же причина, по которой на экране однажды стоял
/// сырой ключ `cab.aspect.meaning.quincunx`: рантайм-ключи не имеют запасного
/// значения из коробки, поэтому запасное значение здесь written into the switch.
class CabinetWords {
  const CabinetWords._();

  /// «work» → «Работа».
  static String area(L l, String area) => switch (area) {
        'work' => l.cabAreaWork,
        'love' => l.cabAreaLove,
        'money' => l.cabAreaMoney,
        'body' => l.cabAreaBody,
        _ => area,
      };

  /// «midheaven» → «Середина неба».
  static String body(L l, String key) => switch (key) {
        'sun' => l.cabBodySun,
        'moon' => l.cabBodyMoon,
        'mercury' => l.cabBodyMercury,
        'venus' => l.cabBodyVenus,
        'mars' => l.cabBodyMars,
        'jupiter' => l.cabBodyJupiter,
        'saturn' => l.cabBodySaturn,
        'uranus' => l.cabBodyUranus,
        'neptune' => l.cabBodyNeptune,
        'pluto' => l.cabBodyPluto,
        'chiron' => l.cabBodyChiron,
        'lilith' => l.cabBodyLilith,
        'ascendant' => l.cabBodyAscendant,
        'midheaven' => l.cabBodyMidheaven,
        'true_node' => l.cabBodyTrueNode,
        'mean_node' => l.cabBodyMeanNode,
        'south_node' => l.cabBodySouthNode,
        'part_of_fortune' => l.cabBodyPartOfFortune,
        'vertex' => l.cabBodyVertex,
        _ => key.replaceAll('_', ' '),
      };

  /// «square» → «квадратура».
  static String aspect(L l, String aspect) => switch (aspect) {
        'conjunction' => l.dailyAspectConjunction,
        'opposition' => l.dailyAspectOpposition,
        'trine' => l.dailyAspectTrine,
        'square' => l.dailyAspectSquare,
        'sextile' => l.dailyAspectSextile,
        'quincunx' => l.dailyAspectQuincunx,
        'quintile' => l.dailyAspectQuintile,
        'biquintile' => l.dailyAspectBiquintile,
        'semisextile' => l.dailyAspectSemisextile,
        'semisquare' => l.dailyAspectSemisquare,
        'sesquiquadrate' => l.dailyAspectSesquiquadrate,
        _ => aspect,
      };

  /// «Солнце сейчас и Сатурн в твоей карте: оппозиция» — та же фраза, которой
  /// говорят строки транзитов и день, чтобы один контакт читался одинаково,
  /// где бы ни встретился. Шаблон приходит из каталога: в пяти языках из семи
  /// он был сломан («Солнце и Солнце: квадратура») и чинился 9 августа.
  static String contact(L l, {required String transiting, required String aspect, required String natal}) =>
      l.dailyContactPhrase(body(l, transiting), CabinetWords.aspect(l, aspect), body(l, natal));
}
