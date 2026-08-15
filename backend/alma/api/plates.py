"""Вклейки глав — единственная картинка, которую продукт отдаёт по сети.

**Почему они здесь, а не в приложении.** Вклеек сорок, и каждая нужна ровно в
один момент — когда человек открывает свою главу. Это заведомо после сети: до
неё главы ещё нет. Вшитые в бандл, они удвоили бы вес приложения ради картинок,
которых большинство читателей никогда не увидит: восемь бесплатных глав из
сорока одной — это восемь вклеек, остальные тридцать три ждут покупки.

**Почему рядом с главами, а не на CDN.** Вклейка — это данные главы: тот же
слаг, тот же деплой, та же жизнь. Отдельный CDN добавил бы второй адрес, второй
сертификат и второй способ протухнуть, ничего не дав: файл отдаётся один раз за
установку и дальше живёт в кэше клиента.

**Авторизации нет намеренно.** Арт не секрет: он не про конкретного человека и
ничего о нём не сообщает. Запертая картинка потребовала бы токена на каждый
`<img>` и сломала бы кэш, ради защиты того, что и так есть в App Store в
скриншотах.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, Response

#: Год. Файл под этим именем никогда не меняется — меняется `?v=` в ссылке.
_YEAR = 60 * 60 * 24 * 365

PLATES = Path(__file__).resolve().parents[2] / "static" / "plates"

router = APIRouter(prefix="/static/plates", tags=["plates"])


def _etag(path: Path) -> str:
    """Слабый тег по содержимому: имя и размер соврут при перегонке, хэш — нет."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:32]
    return f'"{digest}"'


@router.get("/{name}.webp")
async def plate(name: str, request: Request) -> Response:
    """Одна вклейка по имени файла.

    Имя приходит из оглавления глав и в путь подставляется как есть — поэтому
    оно и проверяется здесь, а не доверяется: точка и слэш в имени превратили
    бы этот обработчик в чтение произвольного файла с диска.
    """
    if not name.replace("-", "").isalnum():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such plate")

    path = PLATES / f"{name}.webp"
    if not path.is_file():
        # 404, а не заглушка: клиент рисует арку с римской цифрой сам, и это
        # выглядит лучше, чем чужая картинка на месте отсутствующей.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such plate")

    tag = _etag(path)
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": tag})

    return FileResponse(
        path,
        media_type="image/webp",
        headers={
            "ETag": tag,
            # `immutable` — обещание, которое мы можем сдержать: содержимое под
            # этим именем не меняется, а новая версия приезжает новым `?v=`.
            "Cache-Control": f"public, max-age={_YEAR}, immutable",
        },
    )
