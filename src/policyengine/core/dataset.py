from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from .tax_benefit_model import TaxBenefitModel
from .dataset_version import DatasetVersion


class Dataset(BaseModel):
    """Base class for datasets.

    The data field contains entity-level data as a BaseModel with DataFrame fields.

    Example:
        class YearData(BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True)
            person: pd.DataFrame
            household: pd.DataFrame

        class MyDataset(Dataset):
            data: YearData | None = None
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    dataset_version: DatasetVersion | None = None
    filepath: str
    is_output_dataset: bool = False
    tax_benefit_model: TaxBenefitModel = None
    year: int

    data: BaseModel | None = None
