"""The chapter structure of each system.

Chapters are a product decision, not an astrological one: they are how a
reading is broken into things a person actually wants to know. "Money and
resources" is a question people have; "the second house and its ruler" is the
answer's mechanism.

Each chapter declares which factors it is allowed to read from. That is what
keeps the love chapter from wandering into career — and, more importantly, it
is what makes the sensitivity test possible: change the birth time by two
hours and the house-derived chapters must change, because their inputs did.

The `title` and `question` on each chapter below are the English, and they are
the reference the other five languages are written and checked against. They
are not what a reader is served: `GET /v1/readings/{system}/chapters` takes a
locale and looks the pair up through `alma/i18n/`, which keeps the words in
one file per language and the structure — the factors, the budget, the flags
— here, where changing it is an engineering decision rather than a piece of
copy-editing. `i18n.chapter_words(system, slug, locale=…)` is the only way to
ask for the reader's version; reading `chapter.title` directly gets you
English, which is right for a log line and wrong for a screen.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class Chapter:
    slug: str
    numeral: str
    index: int
    title: str
    question: str
    #: Substrings that select this chapter's factors from the CalcResult.
    #: A chapter with no matching factors is not written at all — silence
    #: beats a paragraph assembled out of whatever was nearby.
    reads: tuple[str, ...]
    #: **Ровно одна глава во всём продукте, и это натал I «Core».**
    #:
    #: Здесь стояло `free=True` у первой главы каждой из восьми систем, и
    #: владелец увидел последствие раньше, чем кто-либо посчитал деньги: одни
    #: главы открывались, другие показывали чёрную стену, и никакого правила за
    #: этим не читалось. Восемь бесплатных первых глав — это восемь разных
    #: обещаний на восьми экранах вместо одного.
    #:
    #: Решение владельца от 17.08.2026 и спека `locked-chapter-spec.md` §7:
    #: свободна одна глава, с бейджем «free», и она же — то, чем кончается квиз.
    #: Всё остальное закрыто и показывает открывающий абзац (§2.5).
    #:
    #: Флаг делает три вещи разом, и это надо знать, снимая его: выбирает модель
    #: (`mid` против `strong` в роутере), выбирает потолок одной генерации
    #: (`free_user_budget` $0.05 против `full_report_budget` $0.50) и — через
    #: `_c` ниже — задаёт длину. Снять его значит не только «закрыть», но и
    #: «сделать длиннее и дороже».
    free: bool = False
    #: True when the chapter depends on the houses, and therefore on a real
    #: birth time. The sensitivity test asserts exactly this set moves.
    time_dependent: bool = False
    #: **Сколько это стоит читателю по времени, а не сколько влезает.**
    #:
    #: Было 180–320, и фактическая середина держалась около 260 слов —
    #: минута чтения за платную главу. Владелец, пройдя все восемь систем:
    #: «такое ощущение, что недостаточно». Верхняя граница поднята до 480,
    #: нижняя до 300: глава становится разворотом, а не заметкой.
    #:
    #: Считано, а не прикинуто: 480 слов по-русски это 6120 токенов потолка,
    #: $0.178 на сильной модели против $0.50 на платную главу — влезает с
    #: запасом. Бесплатная глава на средней модели дала бы $0.107 против
    #: $0.10, поэтому у неё бюджет остаётся прежним: ровно те главы, что
    #: раздаются даром, и остаются короче — это цена бесплатного, а не
    #: скупость. `free=True` ставит его обратно ниже.
    words: tuple[int, int] = (300, 480)
    #: How many paragraphs this piece is asked for, and the floor below which
    #: it is regenerated rather than shipped. The default is what every chapter
    #: in this file has always been asked for and what `writer.MIN_PARAGRAPHS`
    #: enforced as a constant; it is a field now because the daily is a
    #: legitimately one-paragraph piece, and a one-paragraph *chapter* is still
    #: not a chapter. Making it a field rather than a special case in the
    #: writer keeps the rule where the rest of the piece's shape already lives,
    #: next to the word budget it has to agree with.
    paragraphs: tuple[int, int] = (3, 5)

    #: Whether this piece ends with `advice` — "one concrete thing to do or
    #: stop doing", rendered under "what to do with it".
    #:
    #: True for every chapter in this file and False for exactly one piece: the
    #: daily. `voice.DAILY_TIER` spends a third of its length forbidding the
    #: horoscope voice — *"no instructions for the day, no lists of things to
    #: watch for, no 'this is a good time to'"* — and then the schema asked for
    #: an instruction anyway. Seven of eight live generations filled it, every
    #: time with the banned content: *"wait an hour before answering it"*,
    #: *"track effort against actual output this week"*. The paragraphs were
    #: not horoscope; that one line was, every single time, and it is the line
    #: most likely to be screenshotted. It also collided with the product's own
    #: legal copy, which promises this is not advice.
    #:
    #: A field rather than a special case in the writer, for the reason
    #: `paragraphs` above is one: the shape of a piece belongs next to the rest
    #: of its shape, and a chapter that wants no advice should be able to say
    #: so without the writer knowing which chapter it is.
    advice: bool = True

    #: Whether this piece also writes the four life areas of the Today screen.
    #:
    #: **The block had no prompt at all, and that is what the owner saw.** Under
    #: the horoscope the Today screen lists work, love, money and body, each
    #: with its nearest contact. Nothing wrote those lines: the client rendered
    #: the raw calculation through a template — `"{transiting} {aspect} your
    #: {natal}"` — so a reader in English got *"Sun trine your Sun."* and, next
    #: to the heading **Work**, *"Chiron conjunct your Midheaven."* Both are
    #: true and neither is about work. The owner's words: «как будто ты забыл
    #: туда промты добавить… он вообще не по теме».
    #:
    #: True for exactly one piece — the transits' `active` chapter — and that is
    #: not arbitrary: it is the Today screen's day text, it is written from the
    #: very same transit hits the areas are drawn from, and it is written once a
    #: day anyway. Four short lines ride along in a call that was already
    #: happening, which is why this costs a few dozen words rather than a second
    #: request. Any other chapter asking for areas would be paying for a block
    #: nothing renders.
    areas: bool = False

    #: Указание писателю, которое есть только у этой главы, — одной строкой в
    #: промпт (`writer.build_prompt`, «THIS CHAPTER»). Появилось 29.08.2026 из
    #: двух живых скринов владельца: глава личного года объяснила читателю,
    #: что «месяцев четырнадцать» (в соседних факторах лежали «day 14» и
    #: «karmic debt 14», и модель склеила), а глава имени назвала числа
    #: выражения и желания без единого слова о том, как они посчитаны, — при
    #: том что выкладки (`workings`) ей выданы. По-английски, как весь промпт;
    #: пустая строка — глава без особых правил.
    guidance: str = ""


def _c(index, numeral, slug, title, question, reads, **kwargs) -> Chapter:
    # Бесплатная глава пишется средней моделью в кириллический потолок $0.10,
    # и 480 слов туда не помещаются ($0.107). Она остаётся прежней длины,
    # если её собственный бюджет не задан явно.
    #
    # Ветка сохранена, хотя `free=True` теперь стоит ровно у одной главы: она —
    # то место, где «бесплатная короче» записано один раз, а не переписано в
    # `natal/core` руками. Кампания, открывающая вторую главу на неделю, не
    # должна вспоминать про длину.
    if kwargs.get("free") and "words" not in kwargs:
        kwargs["words"] = (180, 320)
        kwargs.setdefault("paragraphs", (2, 4))
    return Chapter(slug, numeral, index, title, question, reads, **kwargs)


NATAL: tuple[Chapter, ...] = (
    _c(1, "I", "core", "Core", "What am I really like underneath?",
       ("sun", "moon", "ascendant", "sect", "dominant"), free=True, time_dependent=True),
    _c(2, "II", "portrait", "Portrait", "How do I come across before I speak?",
       ("ascendant", "midheaven", "dominant", "element", "modality"), time_dependent=True),
    _c(3, "III", "love", "Love and closeness", "How do I attach and what breaks it?",
       ("venus", "moon", "house 7", "house 5", "descendant", "mars"), time_dependent=True),
    _c(4, "IV", "money", "Money and resources", "How does money actually reach me?",
       ("house 2", "house 8", "venus", "jupiter", "part of fortune"), time_dependent=True),
    _c(5, "V", "career", "Career and calling", "What work will not wear me out?",
       ("midheaven", "house 10", "house 6", "saturn", "sun"), time_dependent=True),
    _c(6, "VI", "mind", "Mind and speech", "How do I think and how do I sound?",
       ("mercury", "house 3", "house 9", "air"), time_dependent=True),
    _c(7, "VII", "shadow", "Shadow and wound", "What do I keep repeating?",
       ("chiron", "saturn", "pluto", "house 12", "house 8", "lilith"), time_dependent=True),
    _c(8, "VIII", "roots", "Roots and family", "What did I inherit without choosing?",
       ("imum coeli", "house 4", "moon", "saturn"), time_dependent=True),
    _c(9, "IX", "karmic-axis", "Karmic axis", "What am I being moved toward?",
       ("true_node", "north node", "house 12", "house 6"), time_dependent=True),
    _c(10, "X", "work-rhythms", "Work and rhythms", "What pace can I sustain?",
       ("house 6", "mars", "saturn", "modality", "moon phase"), time_dependent=True),
    _c(11, "XI", "transformation", "Crises and transformation", "How do I fall apart and how do I rebuild?",
       ("pluto", "house 8", "scorpio", "square", "opposition"), time_dependent=True),
    _c(12, "XII", "freedom", "Freedom and uniqueness", "Where do I refuse to be like anyone else?",
       ("uranus", "aquarius", "house 11", "house 1"), time_dependent=True),
    _c(13, "XIII", "dreams", "Dreams and boundaries", "Where do I lose my edges?",
       ("neptune", "pisces", "house 12", "moon"), time_dependent=True),
    _c(14, "XIV", "circle", "Circle and allies", "Who am I actually built to be around?",
       ("house 11", "jupiter", "venus", "air"), time_dependent=True),
    _c(15, "XV", "worldview", "Worldview and growth", "What do I believe when nobody is watching?",
       ("jupiter", "house 9", "sagittarius", "midheaven"), time_dependent=True),
    _c(16, "XVI", "milestones", "Milestones by age", "When does the shape of my life change?",
       ("saturn", "true_node", "configuration", "stellium"), time_dependent=True),
)

NUMEROLOGY: tuple[Chapter, ...] = (
    _c(1, "I", "life-path", "Life path", "What was I built to spend my life on?",
       ("life path", "destiny")),
    _c(2, "II", "birthday-number", "Birthday number", "What comes easily that I overlook?",
       ("birthday number", "karmic debt")),
    _c(3, "III", "personal-year", "Personal year", "What season am I actually in?",
       ("personal year", "personal month", "personal day"),
       # Живой скрин 29.08.2026: глава объяснила читателю, что «месяцев
       # четырнадцать» — движок отдаёт цикл строго 1–9 (numerology.py,
       # reduce_number), а «14» модель подобрала из соседних факторов
       # («day 14», «karmic debt 14») в блоке остальной карты.
       guidance=(
           "The personal year, month and day each run 1 through 9 — there "
           "is no personal month above 9, and a personal month is not a "
           "calendar month. Never state a cycle length other than 9."
       )),
    _c(4, "IV", "pinnacles", "Pinnacles and challenges", "What is being asked of me right now?",
       ("pinnacle", "challenge", "master number")),
    _c(5, "V", "name", "Name numbers", "What does the name I answer to carry?",
       ("expression", "soul urge", "personality", "maturity", "karmic lesson"),
       # Живой скрин 29.08.2026: числа выражения и желания стояли в главе
       # голыми итогами, и владелец спросил, откуда они взялись. Выкладки
       # движок выдаёт (`workings`: буква за буквой, сумма, свёртка) — глава
       # обязана провести читателя по ним, а не объявить результат.
       guidance=(
           "Show the arithmetic in plain words: name the spelling the "
           "letters were counted from (copy it exactly as given) and walk "
           "through the workings you were handed — which letters add to "
           "which sum, and how the sum reduces. Use only the letter values "
           "and sums present in the data; never invent or re-derive them."
       )),
)

BIRTH_CARD: tuple[Chapter, ...] = (
    _c(1, "I", "personality", "Personality card", "How do people read me?",
       ("Personality Card",)),
    _c(2, "II", "soul", "Soul card", "What runs underneath that?",
       ("Soul Card", "same card")),
    _c(3, "III", "year-card", "Year card", "What is this particular year for?",
       ("Year Card", "year", "of 9")),
)

TRANSITS: tuple[Chapter, ...] = (
    # A morning note, not an essay — the owner's verdict on the default
    # length was «слишком длинно». This chapter is also the Today screen's
    # day text, and a day text is read standing up.
    #
    # **И оно больше не бесплатно: «в транзитах нет бесплатного» (владелец,
    # 17.08.2026).** Транзиты — движок ежедневного гороскопа, то есть ровно то,
    # что продаётся подпиской; глава, переписываемая каждый день и раздаваемая
    # даром, — это подписка, за которую забыли взять деньги. Экран «Сегодня»
    # берёт свой дневной текст отсюда, так что у неподписчика он теперь
    # закрыт — и закрыт честно, с открывающим абзацем, а не молчанием.
    #
    # Длина осталась своей (90–150), хотя глава стала платной и получила бы
    # 300–480 по умолчанию: причина той длины — не тир, а то, что это дневная
    # заметка. Подписчик, читающий её стоя в метро, не просил разворот.
    # Guidance — из живого чтения владельцем 29.08.2026 («гороскоп даунский…
    # тут какой-то бред написан, это же будут читать обычные люди»): в одном
    # утреннем тексте сошлись «0°94′» (модель пересчитала орб 0.94° в
    # несуществующие минуты), «во вторник» (в пятницу: день недели выдуман) и
    # сцена-виньетка, в которой читатель себя не узнаёт. Каждое правило ниже —
    # против одной из этих трёх ошибок.
    _c(1, "I", "active", "What is active now", "What is actually happening to me?",
       ("transiting",), time_dependent=True,
       words=(90, 150), paragraphs=(1, 2), areas=True,
       guidance=(
           "This is read by an ordinary person over morning coffee: every "
           "sentence must be something they can recognise in their own day, "
           "in plain words. Copy orb figures exactly as written in the data "
           "(0.94°) — never convert degrees into minutes. Never name a "
           "weekday or a date: the screen prints today's date itself, and a "
           "wrong weekday reads as a broken product. No invented little "
           "scenes about specific moments; describe the tendency of the day."
       )),
    _c(2, "II", "ahead", "The months ahead", "What is coming and when?",
       ("transiting",), time_dependent=True),
    _c(3, "III", "long", "The long transits", "What is this whole chapter of my life about?",
       ("pluto", "neptune", "uranus", "saturn"), time_dependent=True),
)

SOLAR_RETURN: tuple[Chapter, ...] = (
    _c(1, "I", "year-shape", "The shape of the year", "What is this year for?",
       ("return ascendant", "return midheaven", "ruler of the year"),
       time_dependent=True),
    _c(2, "II", "emphasis", "Where the year lands", "Which part of my life does it touch?",
       ("angular", "return"), time_dependent=True),
    _c(3, "III", "contacts", "Where it meets your chart", "How does it connect to who I already am?",
       ("sits on natal", "opposes natal"), time_dependent=True),
)

COMPATIBILITY: tuple[Chapter, ...] = (
    # **Тизер «Притяжение» и эта глава — одно и то же**, решение владельца от
    # 17.08.2026. Отдельной бесплатной механики тизера больше нет: вместе с
    # `free=True` сняты `TEASER_CAP_DEFAULT`, счётчик `pair_teaser` и настройка
    # `pair.teaser_cap` в `billing/credits.py`. Глава закрыта как все прочие и
    # показывает открывающий абзац; бесплатным остаётся **расчёт**
    # совместимости, который и так ничего не стоит.
    _c(1, "I", "attraction", "What pulls", "Why this person and not another?",
       ("venus", "mars", "sun", "moon")),
    # Глифы в списке — не украшение: аспекты пары печатаются «□»/«☍», а не
    # словами, и до 29.08.2026 глава напряжения видела из своих факторов
    # только сатурн и числовой «friction score». Скор из факторов снят (сырая
    # внутренняя сумма читалась моделью как шкала — «у вас накал страстей
    # 3.4», — которую не объяснить читателю), и квадраты с оппозициями отданы
    # главе напрямую, знаками, какими они напечатаны.
    _c(2, "II", "friction", "Where it catches", "What will we keep arguing about?",
       ("□", "☍", "square", "opposition", "saturn", "friction", "tension")),
    _c(3, "III", "overlays", "Where we land in each other", "What part of my life does this person occupy?",
       ("falls in", "house"), time_dependent=True),
    _c(4, "IV", "together", "The two of you as one thing", "What is the relationship itself like?",
       ("composite", "davison")),
)

ASTROCARTOGRAPHY: tuple[Chapter, ...] = (
    _c(1, "I", "lines", "Your lines", "Which places bring out which part of me?",
       ("line",), time_dependent=True),
    # «current place» в списке — фактор настоящего города (`at your current
    # place: …`), который движок отдаёт, когда человек назвал, где живёт
    # (29.08.2026: глава звалась «Где ты сейчас», а считалась только от места
    # рождения). Без названного города фактора нет, и глава честно читает
    # рождение — но обязана говорить о нём как о месте рождения, не как о
    # «сейчас»: см. guidance.
    _c(2, "II", "here", "Where you are now", "How does where I live affect me?",
       ("at the birthplace", "at your current place", "line"),
       time_dependent=True,
       guidance=(
           "If the data carries an 'at your current place' reading, that is "
           "where the person lives now — read the chapter from it, and use "
           "the birthplace only as contrast. If it does not, say plainly "
           "that this is read from the birthplace, and never present the "
           "birthplace as where they are now."
       )),
    _c(3, "III", "crossings", "Crossings", "Where do two things happen at once?",
       ("crosses",), time_dependent=True),
)

SYNTHESIS: tuple[Chapter, ...] = (
    _c(1, "I", "agreement", "Where the systems agree", "What is true from more than one direction?",
       ("agree",)),
    _c(2, "II", "disagreement", "Where they disagree", "What contradiction do I actually live in?",
       ("disagree",), words=(220, 400)),
    _c(3, "III", "single", "What only one system sees", "What would I miss reading just one of these?",
       ("seen by one",)),
    _c(4, "IV", "whole", "All of it together", "So what does this add up to?",
       ("Direction", "Character", "Mind", "Relationships", "Resources",
        "Work", "Weak point", "Growth", "Rhythms"), words=(280, 500)),
)

BY_SYSTEM: dict[str, tuple[Chapter, ...]] = {
    "natal": NATAL,
    "numerology": NUMEROLOGY,
    "birth-card": BIRTH_CARD,
    "transits": TRANSITS,
    "solar-return": SOLAR_RETURN,
    "compatibility": COMPATIBILITY,
    "astrocartography": ASTROCARTOGRAPHY,
    "synthesis": SYNTHESIS,
}


def for_system(system: str) -> tuple[Chapter, ...]:
    try:
        return BY_SYSTEM[system]
    except KeyError:
        raise ValueError(f"no chapters defined for {system!r}") from None


def find(system: str, slug: str) -> Chapter:
    for chapter in for_system(system):
        if chapter.slug == slug:
            return chapter
    raise ValueError(f"{system} has no chapter {slug!r}")


def relevant_factors(chapter: Chapter, factors: list[str] | tuple[str, ...]) -> list[str]:
    """The subset of a CalcResult's factors this chapter may read from.

    Matching is by substring and deliberately generous — a chapter starved of
    factors produces either nothing or something invented, and the first is
    only acceptable when the chart genuinely has nothing to say.
    """
    needles = tuple(needle.lower() for needle in chapter.reads)
    return [f for f in factors if any(needle in f.lower() for needle in needles)]


def free_chapters(system: str) -> frozenset[str]:
    """Which chapters of this system stay open. Usually none.

    The single source of truth for this. It used to live in the entitlements
    module as a hand-written set of slugs, which drifted out of step with the
    chapters themselves — the paywall was exempting a chapter named "sun" that
    had been called "core" for some time, so the exemption never fired and the
    sample chapter was silently locked.

    **Пустое множество — теперь нормальный ответ.** Семь систем из восьми
    возвращают отсюда пустоту, и вызывающий не должен считать это поломкой:
    свободна ровно одна глава во всём продукте, `natal/core`. Всякий, кто
    пишет `next(iter(free_chapters(system)))`, ошибается на семи системах из
    восьми — спрашивать надо `chapter.free` у конкретной главы.
    """
    return frozenset(chapter.slug for chapter in for_system(system) if chapter.free)


# ── открывающий абзац закрытой главы ───────────────────────────────────────

#: Длина открывающего абзаца, `locked-chapter-spec.md` §2.5: «≈40 слов,
#: приходит от движка». Полоса вокруг сорока, а не точное число: писателю
#: задаётся диапазон, и «ровно 40» он всё равно не выдержит, зато будет резать
#: последнюю фразу.
OPENING_WORDS: tuple[int, int] = (34, 46)

#: Один абзац. Не два «покороче»: под ним начинается размытый филлер, и второй
#: настоящий абзац читался бы как обрыв на середине мысли.
OPENING_PARAGRAPHS: tuple[int, int] = (1, 1)


def opening_of(chapter: Chapter) -> Chapter:
    """Та же глава, ужатая до открывающего абзаца.

    **Производная от главы, а не отдельная сущность.** Слаг, вопрос и `reads`
    остаются теми же — то есть абзац пишется из тех же позиций, что и сама
    глава, проходит тот же валидатор цитат и попадает на тот же экран под тот
    же заголовок. Спека §7 проверяет это глазами: на закрытой главе обязан
    быть виден **написанный** текст с позициями, а не описание системы; сделать
    его из чего-то, кроме самой главы, значит написать описание системы.

    `advice=False` и `areas=False` — потому что «одно конкретное действие» под
    сорока словами это уже не абзац, а совет, купленный даром, а четыре строки
    областей Today рисует только оплаченная дневная глава.

    `free` намеренно **не** ставится в True. Это не бесплатная глава; это
    единственный текст, на который тратятся токены до оплаты, и роутер решает
    про его модель и потолок отдельно — см. `_write_opening` там.
    """
    return replace(
        chapter,
        words=OPENING_WORDS,
        paragraphs=OPENING_PARAGRAPHS,
        advice=False,
        areas=False,
    )
