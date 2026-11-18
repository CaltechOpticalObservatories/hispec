"""Archive of fiber-end inspection images: PNG plus a JSON sidecar.

Each image is written under <root>/<UTC date>/<tag>_<UTC time>.png, with the
inspection metadata alongside it in a .json file of the same stem. An
annotated copy (fiber outline and defect boxes drawn on) can be written next
to it as <stem>_annotated.png.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _default_writer(path: str, image) -> bool:
    import cv2  # pylint: disable=import-outside-toplevel
    return bool(cv2.imwrite(path, image))


def safe_tag(tag: str) -> str:
    """A tag reduced to characters safe in a file name; 'image' when empty."""
    return _UNSAFE.sub("-", tag).strip("-.") or "image"


class ImageArchive:  # pylint: disable=too-few-public-methods
    """Write images and their metadata under a root directory."""

    def __init__(self, root: str | os.PathLike,
                 write_image: Optional[Callable[[str, Any], bool]] = None,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.root = Path(root).expanduser()
        self._write_image = write_image or _default_writer
        self._now = now

    def save(self, tag: str, image, metadata: Dict[str, Any],
             annotated=None) -> Path:
        """Write image (and annotated, if given) and its sidecar; return the PNG path."""
        stamp = self._now()
        directory = self.root / stamp.strftime("%Y-%m-%d")
        directory.mkdir(parents=True, exist_ok=True)
        stem = f"{safe_tag(tag)}_{stamp.strftime('%Y%m%dT%H%M%S_%fZ')}"
        path = directory / f"{stem}.png"
        if not self._write_image(str(path), image):
            raise OSError(f"could not write image to {path}")
        record = {"tag": tag, "time": stamp.isoformat(), "image": str(path), **metadata}
        if annotated is not None:
            annotated_path = directory / f"{stem}_annotated.png"
            if self._write_image(str(annotated_path), annotated):
                record["annotated"] = str(annotated_path)
        sidecar = path.with_suffix(".json")
        sidecar.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
        return path
