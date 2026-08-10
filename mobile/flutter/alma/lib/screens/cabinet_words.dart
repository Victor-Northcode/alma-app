import '../l10n/alma_l10n.dart';
import '../net/models.dart';

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

/// Знаки, дома, системы, группы и статусы — вторая половина словаря.
extension CabinetWordsMore on CabinetWords {
  /// «Taurus» → «Телец».
  static String sign(L l, String name) => switch (name) {
        'Aries' => l.cabSignAries,
        'Taurus' => l.cabSignTaurus,
        'Gemini' => l.cabSignGemini,
        'Cancer' => l.cabSignCancer,
        'Leo' => l.cabSignLeo,
        'Virgo' => l.cabSignVirgo,
        'Libra' => l.cabSignLibra,
        'Scorpio' => l.cabSignScorpio,
        'Sagittarius' => l.cabSignSagittarius,
        'Capricorn' => l.cabSignCapricorn,
        'Aquarius' => l.cabSignAquarius,
        'Pisces' => l.cabSignPisces,
        _ => name,
      };

  static String house(L l, int number) => switch (number) {
        1 => l.cabHouse1,
        2 => l.cabHouse2,
        3 => l.cabHouse3,
        4 => l.cabHouse4,
        5 => l.cabHouse5,
        6 => l.cabHouse6,
        7 => l.cabHouse7,
        8 => l.cabHouse8,
        9 => l.cabHouse9,
        10 => l.cabHouse10,
        11 => l.cabHouse11,
        12 => l.cabHouse12,
        _ => 'house $number',
      };

  static String system(L l, SystemSlug slug) => switch (slug) {
        SystemSlug.natal => l.cabSystemNatal,
        SystemSlug.numerology => l.cabSystemNumerology,
        SystemSlug.birthCard => l.cabSystemBirthCard,
        SystemSlug.transits => l.cabSystemTransits,
        SystemSlug.solarReturn => l.cabSystemSolarReturn,
        SystemSlug.compatibility => l.cabSystemCompatibility,
        SystemSlug.astrocartography => l.cabSystemAstrocartography,
        SystemSlug.synthesis => l.cabSystemSynthesis,
      };

  /// Пять состояний хаба. Незнакомое печатает собственный токен сервера:
  /// состояние, которого эта сборка не видела, обязано выродиться в
  /// незнакомое слово, а не в пустой экран.
  static String status(L l, String status) => switch (status) {
        'calculated' => l.cabStatusCalculated,
        'open' => l.cabStatusOpen,
        'needs-time' => l.cabStatusNeedsTime,
        'add-person' => l.cabStatusAddPerson,
        'not-yet' => l.cabStatusNotYet,
        _ => status,
      };

  /// «calculated» значит открыто, «open» — считаемо, но не оплачено; расчёт
  /// бесплатен в обоих случаях, так что оба готовы. Не готовы лишь три,
  /// называющие что-то отсутствующее.
  static bool isReady(String status) => status == 'calculated' || status == 'open';

  /// Глиф знака внутри строки движка, заменённый именем. «9°52′ ♑︎» — глиф
  /// единственное, что читатель не может расшифровать. Подстановка, а не
  /// переформатирование: градусы и минуты остаются ровно теми, что напечатал
  /// движок, и этот слой не становится вторым мнением о числе.
  static String spellSigns(L l, String formatted) {
    const glyphs = {
      'Aries': '♈︎', 'Taurus': '♉︎', 'Gemini': '♊︎', 'Cancer': '♋︎',
      'Leo': '♌︎', 'Virgo': '♍︎', 'Libra': '♎︎', 'Scorpio': '♏︎',
      'Sagittarius': '♐︎', 'Capricorn': '♑︎', 'Aquarius': '♒︎', 'Pisces': '♓︎',
    };
    var out = formatted;
    glyphs.forEach((name, glyph) {
      if (out.contains(glyph)) out = out.replaceAll(glyph, sign(l, name));
    });
    // Движок добавляет к некоторым глифам селектор начертания; замена выше
    // оставляет его позади.
    return out.replaceAll('︎', '').trim();
  }
}
