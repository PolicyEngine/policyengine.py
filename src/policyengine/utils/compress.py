import pickle
from typing import Any

import blosc


def compress_data(data: Any) -> bytes:
    """Compress data using blosc after pickling."""
    pickled_data = pickle.dumps(data)
    compressed_data = blosc.compress(
        pickled_data, typesize=8, cname="zstd", clevel=9, shuffle=blosc.SHUFFLE
    )
    return compressed_data


def decompress_data(compressed_data: bytes) -> Any:
    """Decompress data using blosc and then unpickle."""
    decompressed_data = blosc.decompress(compressed_data)
    data = pickle.loads(decompressed_data)
    return data
