import os
import threading
from mimetypes import guess_type
from pathlib import Path

import magic
from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from config import ASSETS_BASE_PATH
from logger.logger import log
from models.user import User
from utils.media_types import IMAGE_EXT_BY_MIME_TYPE

from .base_handler import FSHandler

# libmagic loads its database on construction (~few MB read from disk), so we
# share a single Magic instance across requests. The underlying magic_t handle
# is not thread-safe, so guard from_buffer with a lock. Endpoints that call
# this validator may execute in worker threads under sync routes.
_MIME_DETECTOR = magic.Magic(mime=True)
_MIME_DETECTOR_LOCK = threading.Lock()


def validate_image_upload(upload: UploadFile, *, label: str = "Image") -> str:
    """Validate that an uploaded file is one of the safe image types.

    Sniffs the leading bytes with libmagic and returns the trusted extension
    matching the detected MIME type. Raises HTTPException(400) if the file
    is not a recognized image, or if MIME sniffing fails.
    Leaves the file cursor at 0.
    """
    upload.file.seek(0)
    header = upload.file.read(4096)
    upload.file.seek(0)

    try:
        with _MIME_DETECTOR_LOCK:
            detected_mime = _MIME_DETECTOR.from_buffer(header)
    except magic.MagicException as exc:
        log.error(f"libmagic failed to sniff uploaded {label.lower()}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not determine {label.lower()} file type",
        ) from exc

    safe_extension = IMAGE_EXT_BY_MIME_TYPE.get(detected_mime)
    if not safe_extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{label} must be a PNG, JPEG, WebP, or GIF image "
                f"(detected {detected_mime or 'unknown type'})"
            ),
        )

    return safe_extension


def build_asset_file_response(
    resolved_path: Path, filename: str | None = None
) -> FileResponse:
    """Serve an asset file. Trusted image types render inline; everything else
    is an opaque attachment, so a user-controlled file (e.g. HTML uploaded as an
    avatar) can't execute as stored XSS."""
    download_name = filename or resolved_path.name
    guessed_type, _ = guess_type(download_name)
    if guessed_type in IMAGE_EXT_BY_MIME_TYPE:
        return FileResponse(
            path=str(resolved_path),
            filename=download_name,
            media_type=guessed_type,
            content_disposition_type="inline",
        )

    return FileResponse(
        path=str(resolved_path),
        filename=download_name,
        media_type="application/octet-stream",
        content_disposition_type="attachment",
    )


class FSAssetsHandler(FSHandler):
    def __init__(self) -> None:
        super().__init__(base_path=ASSETS_BASE_PATH)

    def user_folder_path(self, user: User):
        return os.path.join("users", user.fs_safe_folder_name)

    # /users/557365723a31/profile
    def build_avatar_path(self, user: User):
        return os.path.join(self.user_folder_path(user), "profile")
