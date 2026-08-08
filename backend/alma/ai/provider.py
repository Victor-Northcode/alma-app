"""Talking to a model, behind an interface thin enough to swap.

Provider-agnostic for two unrelated reasons. The obvious one is that model
pricing and quality move, and being locked to one vendor is a business risk.
The one that matters more day to day is testability: the entire generation
pipeline — prompt building, citation validation, regeneration, cost accounting
— is exercised in CI against a scripted provider that returns exactly what a
test says it should, including deliberately bad output. None of that needs a
network or a key.

Three tiers, because the free sample sits between two impossible options. It
has to be good enough that someone reads it and buys the chapter after it —
which the cheapest model is not — and it has to be written against a five-cent
per-user ceiling, which the most expensive model cannot be. So the cheap model
answers chat turns, the middle one writes the sample the business depends on,
and the strong one writes what people have paid for. All three are config
values rather than constants: the right answer moves every time a price list
does, and it should move without a code change.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..config import settings

log = logging.getLogger("alma.ai")


class ModelUnavailable(Exception):
    """No provider is configured, or the provider refused."""


class AnswerTruncated(ModelUnavailable):
    """The model ran into `max_tokens` and the reply is incomplete.

    A subclass rather than a flag on the message, because it is the one
    "unavailable" a caller can actually *do* something about: a writer with a
    retry loop can ask again for something shorter, where nothing can be done
    about an absent API key. It stays a `ModelUnavailable` so that every
    existing `except` clause keeps catching it and the behaviour of callers that
    do not care is unchanged.
    """


@dataclass(frozen=True, slots=True)
class Completion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str = "end_turn"

    def json(self) -> Any:
        """Parse the body as JSON.

        Structured output guarantees valid JSON in the first text block, so a
        failure here is a real contract violation and is raised rather than
        papered over.
        """
        return json.loads(self.text)


class Provider(Protocol):
    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        model: str,
        max_tokens: int = 4096,
        schema: dict | None = None,
    ) -> Completion: ...


class AnthropicProvider:
    """The real one.

    Structured output via `output_config.format` rather than an assistant
    prefill: prefills are rejected by current models, and a schema the server
    enforces is worth far more here than any amount of "reply with only JSON"
    in the prompt — every paragraph we print has to carry a machine-checkable
    list of the factors it came from.
    """

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings().anthropic_api_key
        if not key:
            raise ModelUnavailable(
                "ANTHROPIC_API_KEY is not set — put it in the environment; "
                "it is never written to a file in this repository"
            )
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=key)

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        model: str,
        max_tokens: int = 4096,
        schema: dict | None = None,
    ) -> Completion:
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        if schema is not None:
            request["output_config"] = {"format": {"type": "json_schema", "schema": schema}}

        try:
            # Streaming throughout: a long chapter can exceed the non-streaming
            # HTTP timeout, and the failure mode is a request that dies after
            # the tokens were already paid for.
            async with self._client.messages.stream(**request) as stream:
                message = await stream.get_final_message()
        except Exception as exc:  # provider errors are surfaced, not swallowed
            raise ModelUnavailable(str(exc)) from exc

        text = next(
            (block.text for block in message.content if getattr(block, "type", None) == "text"),
            "",
        )

        # A run that ends at the ceiling is a truncated run, and truncated JSON
        # is unparseable JSON. Until this check existed the failure travelled a
        # long way before being named: an empty string parsed to nothing, the
        # validator saw no paragraphs, and the caller reported that the model
        # had cited factors that do not exist. Every chat turn in the product
        # failed this way, and the message sent the reader to the validator.
        #
        # It is worth being loud about which half ran out. With thinking on,
        # a model can spend the entire allowance reasoning and emit no text at
        # all — that is a budget the caller set too low, not a model fault.
        if message.stop_reason == "max_tokens":
            spent = "the answer was cut off" if text else "nothing was written at all"
            raise AnswerTruncated(
                f"{model} reached max_tokens={max_tokens} and {spent}"
                " — raise the ceiling for this call rather than retrying it"
            )
        return Completion(
            text=text,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            stop_reason=message.stop_reason or "end_turn",
        )


@dataclass
class ScriptedProvider:
    """A provider that returns what a test told it to.

    Not a mock of the SDK — a stand-in for the *contract*. Tests hand it the
    payloads a model might produce, including invalid ones, and assert that
    the pipeline around it behaves. That is how the citation validator and the
    regeneration loop are tested without a key or a network.
    """

    #: What the model "returns", in order. An `Exception` in the list is raised
    #: on that turn instead, which is how a single failed attempt is scripted.
    responses: list[str | Exception] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)
    input_tokens: int = 1200
    output_tokens: int = 400
    fail_with: Exception | None = None

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        model: str,
        max_tokens: int = 4096,
        schema: dict | None = None,
    ) -> Completion:
        self.calls.append(
            {
                "system": system,
                "prompt": prompt,
                "model": model,
                "max_tokens": max_tokens,
                "schema": schema,
            }
        )
        if self.fail_with is not None:
            raise self.fail_with
        if not self.responses:
            raise ModelUnavailable("the scripted provider ran out of responses")

        body = self.responses.pop(0)
        # A scripted turn may be a *failure* as well as a payload. Without this
        # there was no way to test what the writer does when one attempt is
        # truncated and the next is fine — `fail_with` fails every call — and
        # that is precisely the case that took the free sample chapter down on
        # a real chart.
        if isinstance(body, Exception):
            raise body
        return Completion(
            text=body,
            model=model,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )


def default_provider() -> Provider:
    return AnthropicProvider()


def models() -> tuple[str, str, str]:
    """(cheap, mid, strong) — chat turns, the free sample, paid readings.

    One triple rather than three accessors so that every caller has to say
    out loud which tier it is spending on. A helper that returned "the model"
    is how a free chapter ends up being written on the strong one.
    """
    config = settings()
    return config.model_cheap, config.model_mid, config.model_strong
