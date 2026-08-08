"""The calculation service — the only door to the engine.

Nothing above this package imports `alma.engine` directly. That is what makes
"the AI may only cite what the engine produced" enforceable rather than
aspirational: facts become citable in exactly one place.
"""

from .contract import (
    ENGINE_VERSION,
    SYSTEMS,
    BirthData,
    CalcResult,
    HouseSystem,
    build,
    cache_key,
    json_safe,
)
from .service import (
    AmbiguousBirthTime,
    TimeRequired,
    chart_for,
    compute,
    moment_for,
)

__all__ = [
    "ENGINE_VERSION",
    "SYSTEMS",
    "AmbiguousBirthTime",
    "BirthData",
    "CalcResult",
    "HouseSystem",
    "TimeRequired",
    "build",
    "cache_key",
    "chart_for",
    "compute",
    "json_safe",
    "moment_for",
]
