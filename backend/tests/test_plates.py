"""Вклейки отдаются один раз за установку, а не при каждом открытии главы.

Весь смысл этой ручки — в заголовках: если кэш описан неверно, сорок картинок
по сто с лишним килобайт поедут заново каждый раз, когда человек откроет главу,
и на мобильном интернете это будет заметно ему, а не нам.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from alma.api.app import create_app
from alma.api.plates import PLATES


@pytest.fixture
def name() -> str:
    """Любая существующая вклейка — их набор ещё меняется, имя брать нельзя."""
    files = sorted(PLATES.glob("*.webp"))
    if not files:
        pytest.skip("вклейки не перегнаны в этом чекауте")
    return files[0].stem


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def test_plate_is_served_as_webp(client, name: str) -> None:
    r = await client.get(f"/static/plates/{name}.webp")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/webp"
    assert len(r.content) > 1000, "картинка подозрительно лёгкая"


async def test_cached_for_a_year_and_immutable(client, name: str) -> None:
    """`immutable` — обещание, и оно выполнимо: имя файла не переиспользуется.

    Без него браузер и `NSURLCache` перепроверяют картинку на каждом показе
    условным запросом. Он дешёвый, но он есть, а вклейка меняется никогда.
    """
    r = await client.get(f"/static/plates/{name}.webp")
    cache = r.headers["cache-control"]
    assert "immutable" in cache
    assert "max-age=31536000" in cache
    assert "public" in cache


async def test_second_request_with_the_tag_gets_304(client, name: str) -> None:
    first = await client.get(f"/static/plates/{name}.webp")
    tag = first.headers["etag"]
    again = await client.get(
        f"/static/plates/{name}.webp", headers={"If-None-Match": tag}
    )
    assert again.status_code == 304
    assert again.content == b"", "304 не несёт тела — иначе кэш бессмыслен"


async def test_missing_plate_is_404_and_not_a_stand_in(client) -> None:
    """404, а не чужая картинка: клиент рисует арку с римской цифрой сам."""
    r = await client.get("/static/plates/plate-that-does-not-exist.webp")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "attempt",
    ["../../config", "..%2F..%2Fconfig", "plate-love/../../../etc/passwd"],
)
async def test_the_name_cannot_walk_out_of_the_folder(client, attempt: str) -> None:
    """Имя подставляется в путь, значит оно проверяется, а не принимается.

    Точка и слэш в имени превратили бы эту ручку в чтение произвольного файла
    с диска — а она открыта без авторизации, потому что арт не секрет.
    """
    r = await client.get(f"/static/plates/{attempt}.webp")
    assert r.status_code in (404, 400)
