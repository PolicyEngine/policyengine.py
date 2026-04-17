from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    pass


class TaxBenefitModel(BaseModel):
    id: str
    description: Optional[str] = None
