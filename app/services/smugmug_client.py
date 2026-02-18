"""HTTP client for SmugMug's internal JSON-RPC API.

See docs/smugmug-sync.md for full API documentation.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.smugmug.com/services/api/json/1.4.0/"

# Size codes in preference order (largest usable first).
_SIZE_PREFERENCE = ("XL", "L", "M", "S")


class SmugmugAPIError(Exception):
    """Raised when a SmugMug API call fails."""


class SmugmugClient:
    """Async client for SmugMug's internal organizer API.

    Authenticates via SMSESS session cookie.
    """

    def __init__(self, session_cookie: str, nick: str) -> None:
        self._nick = nick
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            cookies={"SMSESS": session_cookie},
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/144.0.0.0 Safari/537.36"
                ),
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "SmugmugClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # API methods
    # ------------------------------------------------------------------

    async def get_node_tree(self) -> list[dict[str, Any]]:
        """Fetch the full folder/album tree as a flat node list."""
        resp = await self._http.get(
            "",
            params={
                "method": "rpc.organizer.getnodesbypath",
                "paths": "/",
                "depth": 10,
                "childrenOnly": "true",
                "nick": self._nick,
                "pageSize": 500,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("stat") != "ok":
            raise SmugmugAPIError(
                f"getnodesbypath failed: {data.get('message', data.get('stat'))}"
            )
        nodes: list[dict[str, Any]] = data.get("nodes", [])
        logger.info("Fetched %d nodes for %s", len(nodes), self._nick)
        return nodes

    async def get_album_images(
        self, album_id: str, album_key: str
    ) -> tuple[int, list[dict[str, Any]]]:
        """Fetch all images in an album, handling pagination.

        Returns (total_count, images).
        """
        all_images: list[dict[str, Any]] = []
        start_index = 0

        while True:
            resp = await self._http.get(
                "",
                params={
                    "method": "rpc.organizer.getimages",
                    "albumId": album_id,
                    "albumKey": album_key,
                    "nick": self._nick,
                    "limit": 100,
                    "startIndex": start_index,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("stat") != "ok":
                raise SmugmugAPIError(
                    f"getimages failed for album {album_key}: "
                    f"{data.get('message', data.get('stat'))}"
                )

            images: list[dict[str, Any]] = data.get("images", [])
            all_images.extend(images)
            total_count: int = data.get("imageCount", 0)

            pagination = data.get("pagination", {})
            next_index = pagination.get("nextIndex")
            if next_index is None:
                break
            start_index = next_index

        logger.info("Fetched %d images for album %s", len(all_images), album_key)
        return total_count, all_images


def pick_best_image_url(sizes: dict[str, Any]) -> str | None:
    """Pick the URL of the largest usable, non-cold image size."""
    for code in _SIZE_PREFERENCE:
        size = sizes.get(code)
        if size and size.get("usable") and not size.get("cold"):
            url: str | None = size.get("url")
            if url:
                return url
    return None


def extract_filename(image: dict[str, Any]) -> str:
    """Extract the real filename from an image response."""
    components = image.get("Components", [])
    if components:
        name: str | None = components[0].get("FileName")
        if name:
            return name
    # Fallback: FileName + Format
    name_part = image.get("FileName", "unknown")
    fmt = image.get("Format", "jpg")
    return f"{name_part}.{fmt}"
