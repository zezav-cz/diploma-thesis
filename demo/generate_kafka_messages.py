#!/usr/bin/env -S uv run --no-project

# /// script
# requires-python = ">=3.11"
# dependencies = [
#  "confluent-kafka",
#  "faker",
# ]
# ///

import argparse
import asyncio
import json
import random
import signal
import string
from datetime import datetime
from confluent_kafka import Producer
from faker import Faker

# ==========================================
# CONFIGURATION
# ==========================================
KAFKA_BOOTSTRAP_SERVERS = "kafka-cluster-kafka-bootstrap.kafka.svc:9092"
KAFKA_TOPIC = "downloader"

# Global flag for graceful shutdown
shutdown_event = None


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM - force immediate shutdown"""
    print("\n\n⚠️  Shutdown requested (Ctrl+C detected)...")
    print("🛑 Stopping immediately...")
    if shutdown_event:
        shutdown_event.set()
    raise KeyboardInterrupt()


def create_image_job(
    fake: Faker, malformed_url_rate: float = 0.0, flannel_yaml_rate: float = 0.0
) -> dict:
    """Create a single ImageJob message

    Args:
        fake: Faker instance for generating fake data
        malformed_url_rate: Probability (0.0-1.0) of generating malformed picsum URLs
        flannel_yaml_rate: Probability (0.0-1.0) of generating flannel YAML download URLs
    """
    # Random image dimensions
    width = random.choice([200, 400, 600, 800, 1000, 1200])
    height = random.choice([200, 400, 600, 800, 1000, 1200])

    # Generate database_id under 64 chars
    customers = [
        "alpha",
        "beta",
        "gamma",
        "delta",
        "epsilon",
        "alpha",
        "beta",
        "gamma",
        "beta",
        "gamma",
        "beta",
        "beta",
        "beta",
    ]
    database_id = f"db_{random.choice(customers)}"

    # Always include image_number as an integer
    image_number = random.randint(1, 10)

    # Determine which URL to use based on independent random probabilities
    # Check malformed URL first
    if random.random() < malformed_url_rate:
        # Malformed picsum URL with random 16-char text
        random_text = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )
        image_url = f"https://picsum.photos/{random_text}"
    # Check flannel YAML second (independent of first check)
    elif random.random() < flannel_yaml_rate:
        # Flannel YAML download
        image_url = "https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml"
    else:
        # Normal image URL
        image_url = f"https://picsum.photos/{width}/{height}"

    return {
        "image_url": image_url,
        "database_id": database_id,
        "item_id": random.randint(1, 1000000),
        "property_name": random.choice(
            [
                "avatar",
                "cover_image",
                "thumbnail",
                "photo",
                "banner",
                "logo",
                "profile_pic",
                "gallery_image",
            ]
        ),
        "image_number": image_number,
    }


def delivery_report(err, msg):
    """Callback for message delivery reports"""
    if err is not None:
        print(f"❌ Message delivery failed: {err}")
    else:
        print(
            f"✅ Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}"
        )


async def generate_messages(
    num_messages: int,
    interval: float,
    num_partitions: int | None,
    duration: float | None,
    malformed_url_rate: float = 0.0,
    flannel_yaml_rate: float = 0.0,
    verbose: bool = True,
):
    """Generate and send Kafka messages using global configuration"""
    global shutdown_event

    # Create event for this async context
    shutdown_event = asyncio.Event()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Configure Kafka producer
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "client.id": "image-job-generator",
    }

    producer = Producer(conf)
    fake = Faker()

    # Calculate timing
    if duration is not None and duration > 0:
        # Calculate delay between messages to spread them over the duration
        delay_between_messages = duration / num_messages if num_messages > 1 else 0
        print(f"🚀 Starting message generation...")
        print(f"📊 Target: {num_messages} messages over {duration} seconds")
        print(f"⏱️  Delay between messages: {delay_between_messages:.4f} seconds")
        print(f"📈 Target rate: {num_messages / duration:.2f} messages/second")
    else:
        delay_between_messages = 0
        print(f"🚀 Starting message generation...")
        print(f"📊 Target: {num_messages} messages (as fast as possible)")

    print(f"🎯 Topic: {KAFKA_TOPIC}")
    if num_partitions:
        print(
            f"⚖️  Load balancing: Random distribution across {num_partitions} partitions"
        )
    else:
        print(f"⚖️  Load balancing: Kafka default (hash-based)")
    print(f"🔌 Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")
    if malformed_url_rate > 0:
        print(f"⚠️  Malformed URL rate: {malformed_url_rate * 100:.1f}%")
    if flannel_yaml_rate > 0:
        print(f"⚠️  Flannel YAML rate: {flannel_yaml_rate * 100:.1f}%")
    print(f"💡 Press Ctrl+C to stop immediately")
    print("-" * 60)

    loop = asyncio.get_event_loop()
    start_time = loop.time()
    messages_sent = 0
    was_interrupted = False
    partition_counts = {}

    try:
        for i in range(num_messages):
            # Check if shutdown was requested
            if shutdown_event.is_set():
                was_interrupted = True
                break

            message_start_time = loop.time()

            try:
                # Create message
                image_job = create_image_job(
                    fake, malformed_url_rate, flannel_yaml_rate
                )
                message = json.dumps(image_job)

                # Determine partition for load balancing
                partition = None
                if num_partitions:
                    # Random partition selection for uneven distribution
                    partition = random.randint(0, num_partitions - 1)
                    partition_counts[partition] = partition_counts.get(partition, 0) + 1

                # Send to Kafka
                producer.produce(
                    KAFKA_TOPIC,
                    value=message.encode("utf-8"),
                    partition=partition,  # None means Kafka will use default partitioner
                    callback=delivery_report if verbose else None,
                )

                # Trigger delivery callbacks
                producer.poll(0)

                messages_sent = i + 1

                if not verbose and messages_sent % 10 == 0:
                    elapsed = loop.time() - start_time
                    current_rate = messages_sent / elapsed if elapsed > 0 else 0
                    print(
                        f"📤 Sent {messages_sent}/{num_messages} messages (rate: {current_rate:.2f} msg/s)"
                    )

                # Calculate sleep time to maintain target rate
                if delay_between_messages > 0:
                    message_elapsed = loop.time() - message_start_time
                    sleep_time = max(0, delay_between_messages - message_elapsed)
                    if sleep_time > 0:
                        try:
                            await asyncio.wait_for(
                                shutdown_event.wait(), timeout=sleep_time
                            )
                            was_interrupted = True
                            break
                        except asyncio.TimeoutError:
                            pass  # Normal timeout, continue
                else:
                    # Allow the event loop to process signals
                    await asyncio.sleep(0)

            except Exception as e:
                print(f"❌ Error sending message {i + 1}: {e}")

        # Wait for the specified interval after all messages are sent
        if interval > 0 and not shutdown_event.is_set():
            print(f"\n⏸️  Waiting {interval} seconds before flushing...")
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
                was_interrupted = True
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue to flush

    except KeyboardInterrupt:
        was_interrupted = True
        print("\n⚠️  Interrupted!")
    finally:
        # Flush remaining messages with timeout
        print("\n⏳ Flushing remaining messages (max 5 seconds)...")
        try:
            # Run flush in executor to make it interruptible
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: producer.flush(5)), timeout=6
            )
        except asyncio.TimeoutError:
            print("⚠️  Flush timeout - some messages may not be delivered")
        except KeyboardInterrupt:
            print("⚠️  Flush interrupted - some messages may not be delivered")

        elapsed_time = loop.time() - start_time
        print("-" * 60)

        if was_interrupted:
            print(f"⚠️  Stopped by user request")
        else:
            print(f"✨ Completed!")

        print(f"📊 Total messages sent: {messages_sent}")
        if num_partitions and partition_counts:
            print(f"📊 Distribution per partition:")
            for partition in sorted(partition_counts.keys()):
                count = partition_counts[partition]
                percentage = (count / messages_sent * 100) if messages_sent > 0 else 0
                print(
                    f"   • Partition {partition}: {count} messages ({percentage:.1f}%)"
                )
        print(f"⏱️  Total time: {elapsed_time:.2f} seconds")
        if elapsed_time > 0:
            print(
                f"📈 Average rate: {messages_sent / elapsed_time:.2f} messages/second"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Generate Kafka messages for ImageJob processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-n",
        "--messages",
        type=int,
        default=1,
        help="Number of messages to generate (default: 1)",
    )

    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=None,
        help="Time duration in seconds over which to spread the messages (default: send as fast as possible)",
    )

    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=0.0,
        help="Time to wait after uploading all messages before flushing (default: 0.0)",
    )

    parser.add_argument(
        "-p",
        "--partitions",
        type=int,
        default=6,
        help="Number of partitions to randomly distribute messages across. If not specified, uses Kafka default partitioner (default: 6)",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Reduce output verbosity (show progress every 10 messages)",
    )

    parser.add_argument(
        "-eu",
        "--malformed-url-rate",
        type=float,
        default=0.0,
        help="Probability (0.0-1.0) of generating malformed picsum URLs (default: 0.0)",
    )

    parser.add_argument(
        "-em",
        "--flannel-yaml-rate",
        type=float,
        default=0.0,
        help="Probability (0.0-1.0) of generating flannel YAML download URLs (default: 0.0)",
    )

    args = parser.parse_args()

    asyncio.run(
        generate_messages(
            num_messages=args.messages,
            interval=args.interval,
            num_partitions=args.partitions,
            duration=args.duration,
            verbose=not args.quiet,
            malformed_url_rate=args.malformed_url_rate,
            flannel_yaml_rate=args.flannel_yaml_rate,
        )
    )


if __name__ == "__main__":
    main()
