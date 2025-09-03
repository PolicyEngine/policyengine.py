import io
import pickle
import zlib

import pandas as pd


def serialise_dataframe_dict(data: dict[str, pd.DataFrame]) -> bytes:
    """
    Serialize a dictionary of DataFrames to bytes.

    Args:
        data: Dictionary with string keys and DataFrame values

    Returns:
        Serialized str-bytes representation
    """
    buffer = io.BytesIO()
    # Use highest protocol for speed and size
    pickle.dump(data, buffer, protocol=pickle.HIGHEST_PROTOCOL)
    raw = buffer.getvalue()
    # Compress to speed up IO and reduce DB size
    return zlib.compress(raw, level=6)


def deserialise_dataframe_dict(data: bytes) -> dict[str, pd.DataFrame]:
    """
    Deserialize str bytes back to a dictionary of DataFrames.

    Args:
        data: String representation of the dictionary

    Returns:
        Dictionary with string keys and DataFrame values
    """
    # Try to decompress; if not compressed, fall back to raw
    try:
        raw = zlib.decompress(data)
    except Exception:
        raw = data
    buffer = io.BytesIO(raw)
    return pickle.load(buffer)
