#!/usr/bin/env python3
"""Разложить присланные вклейки глав по местам — в один заход.

Владелец присылает картинки как есть: PNG из Midjourney, любого размера, с
именами вроде `Anatolii_a_winding_golden_road_….png`. Продукту нужны шесть
файлов ровно определённых имён, в WebP и одного размера с остальными
тридцатью пятью — 620×780. Между этими двумя фактами и стоит этот скрипт:
иначе разложить шесть картинок значит шесть раз не ошибиться руками.

Как пользоваться:

    # положить шесть файлов в любую папку, назвав их 1.png … 6.png
    # (порядок — как в docs/plates-map.md), затем:
    backend/.venv/bin/python backend/tools/add_plates.py ~/Downloads/plates

    # или назвать файлы конечными именами и не думать о порядке:
    backend/.venv/bin/python backend/tools/add_plates.py ~/Downloads/plates --by-name

Скрипт **не трогает** ничего, кроме шести целевых файлов, и перед записью
показывает, что куда положит; `--dry-run` печатает и выходит.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

#: Порядок — тот же, что в `docs/plates-map.md`: по нему владелец и получает
#: промты, по нему же нумерует присланные файлы.
ORDER = [
    ("plate-road", "нумерология · жизненный путь"),
    ("plate-seal", "нумерология · число дня рождения"),
    ("plate-ahead", "транзиты · что впереди"),
    ("plate-longwave", "транзиты · долгие волны"),
    ("plate-here", "астрокартография · где я сейчас"),
    ("plate-crossings", "астрокартография · пересечения"),
]

#: Размер и качество — те же, что у тридцати пяти уже лежащих вклеек. Не
#: «примерно те же»: арка на странице главы обрезает картинку по своим
#: пропорциям, и файл другого отношения сторон обрежется не так, как соседние.
SIZE = (620, 780)
QUALITY = 80

TARGET = Path(__file__).resolve().parent.parent / "static" / "plates"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="папка с присланными картинками")
    parser.add_argument("--by-name", action="store_true",
                        help="брать файлы по конечным именам, а не по номерам 1…6")
    parser.add_argument("--dry-run", action="store_true", help="только показать план")
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("нужен Pillow:  backend/.venv/bin/pip install pillow", file=sys.stderr)
        return 2

    if not args.source.is_dir():
        print(f"нет такой папки: {args.source}", file=sys.stderr)
        return 2

    plan: list[tuple[Path, Path, str]] = []
    for index, (name, what) in enumerate(ORDER, start=1):
        if args.by_name:
            found = sorted(args.source.glob(f"{name}.*"))
        else:
            found = sorted(args.source.glob(f"{index}.*"))
        found = [f for f in found if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
        if not found:
            print(f"не нашёл картинку для «{what}» "
                  f"({'по имени ' + name if args.by_name else 'под номером ' + str(index)})",
                  file=sys.stderr)
            return 1
        plan.append((found[0], TARGET / f"{name}.webp", what))

    print("положу так:")
    for src, dst, what in plan:
        print(f"  {src.name}\n     → {dst.name}   ({what})")
    if args.dry_run:
        return 0

    for src, dst, _ in plan:
        image = Image.open(src).convert("RGB")
        # Обрезка по центру до 4:5, а не растяжение: растянутая картина видна
        # сразу — на лицах и на архитектуре, которых в этих вклейках много.
        want = SIZE[0] / SIZE[1]
        have = image.width / image.height
        if have > want:
            new = int(image.height * want)
            left = (image.width - new) // 2
            image = image.crop((left, 0, left + new, image.height))
        elif have < want:
            new = int(image.width / want)
            top = (image.height - new) // 2
            image = image.crop((0, top, image.width, top + new))
        image = image.resize(SIZE, Image.LANCZOS)
        image.save(dst, "WEBP", quality=QUALITY, method=6)
        print(f"записал {dst.name}  {dst.stat().st_size // 1024} КБ")

    print("\nготово. Приложение подхватит их без пересборки — вклейки живут на "
          "сервере; если сервер уже запущен, перезапускать его не нужно.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
