"""Длинные немецкие и русские слова в теле текста несут мягкий перенос.

**Почему это тест, а не памятка.** Flutter не переносит слова: движок рвёт
строку только по пробелам, автоматической расстановки нет ни для одного языка.
Немецкий словообразователен — «Kompatibilitätsdeutungen» это двадцать четыре
знака одним куском, — и в колонке телефона такое слово либо выпирает за поле,
либо утаскивает за собой пустую строку. Единственный способ переноса, который
у нас есть, — мягкий перенос `\\u00AD`, поставленный в самой строке.

Ставит его человек, и в этом слабое место: через месяц новая строка приедет без
разметки, и никто не заметит, пока не увидит немецкий экран. Регексп заметит.

**Что считается телом.** Строка длиннее трёх слов. Всё, что короче, — подпись:
название системы, метка факта, ярлык юридической ссылки, подпись кнопки. Их
переносить нельзя по правилу владельца: у кнопки работает лестница ужатия
16.5 → 15 → 14 и затем короткий словарный вариант, а мягкий перенос в кнопке —
баг, а не решение. Заголовки Playfair тоже не рвут: длинное слово в титуле
уместнее кеглем на шаг ниже.

Библиотеку переносов по образцам Кнута — Лиана сюда сознательно не берут: две-
три сотни килобайт на язык ради полутора десятков слов — плохой размен, а
недетерминированный перенос в пейволльной строке ещё и юридический риск. Строка
«verlängert sich…» обязана выглядеть одинаково у всех.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

L10N = Path(__file__).resolve().parents[2] / "mobile/flutter/alma/lib/l10n"

#: Языки, где длинное слово — обычное дело. Остальные пять переносов не просят.
HYPHENATED = {"de": "app_de.arb", "ru": "app_ru.arb"}

SOFT = "­"

#: Длина, за которой слово перестаёт помещаться в колонку телефона.
LIMIT = 14

#: Слова, которые не размечают, даже встретив их в теле.
#:
#: Топонимы сюда не попадают: места приходят из API и обрезаются эллипсисом, в
#: каталоге строк их нет вовсе. Здесь — то, что рвать нельзя по смыслу.
ALLOWED = {
    "Alma",
}

#: Строка короче этого — подпись, а не тело.
BODY_WORDS = 3

_WORD = re.compile(r"[^\s­\-—·,.:;!?()«»\"'/\[\]{}]+")


def _strings(locale: str) -> dict[str, str]:
    data = json.loads((L10N / HYPHENATED[locale]).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("@") and isinstance(v, str)}


@pytest.mark.parametrize("locale", sorted(HYPHENATED))
def test_long_words_in_body_carry_a_soft_hyphen(locale: str) -> None:
    offenders: list[str] = []
    for key, value in _strings(locale).items():
        words = _WORD.findall(value)
        if len(words) <= BODY_WORDS:
            continue  # подпись — не переносим намеренно
        for word in words:
            if len(word) <= LIMIT or word in ALLOWED or SOFT in word:
                continue
            offenders.append(f"{key}: {word!r} ({len(word)} знаков)")

    assert not offenders, (
        f"в {locale} есть длинные слова без мягкого переноса — во Flutter они "
        "не перенесутся и выпрут за поле:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("locale", sorted(HYPHENATED))
def test_labels_and_buttons_are_never_hyphenated(locale: str) -> None:
    """Обратная сторона правила, и она важнее первой.

    Мягкий перенос в подписи кнопки — это кнопка, которая на узком экране
    разъезжается на две строки вместо того, чтобы взять короткий вариант
    текста. Проверяется тем же порогом в три слова.
    """
    offenders = [
        f"{key}: {value!r}"
        for key, value in _strings(locale).items()
        if SOFT in value and len(_WORD.findall(value)) <= BODY_WORDS
    ]
    assert not offenders, (
        f"в {locale} мягкий перенос попал в подпись — там работает ужатие и "
        "короткий вариант строки, а не перенос:\n  " + "\n  ".join(offenders)
    )


def test_soft_hyphen_never_reaches_the_other_five_languages() -> None:
    """Английский, испанский, итальянский, французский и португальский.

    Их слова короткие, разметка им не нужна, и попавший туда невидимый знак —
    это мусор, который однажды приедет в поиск или в буфер обмена.
    """
    others = {
        "en": "app_en.arb", "es": "app_es.arb", "it": "app_it.arb",
        "fr": "app_fr.arb", "pt-BR": "app_pt.arb",
    }
    dirty: list[str] = []
    for locale, name in others.items():
        data = json.loads((L10N / name).read_text(encoding="utf-8"))
        dirty += [
            f"{locale}/{k}" for k, v in data.items()
            if not k.startswith("@") and isinstance(v, str) and SOFT in v
        ]
    assert not dirty, "мягкий перенос там, где он не нужен: " + ", ".join(dirty)
