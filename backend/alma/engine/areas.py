"""Which part of a life a transit lands in.

**Why this exists.** The owner asked for «Гороскоп на сегодня» — a horoscope,
in the word an ordinary person uses for the thing they are looking for. What he
did not ask for, and what this product cannot ship, is a text written for one
twelfth of humanity: nothing about it is computed from a chart, so nothing in it
could be cited, and the whole argument the app makes to its readers and to App
Review rests on the opposite.

The shape a horoscope has, though, is not the lie. Work, love, money, the body:
those are the questions people arrive with, and a reading that answers them in
that order is easier to use than one that lists aspects by orb. So the *form* is
borrowed and the *content* stays this person's own — each area names the real
transit touching it, with the date it perfects, and an area with nothing in it
says so rather than being filled.

**The mapping is by natal point, not by house, and that is deliberate.** Houses
are the traditional answer and they are unavailable to half the readers: without
a birth time there are no houses at all, and the daily still has to work for
them. Every natal point a transit can touch has a settled meaning that survives
a missing hour — Venus is what somebody wants from other people whether or not
we know which house it sits in — so the point is what decides the area, and the
house is not consulted.

The four areas are the four the owner named. Nothing is invented to fill a
fifth; a transit whose point belongs to none of them is simply not shown under a
heading, and it still appears in the full list.
"""

from __future__ import annotations

#: Life area → the natal points that speak for it.
#:
#: Each assignment is the point's ordinary meaning rather than a scheme:
#:
#: * **work** — the Midheaven is the career point by definition, Saturn is what
#:   is asked of you, Mars is how you push, Jupiter is where it opens out.
#: * **love** — the Descendant is the partnership axis, Venus is wanting, the
#:   Moon is what it feels like from inside, Juno is the promise.
#: * **money** — the Sun is what you are worth to yourself and Venus is what you
#:   value; Venus is in two areas on purpose, because it genuinely is.
#: * **body** — the Ascendant is the body as it meets the world, Mercury is the
#:   nervous system's pace, Chiron is the old injury, Neptune the thing that
#:   blurs.
#:
#: Pluto and Uranus are absent. They touch everything, which means they
#: distinguish nothing, and putting them under one heading would be choosing for
#: the reader.
AREAS: dict[str, tuple[str, ...]] = {
    "work": ("midheaven", "saturn", "mars", "jupiter"),
    "love": ("descendant", "venus", "moon", "juno"),
    "money": ("sun", "venus", "part_of_fortune"),
    "body": ("ascendant", "mercury", "chiron", "neptune"),
}

#: The order they are read in. Work first because it is what people open the app
#: about on a weekday, the body last because it is the one nobody asks for and
#: everybody reads.
ORDER: tuple[str, ...] = ("work", "love", "money", "body")


def area_of(natal_point: str) -> str | None:
    """The area a transit to this natal point belongs to, or None.

    First match in `ORDER`, so a point in two areas — Venus — is reported under
    the earlier one and never twice. A reader meeting the same transit under two
    headings would reasonably conclude the app was padding.
    """
    point = natal_point.lower()
    for area in ORDER:
        if point in AREAS[area]:
            return area
    return None
