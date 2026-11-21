"""Small, reusable guards for handling untrusted video uploads."""
from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, UploadFile


CHUNK_SIZE = 1024 * 1024


def has_supported_video_signature(header: bytes) -> bool:
    """Check common container signatures; extension and MIME alone are not trusted."""
    if len(header) < 8:
        return False
    # ISO Base Media File Format: MP4, MOV and M4V
    if header[4:8] == b"ftyp":
        return True
    # EBML container: WebM and Matroska
    return header.startswith(b"\x1a\x45\xdf\xa3")


async def save_video_upload(
    upload: UploadFile,
    destination: Path,
    max_size_bytes: int,
) -> int:
    """Stream an upload to disk with a hard byte limit and basic container validation."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    total = 0
    header = bytearray()

    try:
        with temporary.open("wb") as output:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Video exceeds the {max_size_bytes // (1024 * 1024)} MB upload limit.",
                    )
                if len(header) < 32:
                    header.extend(chunk[: 32 - len(header)])
                output.write(chunk)

        if total == 0:
            raise HTTPException(status_code=400, detail="The uploaded video is empty.")
        if not has_supported_video_signature(bytes(header)):
            raise HTTPException(
                status_code=415,
                detail="The file does not have a supported MP4, MOV, WebM, or Matroska container signature.",
            )

        os.replace(temporary, destination)
        return total
    except Exception:
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
