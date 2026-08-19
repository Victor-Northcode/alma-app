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

## numerology (5/5)
| слаг | файл |
|---|---|
| life-path | plate-road |
| birthday-number | plate-seal |
| personal-year | plate-year |
| pinnacles | plate-eleven |
| name | plate-expression |

## birth-card (3/3)
personality → plate-personality · soul → plate-soulcard · year-card → plate-yearcard

## transits (3/3)
active → plate-sky · ahead → plate-ahead · long → plate-longwave

## solar-return (3/3)
year-shape → plate-solar · emphasis → plate-yeartheme · contacts → plate-yearlesson

## compatibility (4/4)
attraction → plate-pull · friction → plate-catches · overlays → plate-veil · together → plate-tender

## astrocartography (3/3)
lines → plate-lines · here → plate-here · crossings → plate-crossings
(`plate-whereto` стоял здесь времянкой и теперь свободен — ни одной главой не занят.)

## synthesis (1 вклейка на все 4 главы — осознанно)
agreement, disagreement, single, whole → plate-synthesis.
Синтез — система «всё вместе», одна картина на систему здесь правило, а не дыра.

## Правила PlateArch
- Ненайденный файл → арка с римской цифрой главы на пергаменте, никогда пустота.
- Времянок больше нет: 19.08.2026 владелец прислал шесть недостающих картин, и у каждой из 41 главы своя. Сторож — `mobile/flutter/alma/test/plates_test.dart`: он падает, если появится глава без картины или имя без файла на диске.

## Как добавить вклейку

Картинки приходят как есть — PNG или WebP любого размера. Продукту нужен ровно один формат, общий с остальными сорока: WebP 620×780 q80, обрезка по центру (не растяжение — растянутая картина видна на лицах и архитектуре, которых здесь много). Руками это шесть шансов ошибиться, поэтому есть скрипт:

```bash
backend/.venv/bin/python backend/tools/add_plates.py ~/Downloads/plates
```

Файлы в папке нумеруются `1.png` … `6.png` в порядке промптов ниже; `--by-name` берёт их по конечным именам, `--dry-run` только печатает план. Скрипт не трогает ничего, кроме названных файлов. Приложение подхватывает вклейки без пересборки — они живут на сервере.

## Промпты шести последних (все с --sref жрицы, --ar 4:5)
Сохранены не для повторения, а чтобы замена держала строй, если картину захочется перерисовать.

1. **numerology/life-path** → `plate-road` — a winding golden road across a dark starfield seen from above, milestones as small stars, antique gold filigree border, baroque oil painting, deep navy and gold
2. **numerology/birthday-number** → `plate-seal` — an ornate gilded seal stamped on parchment glowing among stars, a single blank cartouche at its center, baroque still life, deep navy and antique gold
3. **transits/ahead** → `plate-ahead` — a comet arcing over a row of waning and waxing moons like a calendar, dark luxury sky, antique gold detail, baroque painting
4. **transits/long** → `plate-longwave` — three colossal slow planets stacked deep in space, tiny gilded observer below, oil painting, deep navy, antique gold rim light
5. **astrocartography/here** → `plate-here` — a lone figure standing on a glowing gold point of an antique celestial map, meridian lines radiating, baroque, deep navy and gold
6. **astrocartography/crossings** → `plate-crossings` — two golden ley lines crossing over a dark ocean globe, a bright star born at the intersection, antique map style, baroque, navy and gold
