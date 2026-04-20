"""Core value objects: Dataset, Variable, Parameter, Policy, Simulation, Region.

Provenance (release manifests, TRACE TROs) lives in
:mod:`policyengine.provenance` and is intentionally not re-exported
here — importing a core value object should not pull in the
provenance layer.
"""

from .dataset import Dataset
from .dataset import YearData as YearData
from .dataset import map_to_entity as map_to_entity
from .dynamic import Dynamic as Dynamic
from .output import Output as Output
from .output import OutputCollection as OutputCollection
from .parameter import Parameter as Parameter
from .parameter_node import ParameterNode as ParameterNode
from .parameter_value import ParameterValue as ParameterValue
from .policy import Policy as Policy
from .region import Region as Region
from .region import RegionRegistry as RegionRegistry
from .region import RegionType as RegionType
from .scoping_strategy import RegionScopingStrategy as RegionScopingStrategy
from .scoping_strategy import RowFilterStrategy as RowFilterStrategy
from .scoping_strategy import ScopingStrategy as ScopingStrategy
from .scoping_strategy import (
    WeightReplacementStrategy as WeightReplacementStrategy,
)
from .simulation import Simulation as Simulation
from .tax_benefit_model import TaxBenefitModel as TaxBenefitModel
from .tax_benefit_model_version import (
    TaxBenefitModelVersion as TaxBenefitModelVersion,
)
from .variable import Variable as Variable

# Rebuild models to resolve forward references
Dataset.model_rebuild()
TaxBenefitModelVersion.model_rebuild()
Variable.model_rebuild()
Parameter.model_rebuild()
ParameterNode.model_rebuild()
ParameterValue.model_rebuild()
