import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from adapters.warehouse.events import EnvelopeError, parse_message
from adapters.warehouse.kafka_config import WAREHOUSE_TOPICS, KafkaSettings
from adapters.warehouse.kafka_source import KafkaEventSource
from core.events import Event, EventSource

ROOT = Path(__file__).resolve().parent.parent
EVENT_ID = "0b6f9c1e-4a52-4c8e-9a51-2f6d1c3e7a10"


def envelope(**overrides) -> dict:
    body = {
        "event_id": EVENT_ID,
        "event_type": "wms.pick.completed",
        "occurred_at": "2026-11-21T10:15:00+00:00",
        "order_id": 42,
        "request_id": "req-test-1",
        "payload": {"items": [{"product_id": 7, "qty": 3}]},
    }
    body.update(overrides)
    return body


def encode(body) -> bytes:
    return json.dumps(body).encode()


@dataclass
class FakeMessage:
    value: bytes
    topic: str = "wms.pick.completed"
    partition: int = 0
    offset: int = 0


class FakeConsumer:
    """Stands in for AIOKafkaConsumer: no network, records every call."""

    def __init__(self, messages):
        self.messages = messages
        self.calls = []
        self.commits = []

    async def start(self):
        self.calls.append("start")

    async def stop(self):
        self.calls.append("stop")

    async def commit(self, offsets):
        self.commits.append({(tp.topic, tp.partition): offset for tp, offset in offsets.items()})

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for message in self.messages:
            yield message


def kafka_settings(**values) -> KafkaSettings:
    # _env_file=None keeps a developer's real .env out of the test.
    return KafkaSettings(_env_file=None, **values)


# AC-1: generic interface in core


def test_kafka_source_is_an_event_source():
    assert isinstance(KafkaEventSource(FakeConsumer([])), EventSource)


def test_core_events_has_no_warehouse_terms():
    text = (ROOT / "core" / "events.py").read_text(encoding="utf-8").lower()
    for term in ("kafka", "order", "wms", "stock", "warehouse"):
        assert term not in text, f"core/events.py mentions {term!r}"


# AC-2: envelope parsing


def test_parse_valid_envelope():
    event = parse_message(encode(envelope()))
    assert event == Event(
        event_id=EVENT_ID,
        type="wms.pick.completed",
        occurred_at=datetime(2026, 11, 21, 10, 15, tzinfo=UTC),
        entity="42",
        payload={"items": [{"product_id": 7, "qty": 3}]},
        metadata={"request_id": "req-test-1"},
    )


@pytest.mark.parametrize("field", ["event_id", "event_type", "occurred_at", "order_id", "request_id", "payload"])
def test_parse_missing_field(field):
    body = envelope()
    del body[field]
    with pytest.raises(EnvelopeError, match=field):
        parse_message(encode(body))


def test_parse_broken_json():
    with pytest.raises(EnvelopeError, match="JSON"):
        parse_message(b'{"event_id": ')


def test_parse_rejects_non_uuid_event_id():
    with pytest.raises(EnvelopeError, match="event_id"):
        parse_message(encode(envelope(event_id="not-a-uuid")))


def test_no_commit_on_parse_error():
    consumer = FakeConsumer([FakeMessage(encode(envelope()), offset=0), FakeMessage(b"garbage", offset=1)])
    seen = []

    async def handler(event):
        seen.append(event.event_id)

    with pytest.raises(EnvelopeError, match="offset 1"):
        asyncio.run(KafkaEventSource(consumer).consume(handler))
    assert seen == [EVENT_ID]
    assert consumer.commits == [{("wms.pick.completed", 0): 1}]
    assert consumer.calls == ["start", "stop"]


# AC-3: manual commit after the handler


