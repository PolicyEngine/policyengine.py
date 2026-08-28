"""File hashing utilities."""

import hashlib
from pathlib import Path
from typing import Union


def sha256_file(path: Union[str, Path]) -> str:
    """Return the SHA-256 digest of a file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
