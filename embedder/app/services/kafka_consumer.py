"""Async Kafka consumer service."""

import json

from aiokafka import AIOKafkaConsumer
from loguru import logger

from app.internal.config import Settings
from app.models.message import UploadSuccessMessage


class KafkaConsumerService:
    """Async Kafka consumer with rebalancing support."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        """Start the Kafka consumer."""
        brokers = self.settings.kafka_brokers.split(",")

        self._consumer = AIOKafkaConsumer(
            self.settings.kafka_topic,
            bootstrap_servers=brokers,
            group_id=self.settings.kafka_consumer_group,
            enable_auto_commit=False,  # Manual commit for reliability
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        await self._consumer.start()
        logger.info(
            "Kafka consumer started",
            topic=self.settings.kafka_topic,
            group=self.settings.kafka_consumer_group,
        )

    async def stop(self) -> None:
        """Stop the Kafka consumer gracefully."""
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def fetch(self) -> UploadSuccessMessage | None:
        """
        Fetch one message from Kafka if available.

        Returns None if no message is available (non-blocking).
        Uses getmany() with timeout=0 for immediate return.
        """
        if not self._consumer:
            raise RuntimeError("Consumer not started")

        # getmany with timeout=0 returns immediately with available messages
        # This is rebalancing-friendly as it yields control
        records = await self._consumer.getmany(timeout_ms=0, max_records=1)

        # records is a dict: {TopicPartition: [records]}
        for tp, messages in records.items():
            if messages:
                msg = messages[0]
                logger.debug(
                    "Received message",
                    topic=msg.topic,
                    partition=msg.partition,
                    offset=msg.offset,
                )

                # Parse the message
                message = UploadSuccessMessage.model_validate(msg.value)

                # Commit the offset after successful parsing
                await self._consumer.commit()

                return message

        return None
