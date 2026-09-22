"""JSON transport for the NZ pilot's primitive entity-table values.

This is a serialization codec, not a policy evaluator or dataset writer.
Decimal values use explicit tags so JSON cannot turn exact money into floats.
"""

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from microdf import MicroDataFrame

TABLE_SCHEMA = "policyengine/nz-entity-table/1"


def _encode_cell(value: Any) -> Any:
    if value is pd.NA:
        return {"_type": "na"}
    if value is pd.NaT:
        return {"_type": "nat"}
    if isinstance(value, Decimal):
        return {"_type": "decimal", "value": str(value)}
    if isinstance(value, pd.Timestamp):
        return {"_type": "timestamp", "value": value.isoformat()}
    if isinstance(value, (datetime, date)):
        return {"_type": type(value).__name__, "value": value.isoformat()}
    if isinstance(value, np.generic):
        return _encode_cell(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return {"_type": "float", "value": str(value)}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise ValueError(f"Unsupported NZ entity-table JSON value: {type(value).__name__}.")


def _decode_cell(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    kind = value.get("_type")
    if kind == "na":
        return pd.NA
    if kind == "nat":
        return pd.NaT
    decoders = {
        "decimal": Decimal,
        "timestamp": pd.Timestamp,
        "datetime": datetime.fromisoformat,
        "date": date.fromisoformat,
        "float": float,
    }
    if kind not in decoders:
        raise ValueError(f"Unsupported NZ JSON scalar tag {kind!r}.")
    return decoders[kind](value["value"])


def _encode_dtype(dtype: Any) -> dict[str, Any]:
    if isinstance(dtype, pd.CategoricalDtype):
        return {
            "kind": "category",
            "categories": _encode_index(dtype.categories),
            "ordered": dtype.ordered,
        }
    if isinstance(dtype, pd.StringDtype):
        return {
            "kind": "string",
            "storage": dtype.storage,
            "na_value": _encode_cell(dtype.na_value),
        }
    return {"kind": "pandas", "name": str(dtype)}


def _decode_dtype(payload: dict[str, Any]) -> Any:
    if payload["kind"] == "category":
        return pd.CategoricalDtype(
            categories=_decode_index(payload["categories"]), ordered=payload["ordered"]
        )
    if payload["kind"] == "string":
        na_value = _decode_cell(payload.get("na_value", {"_type": "na"}))
        if na_value is pd.NA:
            # The omitted keyword keeps older pandas versions compatible.
            return pd.StringDtype(storage=payload["storage"])
        if not isinstance(na_value, float) or not math.isnan(na_value):
            raise ValueError("Invalid NZ JSON string missing-value descriptor.")
        try:
            return pd.StringDtype(storage=payload["storage"], na_value=na_value)
        except TypeError as exc:
            # pandas 2.2's pyarrow_numpy storage already has NaN semantics,
            # but its constructor does not accept the na_value keyword.
            legacy_dtype = pd.StringDtype(storage=payload["storage"])
            if _encode_cell(legacy_dtype.na_value) == _encode_cell(na_value):
                return legacy_dtype
            raise ValueError(
                "This pandas version cannot restore NaN-semantics string data."
            ) from exc
    if payload["kind"] != "pandas":
        raise ValueError("Unsupported NZ JSON dtype descriptor.")
    return pd.api.types.pandas_dtype(payload["name"])


def _encode_index(index: pd.Index) -> dict[str, Any]:
    if isinstance(index, pd.MultiIndex):
        return {
            "kind": "multi",
            "levels": [_encode_index(level) for level in index.levels],
            "codes": [code.tolist() for code in index.codes],
            "names": [_encode_cell(name) for name in index.names],
        }
    name = _encode_cell(index.name)
    if isinstance(index, pd.RangeIndex):
        return {
            "kind": "range",
            "start": index.start,
            "stop": index.stop,
            "step": index.step,
            "name": name,
        }
    return {
        "kind": "index",
        "values": [_encode_cell(value) for value in index],
        "dtype": _encode_dtype(index.dtype),
        "name": name,
    }


def _decode_index(payload: dict[str, Any]) -> pd.Index:
    if payload["kind"] == "multi":
        return pd.MultiIndex(
            levels=[_decode_index(level) for level in payload["levels"]],
            codes=payload["codes"],
            names=[_decode_cell(name) for name in payload["names"]],
            verify_integrity=True,
        )
    name = _decode_cell(payload["name"])
    if payload["kind"] == "range":
        return pd.RangeIndex(
            payload["start"], payload["stop"], payload["step"], name=name
        )
    if payload["kind"] != "index":
        raise ValueError("Unsupported NZ JSON index descriptor.")
    return pd.Index(
        [_decode_cell(value) for value in payload["values"]],
        dtype=_decode_dtype(payload["dtype"]),
        name=name,
    )


def encode_table(value: MicroDataFrame) -> dict[str, Any]:
    table = pd.DataFrame(value)
    if not table.columns.is_unique or not all(
        isinstance(name, str) for name in table.columns
    ):
        raise ValueError("NZ JSON entity tables need unique string column names.")
    return {
        "schema": TABLE_SCHEMA,
        "columns": list(table.columns),
        "columns_name": _encode_cell(table.columns.name),
        "dtypes": [_encode_dtype(dtype) for dtype in table.dtypes],
        "index": _encode_index(table.index),
        "data": [
            [_encode_cell(value) for value in row]
            for row in table.itertuples(index=False, name=None)
        ],
    }


def decode_table(payload: dict[str, Any], entity: str) -> MicroDataFrame:
    if payload.get("schema") != TABLE_SCHEMA:
        raise ValueError("Unsupported NZ entity-table JSON schema.")
    columns = payload["columns"]
    if (
        not all(isinstance(name, str) for name in columns)
        or len(set(columns)) != len(columns)
        or len(columns) != len(payload["dtypes"])
    ):
        raise ValueError("Invalid NZ entity-table JSON columns/dtypes.")
    table = pd.DataFrame(
        [[_decode_cell(value) for value in row] for row in payload["data"]],
        index=_decode_index(payload["index"]),
        columns=columns,
        # Avoid pandas inferring float for integer+None object columns before
        # the recorded dtype is restored: that can round integers above 2**53.
        dtype=object,
    ).astype(
        {
            name: _decode_dtype(dtype)
            for name, dtype in zip(columns, payload["dtypes"], strict=True)
        }
    )
    table.columns.name = _decode_cell(payload["columns_name"])
    weight = f"{entity}_weight"
    if weight not in table:
        raise ValueError(f"NZ JSON {entity} table must contain effective {weight}.")
    return MicroDataFrame(table, weights=weight)
