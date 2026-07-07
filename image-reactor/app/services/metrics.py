"""Prometheus metrics service for tracking application metrics."""

from prometheus_client import Counter

PREFIX = "image_reactor_"

# Counter metrics (always increasing)
images_stored = Counter(
    PREFIX + "images_stored",
    "Number of stored images",
    labelnames=["database_id", "collection"],
)

failed_attempts = Counter(
    PREFIX + "failed_attempts",
    "Number of failed download attempts",
    labelnames=["database_id", "attempt_status"],
)


def track_image_stored(database_id: str, collection: str) -> None:
    """Track a stored image.

    Args:
        database_id: The database ID associated with the image
        collection: The collection name where the image is stored
    """
    images_stored.labels(database_id=database_id, collection=collection).inc()


def track_failed_attempt(database_id: str, attempt_status: str) -> None:
    """Track a failed download attempt.

    Args:
        database_id: The database ID associated with the attempt
        attempt_status: The status of the attempt
    """
    failed_attempts.labels(database_id=database_id, attempt_status=attempt_status).inc()
