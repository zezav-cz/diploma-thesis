"""Test data factories for creating test instances."""

from datetime import datetime

from faker import Faker

from app.domains.models import FailedDownloadAttempt, FailedDownloadAttemptCreate, Image, ImageCreate

fake = Faker()


def create_image_data(**kwargs) -> ImageCreate:
    """Create ImageCreate instance with test data.

    Args:
        **kwargs: Override default values

    Returns:
        ImageCreate instance with test data
    """
    defaults = {
        "link": fake.url(),
        "store_collection": fake.word(),
        "filepath": f'{fake.file_path(depth=2, extension="jpg")}',
        "database_id": fake.lexify(text="????"),
        "item_id": fake.random_int(min=1, max=100000),
        "property_name": fake.word(),
        "image_number": fake.random_int(min=1, max=10),
        "hashsum": fake.hexify(text="^" * 64),
        "extension": "jpg",
        "width": fake.random_int(min=100, max=4000),
        "height": fake.random_int(min=100, max=4000),
    }
    defaults.update(kwargs)
    return ImageCreate(**defaults)


def create_image(**kwargs) -> Image:
    """Create complete Image instance with test data.

    Args:
        **kwargs: Override default values

    Returns:
        Image instance with test data
    """
    image_data = create_image_data()
    defaults = {
        "id": fake.random_int(min=1, max=10000),
        "link": image_data.link,
        "store_collection": image_data.store_collection,
        "filepath": image_data.filepath,
        "database_id": image_data.database_id,
        "item_id": image_data.item_id,
        "property_name": image_data.property_name,
        "image_number": image_data.image_number,
        "hashsum": image_data.hashsum,
        "extension": image_data.extension,
        "width": image_data.width,
        "height": image_data.height,
        "stored_at": datetime.now(),
    }
    defaults.update(kwargs)
    return Image(**defaults)


def create_failed_download_attempt_data(**kwargs) -> FailedDownloadAttemptCreate:
    """Create FailedDownloadAttemptCreate instance with test data.

    Args:
        **kwargs: Override default values

    Returns:
        FailedDownloadAttemptCreate instance with test data
    """
    defaults = {
        "image_id": fake.random_int(min=1, max=10000),
        "link": fake.url(),
        "database_id": fake.lexify(text="????"),
        "item_id": fake.random_int(min=1, max=100000),
        "property_name": fake.word(),
        "image_number": fake.random_int(min=1, max=10),
        "attempt_status": fake.random_element(elements=("timeout", "http_error", "network_error")),
        "error_message": fake.sentence(),
        "http_status": fake.random_element(elements=(404, 500, 503, None)),
    }
    defaults.update(kwargs)
    return FailedDownloadAttemptCreate(**defaults)


def create_failed_download_attempt(**kwargs) -> FailedDownloadAttempt:
    """Create complete FailedDownloadAttempt instance with test data.

    Args:
        **kwargs: Override default values

    Returns:
        FailedDownloadAttempt instance with test data
    """
    attempt_data = create_failed_download_attempt_data()
    defaults = {
        "id": fake.random_int(min=1, max=10000),
        "link": attempt_data.link,
        "database_id": attempt_data.database_id,
        "item_id": attempt_data.item_id,
        "property_name": attempt_data.property_name,
        "image_number": attempt_data.image_number,
        "attempt_status": attempt_data.attempt_status,
        "error_message": attempt_data.error_message,
        "http_status": attempt_data.http_status,
        "attempted_at": datetime.now(),
        "image_link": fake.url(),
        "tries": fake.random_int(min=1, max=5),
    }
    defaults.update(kwargs)
    return FailedDownloadAttempt(**defaults)
