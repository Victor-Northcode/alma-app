"""The writing layer — where calculated facts become a reading.

One rule governs everything in this package: nothing may be asserted that the
engine did not calculate. It is enforced structurally rather than by
instruction — every generated paragraph carries the factor strings it was read
from, and `validator` checks them against the CalcResult before anyone sees
the text.
"""

from . import chapters, conversation, cost, provider, validator, voice, writer
from .cost import BudgetExceeded, Ledger, Spend
from .provider import AnthropicProvider, Completion, ModelUnavailable, Provider, ScriptedProvider
from .validator import Paragraph, Verdict
from .writer import ReadingRefused, Written

__all__ = [
    "AnthropicProvider",
    "BudgetExceeded",
    "Completion",
    "Ledger",
    "ModelUnavailable",
    "Paragraph",
    "Provider",
    "ReadingRefused",
    "ScriptedProvider",
    "Spend",
    "Verdict",
    "Written",
    "chapters",
    "conversation",
    "cost",
    "provider",
    "validator",
    "voice",
    "writer",
]
