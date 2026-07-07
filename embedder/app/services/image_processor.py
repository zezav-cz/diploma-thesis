"""Image download and hash computation service."""

import hashlib
from pathlib import Path

import aiohttp
from loguru import logger

from app.internal.config import Settings
from app.models.message import UploadSuccessMessage


class ImageProcessorService:
    """Service for downloading images and computing hashes."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """Initialize the HTTP session."""
        timeout = aiohttp.ClientTimeout(total=self.settings.http_timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.info("Image processor started")

    async def stop(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            logger.info("Image processor stopped")

    async def download_image(self, url: str) -> bytes:
        """
        Download image from URL.

        Args:
            url: Image URL to download

        Returns:
            Image content as bytes
        """
        if not self._session:
            raise RuntimeError("Image processor not started")

        logger.debug("Downloading image", url=url)

        async with self._session.get(url) as response:
            response.raise_for_status()
            content = await response.read()

        logger.debug("Image downloaded", url=url, size=len(content))
        return content

    def compute_hash(self, data: bytes, algorithm: str = "sha256") -> str:
        """
        Compute hash of the given data.

        Args:
            data: Binary data to hash
            algorithm: Hash algorithm to use (default: sha256)

        Returns:
            Hex digest of the hash
        """
        hasher = hashlib.new(algorithm)
        hasher.update(data)
        return hasher.hexdigest()

    async def write_hash_to_file(
        self,
        hash_value: str,
        image_id: str | None = None,
        url: str | None = None,
    ) -> None:
        """
        Write hash to the output file.

        Args:
            hash_value: Computed hash value
            image_id: Optional image identifier
            url: Optional image URL
        """
        output_path = Path(self.settings.output_file)

        # Format the output line
        parts = []
        if image_id:
            parts.append(f"id={image_id}")
        if url:
            parts.append(f"url={url}")
        parts.append(f"hash={hash_value}")

        line = " ".join(parts) + "\n"

        # Append to file
        with output_path.open("a") as f:
            f.write(line)

        logger.info(
            "Hash written to file",
            file=str(output_path),
            hash=hash_value[:16] + "...",
        )

    async def process(self, message: UploadSuccessMessage) -> str:
        """
        Process an image message: download, hash, and write to file.

        Args:
            message: Upload success message containing image info

        Returns:
            Computed hash value
        """
        # Build download URL from storage_path by replacing seaweedfs:// with base address
        storage_path = message.storage_path
        if not storage_path.startswith("seaweedfs://"):
            logger.error(
                "Invalid storage path scheme, expected seaweedfs://",
                storage_path=storage_path,
                item_id=message.item_id,
            )
            raise ValueError(f"Invalid storage path scheme: {storage_path}")
        path = storage_path.removeprefix("seaweedfs://")
        url = f"{self.settings.seaweedfs_address.rstrip('/')}/{path}"

        # Download the image
        image_data = await self.download_image(url)

        # Compute hash
        hash_value = self.compute_hash(image_data)

        # Write to file
        await self.write_hash_to_file(
            hash_value=hash_value,
            image_id=str(message.item_id) if message.item_id else None,
            url=url,
        )

        return hash_value
