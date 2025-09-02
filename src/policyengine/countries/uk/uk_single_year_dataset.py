from typing import Any

from pydantic import BaseModel

from policyengine.utils.dataframe_storage import (
    deserialise_dataframe_dict,
    serialise_dataframe_dict,
)


class UKSingleYearDataset(BaseModel):
    person: Any
    benunit: Any
    household: Any
    year: int

    def __init__(self, serialised_bytes: bytes | None = None, **kwargs):
        if serialised_bytes is None:
            super().__init__(**kwargs)
        else:
            deserialised_data = deserialise_dataframe_dict(serialised_bytes)
            self.person = deserialised_data.get("person")
            self.benunit = deserialised_data.get("benunit")
            self.household = deserialised_data.get("household")
            self.year = deserialised_data.get("year")

    def serialise(self) -> bytes:
        return serialise_dataframe_dict(
            {
                "person": self.person,
                "benunit": self.benunit,
                "household": self.household,
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
        return UKSingleYearDataset(
            person=self.person.copy(),
            benunit=self.benunit.copy(),
            household=self.household.copy(),
        )
