"""EventSource backed by an aiokafka consumer: one message at a time, offset committed after the handler.

With a dead-letter sink (core/deadletter.py), an unreadable message or a handler that fails on every try
is saved there and the consumer moves on; a database outage still stops it. Without a sink, any error
stops the consumer without committing, so the message is read again on the next run.
"""

import asyncio
from dataclasses import replace
from typing import Any

from aiokafka import AIOKafkaConsumer, TopicPartition

from adapters.warehouse.events import EnvelopeError, parse_message
from adapters.warehouse.kafka_config import KafkaSettings
from core.deadletter import DeadLetterSink, Sleep, handler_error_text, run_with_retries
from core.events import EventHandler, Position


class KafkaEventSource:
    def __init__(self, consumer: Any, dead_letters: DeadLetterSink | None = None, sleep: Sleep = asyncio.sleep):
        # Any object with start, stop, commit and async iteration (AIOKafkaConsumer, or a fake in tests).
        self._consumer = consumer
        self._dead_letters = dead_letters
        # The wait between handler tries; tests pass a fake that records it.
        self._sleep = sleep

    @classmethod
    def from_settings(
        cls, settings: KafkaSettings | None = None, dead_letters: DeadLetterSink | None = None
    ) -> "KafkaEventSource":
        settings = settings or KafkaSettings()
        return cls(AIOKafkaConsumer(*settings.topics, **settings.consumer_kwargs()), dead_letters=dead_letters)

    async def consume(self, handler: EventHandler) -> None:
        await self._consumer.start()
        try:
            async for message in self._consumer:
                position = Position(message.topic, message.partition, message.offset)
                try:
                    event = parse_message(message.value)
                except EnvelopeError as exc:
                    if self._dead_letters is None:
                        raise EnvelopeError(
                            f"{message.topic} partition {message.partition} offset {message.offset}: {exc}"
                        ) from None
                    await self._dead_letters.record(position, message.value, str(exc))
                else:
                    event = replace(event, position=position)
                    if self._dead_letters is None:
                        await handler(event)
                    else:
                        error = await run_with_retries(handler, event, self._sleep)
                        if error is not None:
                            await self._dead_letters.record(position, message.value, handler_error_text(error))
                # Kafka stores the next offset to read, so a restart resumes after this message.
                await self._consumer.commit({TopicPartition(message.topic, message.partition): message.offset + 1})
        finally:
            await self._consumer.stop()
