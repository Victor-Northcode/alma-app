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

  /// Глиф знака внутри строки движка, заменённый именем: «9°52′ ♑︎» → «9°52′
  /// Козерог». Подстановка, а не переформатирование: градусы и минуты остаются
  /// ровно теми, что напечатал движок, и этот слой не становится вторым
  /// мнением о числе.
  ///
  /// **Это форма для голоса и для прозы, а не для мета-строки.** Имя знака
  /// длиннее глифа в разы, и в строку «read from» — одну, узкую, рядом с
  /// подписью и счётчиком — оно не влезает: строка обрезалась многоточием, и
  /// вместе с хвостом уходил сам факт, ради которого цитата существует. Где
  /// места вдоволь — в прозе глав и в подписи для VoiceOver — имя честнее
  /// глифа; где места нет, честнее глиф. Отсюда пара `spellSigns`/`keepSigns`.
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
    return keepSigns(out);
  }

  /// Та же строка, но знак остаётся знаком: «9°52′ ♑︎» → «9°52′ ♑».
  ///
  /// Снимается один только селектор начертания U+FE0E. Flutter его не слушает
  /// — просьба «нарисуй текстом, а не картинкой» проходит мимо, и «♌» выходит
  /// цветной эмодзи-плашкой, — поэтому вид знака здесь задаётся не селектором,
  /// а шрифтом: `AlmaType.glyphFallback` на той стороне, где эта строка
  /// печатается. Сам селектор убран, чтобы не висеть в строке пустым кодом.
  static String keepSigns(String formatted) =>
      formatted.replaceAll('︎', '').trim();

  /// Цитата под текстом, сказанная на языке читателя.
  ///
  /// **Данные остаются английскими, а экран — нет.** Факторы — это
  /// идентификаторы: валидатор сверяет их с текстом посимвольно, и переводить
  /// их в ответе значило бы сломать единственную проверку, которая ловит
  /// выдуманную позицию. Поэтому подстановка происходит здесь, в последний
  /// момент перед экраном.
  ///
  /// Найдено на кадре: под русской главой стояло «sun 21°39′ ♓ · house 9».
  /// Читателю, который не знает английского, эта строка не подтверждает
  /// ничего — а она существует ровно для подтверждения.
  ///
  /// **Знак остаётся глифом.** Мета-строка «read from» — техническая: подпись,
  /// одна позиция, счётчик остальных и кнопка, всё в одну строку. Имя знака
  /// словом её переполняло, и `Text` резал хвост многоточием — «Луна 22°07′
  /// Стрел…», то есть ровно то место, которое цитата и обязана назвать. Глиф
  /// занимает один знак и не теряется никогда; в макете (s5, s7) в этой строке
  /// стоит именно он. Имена знаков живут в прозе главы, где им хватает места,
  /// и в подписи для VoiceOver — см. [factorSpoken].
  static String factor(L l, String raw) =>
      keepSigns(_translated(l, raw, lower: true));

  /// Та же цитата вслух: знак назван именем.
  ///
  /// Глиф VoiceOver либо молчит, либо читает кодовую точку, и позиция для
  /// незрячего читателя пропадает целиком. Подпись собирается из тех же слов
  /// каталога, что и проза, — ничего нового не выдумано.
  static String factorSpoken(L l, String raw) =>
      spellSigns(l, _translated(l, raw));

  /// Имя тела в регистре, который требует **язык**, а не оформление.
  ///
  /// В эталоне мета-строка набрана строчными: `venus 28°40′ ♓︎ · 7th house`.
  /// Понизить регистр в каталоге было бы ошибкой: по-немецки существительные
  /// пишутся с заглавной по правилу орфографии, и «mond» вместо «Mond» — не
  /// стиль, а опечатка. Поэтому регистр применяется здесь, на рендере строки, и
  /// только к английскому — единственному языку, на котором эталон нарисован.
  /// Остальным пяти строчная норма разрешена, но их каталоги мы не трогаем: у
  /// каждого своя традиция, и менять её вслепую не за что.
  /// [lower] просит строчную — но просит только видимая строка. Голосовая
  /// форма зовёт то же самое без него: спека даёт скринридеру «Moon 22°07′
  /// Sagittarius», с заглавной, и это не непоследовательность — проговорённое
  /// имя начинает фразу, а не стоит в наборе.
  static String _bodyCased(L l, String key, {required bool lower}) {
    final name = CabinetWords.body(l, key);
    return lower && l.localeName.startsWith('en') ? name.toLowerCase() : name;
  }

  /// Общая половина обеих форм: тела, аспекты и дома — словами каталога,
  /// знаки — как их напечатал движок.
  static String _translated(L l, String raw, {bool lower = false}) {
    var out = raw;

    // Дом: «house 9» → «9-й дом». Регистр числа — до имени тела, иначе
    // «house» успевает уехать в другую замену.
    out = out.replaceAllMapped(RegExp(r'\bhouse (\d{1,2})\b'), (match) {
      final number = int.tryParse(match.group(1)!);
      return number == null ? match.group(0)! : CabinetWordsMore.house(l, number);
    });

    // Тела и точки: слово целиком, чтобы `sun` внутри `sun_sign` не поймалось
    // половиной.
    for (final key in const [
      'true_node', 'mean_node', 'north_node', 'south_node',
      'part_of_fortune', 'vertex',
      'ascendant', 'midheaven', 'chiron', 'lilith',
      'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn',
      'uranus', 'neptune', 'pluto',
    ]) {
      out = out.replaceAll(RegExp('\\b$key\\b'), _bodyCased(l, key, lower: lower));
    }

    // Аспекты словами — тем же способом, что и везде.
    for (final key in const [
      'conjunction', 'opposition', 'trine', 'square', 'sextile', 'quincunx',
    ]) {
      out = out.replaceAll(RegExp('\\b$key\\b'), CabinetWords.aspect(l, key));
    }
    return out;
  }
}
