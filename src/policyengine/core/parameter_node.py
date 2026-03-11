from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .tax_benefit_model_version import TaxBenefitModelVersion


class ParameterNode(BaseModel):
    """Represents a folder/category node in the parameter hierarchy.

    Parameter nodes are intermediate nodes in the parameter tree (e.g., "gov",
    "gov.hmrc", "gov.hmrc.income_tax"). They provide structure and human-readable
    labels for navigating the parameter tree, but don't have values themselves.

    Unlike Parameter objects (which are leaf nodes with actual values),
    ParameterNode objects are purely organizational.
    """

    model_config = {"arbitrary_types_allowed": True}

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(description="Full path of the node (e.g., 'gov.hmrc')")
    label: str | None = Field(
        default=None, description="Human-readable label (e.g., 'HMRC')"
    )
    description: str | None = Field(default=None, description="Node description")
    tax_benefit_model_version: "TaxBenefitModelVersion"
