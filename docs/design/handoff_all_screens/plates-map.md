# Вклейки глав → файлы (карта для PlateArch)

Источник истины по слагам: `backend/alma/ai/chapters.py` (41 глава).
Файлы: `plate-*.webp` (из оригиналов пакета, 620×780 q80).
Помимо глав: `plate-moon` — вклейка ежедневника **Today (S1)**, главой не является.

## natal (16/16 — полный)
| слаг | файл |
|---|---|
| core | plate-shape |
| portrait | plate-face |
| love | plate-love |
| money | plate-money |
| career | plate-calling |
| mind | plate-speech |
| shadow | plate-depths |
| roots | plate-home |
| karmic-axis | plate-repeats |
| work-rhythms | plate-sun |
| transformation | plate-crisis |
| freedom | plate-freedom |
| dreams | plate-dreams |
| circle | plate-friends |
| worldview | plate-faith |
| milestones | plate-saturn |

## numerology (3/5 + 1 времянка)
| слаг | файл |
|---|---|
| life-path | plate-soulurge — ВРЕМЯННО, до генерации «дороги» (промпт №1) |
| birthday-number | — (fallback-арка с цифрой, промпт №2) |
| personal-year | plate-year |
| pinnacles | plate-eleven |
| name | plate-expression |

## birth-card (3/3)
personality → plate-personality · soul → plate-soulcard · year-card → plate-yearcard

## transits (1/3)
active → plate-sky · ahead → — (промпт №3) · long → — (промпт №4)

## solar-return (3/3)
year-shape → plate-solar · emphasis → plate-yeartheme · contacts → plate-yearlesson

## compatibility (4/4)
attraction → plate-pull · friction → plate-catches · overlays → plate-veil · together → plate-tender

## astrocartography (2/3)
lines → plate-lines · here → plate-whereto (приемлемо: «где я сейчас» ≈ дороги/точка; замена — промпт №5) · crossings → — (промпт №6)

## synthesis (1 вклейка на все 4 главы — осознанно)
agreement, disagreement, single, whole → plate-synthesis.
Синтез — система «всё вместе», одна картина на систему здесь правило, а не дыра.

## Правила PlateArch
- Ненайденный файл → арка с римской цифрой главы на пергаменте, никогда пустота.
- Времянки помечены в этом файле; после генерации шести новых артов обновить только эту таблицу.

## 6 недостающих — промпты Midjourney (все с --sref жрицы, --ar 4:5)
1. **numerology/life-path** — a winding golden road across a dark starfield seen from above, milestones as small stars, antique gold filigree border, baroque oil painting, deep navy and gold
2. **numerology/birthday-number** — an ornate gilded seal stamped on parchment glowing among stars, a single blank cartouche at its center, baroque still life, deep navy and antique gold
3. **transits/ahead** — a comet arcing over a row of waning and waxing moons like a calendar, dark luxury sky, antique gold detail, baroque painting
4. **transits/long** — three colossal slow planets stacked deep in space, tiny gilded observer below, oil painting, deep navy, antique gold rim light
5. **astrocartography/here** — a lone figure standing on a glowing gold point of an antique celestial map, meridian lines radiating, baroque, deep navy and gold
6. **astrocartography/crossings** — two golden ley lines crossing over a dark ocean globe, a bright star born at the intersection, antique map style, baroque, navy and gold
