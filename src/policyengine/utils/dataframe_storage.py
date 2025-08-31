
import pyarrow.parquet as pq
import pyarrow as pa
import io
import pandas as pd

def serialise_dataframe_dict(data: dict[str, pd.DataFrame]) -> bytes:
    # compress a dictionary of dataframes
    buffers = {}
    for key, df in data.items():
        buffer = io.BytesIO()
        table = pa.Table.from_pandas(df)
        pq.write_table(table, buffer, compression='snappy')
        buffers[key] = buffer.getvalue()
    return pa.serialize(buffers).to_buffer()

def deserialise_dataframe_dict(data: bytes) -> dict[str, pd.DataFrame]:
    buffers = pa.deserialize(data)
    return {key: pd.read_parquet(io.BytesIO(buffer)) for key, buffer in buffers.items()}