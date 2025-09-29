import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ForwardRef

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .report_element import ReportElement


class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    created_at: datetime | None = None
    elements: list[ForwardRef("ReportElement")] = Field(default_factory=list)


# Import after class definition to avoid circular import
from .report_element import ReportElement
Report.model_rebuild()
