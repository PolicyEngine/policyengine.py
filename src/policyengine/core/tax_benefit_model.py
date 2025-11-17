from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    pass


class TaxBenefitModel(BaseModel):
    id: str
    description: str | None = None