def test_commit_after_handler():
    order = []
    consumer = FakeConsumer([FakeMessage(encode(envelope()), partition=2, offset=9)])

    async def handler(event):
        order.append(("handled", event.event_id))
        assert consumer.commits == [], "committed before the handler finished"

    asyncio.run(KafkaEventSource(consumer).consume(handler))
    assert order == [("handled", EVENT_ID)]
    # Kafka commits the next offset to read: 9 + 1.
    assert consumer.commits == [{("wms.pick.completed", 2): 10}]
    assert consumer.calls == ["start", "stop"]


def test_no_commit_when_handler_fails():
    consumer = FakeConsumer([FakeMessage(encode(envelope()))])

    async def handler(event):
        raise RuntimeError("database down")

    with pytest.raises(RuntimeError, match="database down"):
        asyncio.run(KafkaEventSource(consumer).consume(handler))
    assert consumer.commits == []
    assert consumer.calls == ["start", "stop"]


# AC-4: consumer settings from KAFKA_* environment variables


def test_consumer_config_sasl_ssl():
    settings = kafka_settings(
        bootstrap_servers="kafka-test.example.com:12345",
        security_protocol="SASL_SSL",
        sasl_username="wi-test",
        sasl_password="fake-password",
        ssl_cafile="ca-test.pem",
    )
    kwargs = settings.consumer_kwargs(ssl_context_factory=lambda cafile: f"context for {cafile}")
    assert kwargs == {
        "bootstrap_servers": "kafka-test.example.com:12345",
        "group_id": "warehouse-intelligence",
        "enable_auto_commit": False,
        "auto_offset_reset": "earliest",
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "PLAIN",
        "sasl_plain_username": "wi-test",
        "sasl_plain_password": "fake-password",
        "ssl_context": "context for ca-test.pem",
    }
    assert settings.topics == WAREHOUSE_TOPICS


def test_consumer_config_plaintext():
    kwargs = kafka_settings().consumer_kwargs()
    assert kwargs == {
        "bootstrap_servers": "localhost:9092",
        "group_id": "warehouse-intelligence",
        "enable_auto_commit": False,
        "auto_offset_reset": "earliest",
        "security_protocol": "PLAINTEXT",
    }


@pytest.mark.parametrize("missing", ["sasl_username", "sasl_password", "ssl_cafile"])
def test_sasl_ssl_requires_credentials(missing):
    values = {"security_protocol": "SASL_SSL", "sasl_username": "u", "sasl_password": "p", "ssl_cafile": "ca.pem"}
    values[missing] = ""
    with pytest.raises(ValueError, match=missing):
        kafka_settings(**values).consumer_kwargs(ssl_context_factory=lambda cafile: None)


def test_from_settings_builds_a_manual_commit_consumer():
    async def build():
        # Building the consumer opens no connection; start() would.
        return KafkaEventSource.from_settings(kafka_settings(group_id="wi-test"))

    consumer = asyncio.run(build())._consumer
    assert consumer.subscription() == set(WAREHOUSE_TOPICS)
    assert consumer._group_id == "wi-test"
    assert consumer._enable_auto_commit is False


def test_topics_are_the_section_4_topics():
    assert WAREHOUSE_TOPICS == ["wms.stock.reserved", "wms.stock.released", "wms.pick.completed", "wms.order.audit"]


def test_password_hidden_in_repr():
    assert "fake-password" not in repr(kafka_settings(sasl_password="fake-password"))


# AC-5: names listed in .env.example, no values


def test_env_example_lists_kafka_names():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    names = {
        "KAFKA_BOOTSTRAP_SERVERS",
        "KAFKA_GROUP_ID",
        "KAFKA_SECURITY_PROTOCOL",
        "KAFKA_SASL_MECHANISM",
        "KAFKA_SASL_USERNAME",
        "KAFKA_SASL_PASSWORD",
        "KAFKA_SSL_CAFILE",
    }
    for name in names:
        entry = [line for line in lines if line.lstrip("# ").startswith(name + "=")]
        assert entry, f"{name} missing from .env.example"
        assert entry[0].split("=", 1)[1].strip() == "", f"{name} has a value in .env.example"
