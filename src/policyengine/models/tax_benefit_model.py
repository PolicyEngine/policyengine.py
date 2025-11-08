from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from .variable import Variable
    from .parameter import Parameter


class TaxBenefitModel(BaseModel):
    id: str
    name: str
    description: str | None = None
