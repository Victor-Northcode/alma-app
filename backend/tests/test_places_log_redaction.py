"""Access-лог не хранит, что человек набрал про место своего рождения.

Ответ Data safety в Play «поисковые запросы не собираются» держится на том,
что их действительно нигде нет, включая логи uvicorn. До 24 августа 2026 лог
писал `GET /v1/places/search?q=Mosc…` вместе с адресом клиента — фильтр
`_PlacesQueryRedactor` стирает набранное, оставляя факт запроса.
"""

import logging

from alma.api.app import _PlacesQueryRedactor


def _record(path: str) -> logging.LogRecord:
    # Ровно та форма, которой пишет uvicorn.access: пять аргументов, путь третий.
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("89.26.184.70:0", "GET", path, "1.1", 200),
        exc_info=None,
    )


def test_search_query_is_erased() -> None:
    record = _record("/v1/places/search?q=Moscow&limit=8")
    assert _PlacesQueryRedactor().filter(record) is True
    assert "Moscow" not in record.getMessage()
    assert "/v1/places/search?…" in record.getMessage()


def test_other_paths_untouched() -> None:
    # Чужие строки фильтр не трогает: /health со своими аргументами и глава со
    # слагом в пути обязаны логироваться как были.
    for path in ("/health", "/v1/readings", "/v1/systems/natal"):
        record = _record(path)
        _PlacesQueryRedactor().filter(record)
        assert path in record.getMessage()


def test_foreign_record_shape_passes_through() -> None:
    # Запись не-uvicorn формата (другое число аргументов) проходит нетронутой:
    # сломать логирование хуже, чем один раз не заредактировать.
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname=__file__, lineno=0,
        msg="places/search?q=secret %s", args=("tail",), exc_info=None,
    )
    assert _PlacesQueryRedactor().filter(record) is True
    assert "secret" in record.getMessage()
