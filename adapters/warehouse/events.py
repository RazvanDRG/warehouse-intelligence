"""System 1 event envelope (docs/architecture.md section 4) and its mapping to the core Event."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError

from core.events import Event


class EnvelopeError(ValueError):
    """A message that is not a valid System 1 envelope."""


class WarehouseEnvelope(BaseModel):
    # Unknown extra fields are ignored, so System 1 can add fields without breaking ingestion.
    model_config = ConfigDict(extra="ignore")

    event_id: UUID
    event_type: str
    occurred_at: datetime
    # Section 4 does not fix the type; both forms are accepted and the core sees text.
    order_id: StrictInt | str
    # Required key; null is accepted because section 4 does not say it is always set.
    request_id: str | None
    payload: dict[str, Any]


def parse_message(value: bytes) -> Event:
    try:
        raw = json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnvelopeError(f"message is not valid JSON: {exc}") from None
    try:
        envelope = WarehouseEnvelope.model_validate(raw)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'message'}: {e['msg']}" for e in exc.errors())
        raise EnvelopeError(f"invalid envelope: {problems}") from None
    return Event(
        event_id=str(envelope.event_id),
        type=envelope.event_type,
        occurred_at=envelope.occurred_at,
        entity=str(envelope.order_id),
        payload=envelope.payload,
        metadata={"request_id": envelope.request_id},
    )
