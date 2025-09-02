import io
import pickle

import pandas as pd


def serialise_dataframe_dict(data: dict[str, pd.DataFrame]) -> str:
    """
    Serialize a dictionary of DataFrames to bytes.

    Args:
        data: Dictionary with string keys and DataFrame values

    Returns:
        Serialized str-bytes representation
    """
    buffer = io.BytesIO()
    pickle.dump(data, buffer)
    bytes_val = buffer.getvalue()
    # encode into sql-safe string
    return bytes_val


def deserialise_dataframe_dict(data: str) -> dict[str, pd.DataFrame]:
    """
    Deserialize str bytes back to a dictionary of DataFrames.

    Args:
        data: String representation of the dictionary

    Returns:
        Dictionary with string keys and DataFrame values
    """
    buffer = io.BytesIO(data)
    return pickle.load(buffer)
