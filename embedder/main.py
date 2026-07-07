"""Main entry point for the embeder application."""

import asyncio
import signal
import sys

from loguru import logger

from app.internal.config import get_settings
from app.internal.logging_config import configure_logging
from app.services.kafka_consumer import KafkaConsumerService
from app.services.image_processor import ImageProcessorService


async def main() -> None:
    """Main async entry point."""
    settings = get_settings()
    configure_logging(settings)

    logger.info("Starting embeder application")

    # Initialize services
    kafka_consumer = KafkaConsumerService(settings)
    image_processor = ImageProcessorService(settings)

    # Handle shutdown signals gracefully
    shutdown_event = asyncio.Event()

    def signal_handler(sig: signal.Signals) -> None:
        logger.info("Received shutdown signal", signal=sig.name)
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        # Start services
        await kafka_consumer.start()
        await image_processor.start()

        logger.info("Waiting for messages from Kafka...")

        # Main processing loop
        processed = 0
        while not shutdown_event.is_set():
            # Fetch message (non-blocking, returns immediately)
            message = await kafka_consumer.fetch()

            if message:
                # Process the message - this will complete even if shutdown is requested
                logger.info(
                    "Processing message",
                    item_id=message.item_id,
                    database_id=message.database_id,
                    url=str(message.original_url),
                )
                try:
                    await image_processor.process(message)
                    processed += 1
                    logger.info(
                        "Message processed successfully",
                        item_id=message.item_id,
                        processed_count=processed,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to process message",
                        error=str(e),
                        item_id=message.item_id,
                    )
            else:
                # No message available, wait a bit before next poll
                # Use wait with timeout so we can check shutdown_event
                try:
                    await asyncio.wait_for(
                        shutdown_event.wait(),
                        timeout=0.1,
                    )
                except asyncio.TimeoutError:
                    pass  # Normal case - no shutdown, continue polling

        logger.info("Graceful shutdown complete", messages_processed=processed)

    except Exception as e:
        logger.error("Application error", error=str(e))
        raise
    finally:
        # Graceful shutdown
        logger.info("Shutting down services...")
        await kafka_consumer.stop()
        await image_processor.stop()
        logger.info("Shutdown complete")


def run() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    run()
