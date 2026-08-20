"""Alma in Russian.

The 41 chapter titles and questions and the nine pairs of synthesis poles,
in Russian. Nothing else belongs in this file: the structure they hang on —
which factors a chapter reads from, its word budget, whether it needs a birth
time — lives in `alma/ai/chapters.py`, and the axis *names* are identifiers
that stay English everywhere. `alma/i18n/__init__.py` explains why.

What these strings are, so they are written as what they are.

A **title** is a noun phrase of two or three words: the name of a room in
somebody's chart. Not a heading, not a sentence.

A **question** is the reader's own, in their own voice, and it is the reason
they tap. It is a question somebody asks themselves at two in the morning,
and it stays theirs in Russian.

A **pole** is a short clause describing a way of being, and the pair has to
read as two ends of one line — the reader sees both at once, under the axis
they disagree about.

Alma's voice is plain, exact, a little cool. Never breathy, never flattering,
never mystical for its own sake; concrete over cosmic. She addresses the
reader as «ты», the same register every other language ships in.

**The rule Russian has to work hardest for: nothing here picks the reader's
gender.** Russian gender lives in past-tense verbs, participles and
adjectives — «какой я», «я выбирал», «остаться незамеченным» each tell half
of Alma's readers she assumed they were men. So every question is built in
the present tense or on impersonal constructions: «Что во мне настоящее»
rather than «какой я», «Что мне досталось без спроса?» rather than «что я
унаследовал», «Куда меня ведёт?» with the agentless third person the Spanish
file reached for with «llevar». The poles are third-person present or hang on
nouns — «боится остаться вне поля зрения», not «незамеченным». No participle,
no adjective and no pronoun in these 100 strings agrees with the person
reading them.

**«Сезон» is one thread, deliberately.** The Rhythms poles and the personal
year chapter are the same idea in two places — a stretch of time that opens
and closes — and a reader who meets «сезон, который открывается» under an
axis should recognise the word when the numerology chapter asks which one
they are in.

What `tests/test_locales.py` will not let through: a key added, removed or
renamed; a title or a question left blank; a question that does not end in a
question mark, or a title that does; a file left half-done with `WRITTEN`
still False; and, once `WRITTEN` is True, any string still identical to the
English and not listed in `SHARED`. Translate the values. Leave every key —
and the nine axis names, which are identifiers the model cites and the
validator checks — exactly as they are.
"""

from __future__ import annotations

from .words import AxisWords, ChapterWords

#: Every one of the 100 strings below is Russian. From here on, any string
#: that matches the English character for character fails the suite unless it
#: is listed in `SHARED`.
WRITTEN = True

#: Words that are correctly the same in Russian as in English. Empty, and not
#: for lack of looking: Cyrillic guarantees that nothing here can match the
#: English character for character.
SHARED: frozenset[str] = frozenset()

