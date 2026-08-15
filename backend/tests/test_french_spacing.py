"""Французская типографика: узкий неразрывный пробел перед двойными знаками.

**Почему это тест, а не вкус.** Во французском перед `?`, `!`, `;`, `:` и
внутри кавычек-ёлочек стоит пробел — но не обычный. Обычный переносится: строка
рвётся, и вопросительный знак уезжает на следующую строку один. Узкий
неразрывный `U+202F` не рвётся и уже обычного, поэтому «est le tien ?» выглядит
французским текстом, а не английским с лишним пробелом.

Правило действует **на всю локаль разом**. Ровно так владелец распорядился с
обращением: «если во fr.arb принято vous — приведите к vous везде разом».
Половина файла по одному правилу, половина по другому — хуже любой из
половин, потому что читается неряшливостью, а не решением.

Остальные шесть языков этого знака не знают, и попавший туда невидимый пробел —
мусор: он приедет в поиск, в буфер обмена и в чужой текстовый редактор.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

L10N = Path(__file__).resolve().parents[2] / "mobile/flutter/alma/lib/l10n"

NNBSP = " "

#: Знаки, которым во французском положен пробел слева.
DOUBLE = "?!;:"


def _strings(name: str) -> dict[str, str]:
    data = json.loads((L10N / name).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("@") and isinstance(v, str)}


def test_french_uses_the_narrow_space_before_double_marks() -> None:
    offenders = [
        f"{key}: {value!r}"
        for key, value in _strings("app_fr.arb").items()
        if re.search(rf" [{re.escape(DOUBLE)}]", value)
    ]
    assert not offenders, (
        "во французском остался обычный пробел перед двойным знаком — он "
        "переносится, и знак уедет на следующую строку один:\n  "
        + "\n  ".join(offenders)
    )


def test_french_guillemets_hug_their_text_with_the_narrow_space() -> None:
    offenders = [
        f"{key}: {value!r}"
        for key, value in _strings("app_fr.arb").items()
        if "« " in value or " »" in value
    ]
    assert not offenders, (
        "внутри ёлочек нужен тот же узкий неразрывный:\n  " + "\n  ".join(offenders)
    )


def test_the_narrow_space_never_reaches_the_other_six_languages() -> None:
    others = {
        "en": "app_en.arb", "ru": "app_ru.arb", "de": "app_de.arb",
        "es": "app_es.arb", "it": "app_it.arb", "pt-BR": "app_pt.arb",
    }
    dirty = [
        f"{locale}/{key}: {value!r}"
        for locale, name in others.items()
        for key, value in _strings(name).items()
        if NNBSP in value
    ]
    assert not dirty, (
        "узкий неразрывный пробел — правило одного языка:\n  " + "\n  ".join(dirty)
    )


def test_the_rule_actually_applies_somewhere() -> None:
    """Страховка от теста, который зелен, потому что проверять нечего.

    Три проверки выше пройдут и на файле без единого двойного знака. Эта
    падает, если французский вдруг лишился их всех, — то есть если правило
    выполнили удалением текста, а не расстановкой пробелов.
    """
    marked = sum(value.count(NNBSP) for value in _strings("app_fr.arb").values())
    assert marked >= 20, f"узких пробелов всего {marked} — правило где-то потерялось"
