"""EventSource backed by an aiokafka consumer: one message at a time, offset committed after the handler."""

from typing import Any

from aiokafka import AIOKafkaConsumer, TopicPartition

from adapters.warehouse.events import EnvelopeError, parse_message
from adapters.warehouse.kafka_config import KafkaSettings
from core.events import EventHandler


class KafkaEventSource:
    def __init__(self, consumer: Any):
        # Any object with start, stop, commit and async iteration (AIOKafkaConsumer, or a fake in tests).
        self._consumer = consumer

    @classmethod
    def from_settings(cls, settings: KafkaSettings | None = None) -> "KafkaEventSource":
        settings = settings or KafkaSettings()
        return cls(AIOKafkaConsumer(*settings.topics, **settings.consumer_kwargs()))

    async def consume(self, handler: EventHandler) -> None:
        await self._consumer.start()
        try:
            async for message in self._consumer:
                try:
                    event = parse_message(message.value)
                except EnvelopeError as exc:
                    # No dead-letter yet (Week 2 Wed): stop without committing, so the message is not lost.
                    raise EnvelopeError(
                        f"{message.topic} partition {message.partition} offset {message.offset}: {exc}"
                    ) from None
                await handler(event)
                # Kafka stores the next offset to read, so a restart resumes after this message.
                await self._consumer.commit({TopicPartition(message.topic, message.partition): message.offset + 1})
        finally:
            await self._consumer.stop()
