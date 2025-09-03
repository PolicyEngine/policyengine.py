from typing import Any

from pydantic import BaseModel

from policyengine.utils.dataframe_storage import (
    deserialise_dataframe_dict,
    serialise_dataframe_dict,
)


class SingleYearDataset(BaseModel):
    tables: dict[str, Any]
    year: int

    def __init__(self, serialised_bytes: bytes | None = None, **kwargs):
        if serialised_bytes is not None:
            deserialised_data = deserialise_dataframe_dict(serialised_bytes)
            for key, table in deserialised_data.items():
                kwargs[key] = table

        super().__init__(**kwargs)

    def serialise(self) -> bytes:
        return serialise_dataframe_dict(
            {
                "tables": self.tables,
                "year": self.year,
            }
        )

    def deserialise(self, serialised_bytes: bytes):
        deserialised_data = deserialise_dataframe_dict(serialised_bytes)
        self.person = deserialised_data.get("person")
        self.benunit = deserialised_data.get("benunit")
        self.household = deserialised_data.get("household")
        self.year = deserialised_data.get("year")

    def copy(self):
        return SingleYearDataset(
            tables={key: table.copy() for key, table in self.tables.items()},
            year=self.year,
        )