CHAPTERS: dict[str, dict[str, ChapterWords]] = {
    "natal": {
        "core": ChapterWords(
            # **Our own copy was breaking our own rule.**
            #
            # This said «Ядро», and «ядро» is the first word on the banned list
            # in `validator._PURPLE["ru"]` — the list the owner dictated, from
            # the paragraph that angered him. The gate only ever reads what the
            # model writes, so the catalogue walked straight past it and the
            # very first free chapter greeted a Russian reader with the exact
            # word we refuse to let Alma use. Seen on a phone, 9 August 2026.
            #
            # «Основа» says the same thing with a word people use about houses
            # and arguments: what everything else stands on.
            title="Основа",
            # The question went the same way: «Что во мне настоящее, под всем
            # остальным?» is verbatim the phrase the specification bans, and it
            # promises a hidden real self underneath a false one — which is the
            # horoscope move this product exists to avoid. What the chapter
            # actually reads is the fixed part of the chart: Sun sign, dominant
            # sign, element and modality, the stellium. So it asks about that,
            # in words the reader can check against their own life.
            #
            # «Какой я» would gender the reader on the first screen. This asks
            # the same thing of everybody.
            question="Что во мне не меняется?",
        ),
        "portrait": ChapterWords(
            title="Портрет",
            question="Как меня видят, пока я молчу?",
        ),
        "love": ChapterWords(
            title="Любовь и близость",
            question="Как я привязываюсь и что это ломает?",
        ),
        "money": ChapterWords(
            title="Деньги и ресурсы",
            question="Как деньги на самом деле приходят ко мне?",
        ),
        "career": ChapterWords(
            title="Карьера и призвание",
            question="Какая работа меня не истощит?",
        ),
        "mind": ChapterWords(
            title="Ум и речь",
            question="Как я думаю и как говорю?",
        ),
        "shadow": ChapterWords(
            title="Тень и рана",
            question="Что я повторяю снова и снова?",
        ),
        "roots": ChapterWords(
            title="Корни и семья",
            # «Что я унаследовал» is masculine. «Досталось» agrees with «что»,
            # so it is everybody's, and «без спроса» is how a person says
            # "without being asked" about their own family.
            question="Что мне досталось без спроса?",
        ),
        "karmic-axis": ChapterWords(
            title="Кармическая ось",
            # The agentless «ведёт» carries the English passive: something is
            # doing the moving, and it is not the reader.
            question="Куда меня ведёт?",
        ),
        "work-rhythms": ChapterWords(
            title="Работа и ритмы",
            question="Какой темп я могу выдержать?",
        ),
        "transformation": ChapterWords(
            title="Кризисы и трансформация",
            question="Как я разваливаюсь и как собираю себя заново?",
        ),
        "freedom": ChapterWords(
            title="Свобода и непохожесть",
            question="Где я отказываюсь быть как все?",
        ),
        "dreams": ChapterWords(
            title="Мечты и границы",
            question="Где я теряю границы?",
        ),
        "circle": ChapterWords(
            title="Круг и союзники",
            # «Быть рядом с кем» is a construction; «по пути» is what a person
            # says — and it keeps the question about companionship rather
            # than geography.
            question="С кем мне и правда по пути?",
        ),
        "worldview": ChapterWords(
            title="Взгляды и рост",
            question="Во что я верю, когда никто не видит?",
        ),
        "milestones": ChapterWords(
            title="Возрастные рубежи",
            question="Когда моя жизнь меняет форму?",
        ),
    },
    "numerology": {
        "life-path": ChapterWords(
            title="Жизненный путь",
            # "Built to spend my life on" has no Russian that keeps the
            # machinery metaphor without gendering the reader («устроен»).
            # «Рассчитана» agrees with «жизнь», so it is safe — and it keeps
            # the sense of design rather than fate.
            question="На что рассчитана моя жизнь?",
        ),
        "birthday-number": ChapterWords(
            title="Число дня рождения",
            question="Что даётся мне легко, а я не замечаю?",
        ),
        "personal-year": ChapterWords(
            title="Личный год",
            question="Какой у меня сейчас сезон?",
        ),
        "pinnacles": ChapterWords(
            title="Вершины и вызовы",
            question="Что от меня сейчас требуется?",
        ),
        "name": ChapterWords(
            title="Числа имени",
            question="Что несёт имя, на которое я откликаюсь?",
        ),
    },
    "birth-card": {
        "personality": ChapterWords(
            title="Карта личности",
            question="Как меня считывают люди?",
        ),
        "soul": ChapterWords(
            title="Карта души",
            question="А что под этим?",
        ),
        "year-card": ChapterWords(
            title="Карта года",
            question="Для чего именно этот год?",
        ),
    },
    "transits": {
        "active": ChapterWords(
            title="Что активно сейчас",
            question="Что со мной происходит на самом деле?",
        ),
        "ahead": ChapterWords(
            title="Ближайшие месяцы",
            question="Что впереди и когда?",
        ),
        "long": ChapterWords(
            title="Долгие транзиты",
            question="О чём эта глава моей жизни?",
        ),
    },
    "solar-return": {
        "year-shape": ChapterWords(
            title="Форма года",
            question="Для чего этот год?",
        ),
        "emphasis": ChapterWords(
            title="Куда ложится год",
            question="Какой части моей жизни он касается?",
        ),
        "contacts": ChapterWords(
            title="Где он встречает твою карту",
            # "Who I already am" would be «кто я» plus a gendered adjective in
            # any natural phrasing; «что во мне уже есть» asks the same
            # question of everybody.
            question="Как это соединяется с тем, что во мне уже есть?",
        ),
    },
    "compatibility": {
        "attraction": ChapterWords(
            title="Что притягивает",
            question="Почему именно этот человек, а не другой?",
        ),
        "friction": ChapterWords(
            title="Где цепляет",
            question="О чём мы будем спорить снова и снова?",
        ),
        "overlays": ChapterWords(
            title="Куда мы попадаем в жизни друг друга",
            question="Какую часть моей жизни занимает этот человек?",
        ),
        "together": ChapterWords(
            title="Двое как одно",
            question="А какие они сами, эти отношения?",
        ),
    },
    "astrocartography": {
        "lines": ChapterWords(
            title="Твои линии",
            question="Какие места усиливают какую часть меня?",
        ),
        "here": ChapterWords(
            title="Где ты сейчас",
            question="Как на меня влияет место, где я живу?",
        ),
        "crossings": ChapterWords(
            title="Пересечения",
            question="Где происходят сразу две вещи?",
        ),
    },
    "synthesis": {
        "agreement": ChapterWords(
            title="Где системы согласны",
            question="Что подтверждается с разных сторон?",
        ),
        "disagreement": ChapterWords(
            title="Где они расходятся",
            question="В каком противоречии я живу на самом деле?",
        ),
        "single": ChapterWords(
            title="Что видит только одна система",
            question="Что я упущу, читая только одну из них?",
        ),
        "whole": ChapterWords(
            title="Всё вместе",
            question="И что из этого складывается?",
        ),
    },
}

#: The nine pairs of poles, keyed by the English axis names — identifiers the
#: model cites and the validator checks, never translated.
AXES: dict[str, AxisWords] = {
    "Direction": AxisWords(
        negative="работает в одиночку, вне поля зрения",
        positive="работает на публике, у всех на виду",
    ),
    "Character": AxisWords(
        negative="держит позицию",
        positive="меняет форму",
    ),
    "Mind": AxisWords(
        negative="сначала требует доказательств",
        positive="доверяет первому впечатлению",
    ),
    "Relationships": AxisWords(
        negative="нужна открытая дверь",
        positive="нужен свидетель",
    ),
    "Resources": AxisWords(
        negative="строит своё",
        positive="получает через других людей",
    ),
    "Work": AxisWords(
        negative="один большой рывок",
        positive="понемногу, но каждый день",
    ),
    # «Незамеченным» would be the natural word and it is masculine; the fear
    # hangs on «поле зрения» instead, which is nobody's gender.
    "Weak point": AxisWords(
        negative="боится остаться вне поля зрения",
        positive="боится оказаться у всех на виду",
    ),
    # The English "asked to" is agentless; «жизнь зовёт» keeps the agent
    # outside the reader without a passive participle to decline.
    "Growth": AxisWords(
        negative="жизнь зовёт в тень",
        positive="жизнь зовёт на свет",
    ),
    "Rhythms": AxisWords(
        negative="сезон, который закрывается",
        positive="сезон, который открывается",
    ),
}
