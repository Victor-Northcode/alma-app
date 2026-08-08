"""Billing — the price list, the processor seam, and the adapters behind it.

Import the seam, not an adapter. `provider.provider_for()` answers with
whichever processor the configuration names, and it imports that adapter lazily
— so **nothing is loaded here that names a processor**.

That is not tidiness. The whole point of the seam is that being refused by a
processor is an afternoon, and this file used to do `from . import catalogue,
paddle, provider`: deleting `paddle.py` would have broken every importer of the
billing package, which is most of the backend. The coupling had moved from the
router to the package header rather than disappearing. Ask for an adapter by
name and you get one; ask for the package and you get the vocabulary.
"""

from . import catalogue, provider
from .provider import (
    BillingProvider,
    BillingUnavailable,
    EventKind,
    Grant,
    InvalidSignature,
    NormalisedEvent,
    SessionHandle,
    provider_for,
)

# `entitlement_for` is deliberately *not* re-exported. There are three of them —
# `provider.entitlement_for` takes a `NormalisedEvent`, and each adapter has one
# taking its own `Event` — and one name at package level that resolves to
# whichever the reader assumed is how a caller passes the wrong object to a
# function that will happily return `None` for it. It was named in `__all__`
# anyway, so `from alma.billing import *` raised `AttributeError`: the comment
# and the list disagreed, and the list was the one being executed.

__all__ = [
    "BillingProvider",
    "BillingUnavailable",
    "EventKind",
    "Grant",
    "InvalidSignature",
    "NormalisedEvent",
    "SessionHandle",
    "catalogue",
    "provider",
    "provider_for",
]
