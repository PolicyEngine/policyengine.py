from .baseline_parameter_value_table import (
    BaselineParameterValueTable,
    baseline_parameter_value_table_link,
)
from .baseline_variable_table import (
    BaselineVariableTable,
    baseline_variable_table_link,
)
from .database import Database
from .dataset_table import DatasetTable, dataset_table_link
from .dynamic_table import DynamicTable, dynamic_table_link
from .link import TableLink

# Import all table classes and links
from .model_table import ModelTable, model_table_link
from .model_version_table import ModelVersionTable, model_version_table_link
from .parameter_table import ParameterTable, parameter_table_link
from .parameter_value_table import (
    ParameterValueTable,
    parameter_value_table_link,
)
from .policy_table import PolicyTable, policy_table_link
from .simulation_table import SimulationTable, simulation_table_link
from .versioned_dataset_table import (
    VersionedDatasetTable,
    versioned_dataset_table_link,
)
from .report_table import ReportTable, report_table_link
from .report_element_table import ReportElementTable, report_element_table_link
from .aggregate import AggregateTable, aggregate_table_link
from .aggregate_change import AggregateChangeTable, aggregate_change_table_link
from .user_table import UserTable, user_table_link
from .user_policy_table import UserPolicyTable, user_policy_table_link
from .user_dynamic_table import UserDynamicTable, user_dynamic_table_link
from .user_dataset_table import UserDatasetTable, user_dataset_table_link
from .user_simulation_table import UserSimulationTable, user_simulation_table_link
from .user_report_table import UserReportTable, user_report_table_link

__all__ = [
    "Database",
    "TableLink",
    # Tables
    "ModelTable",
    "ModelVersionTable",
    "DatasetTable",
    "VersionedDatasetTable",
    "PolicyTable",
    "DynamicTable",
    "ParameterTable",
    "ParameterValueTable",
    "BaselineParameterValueTable",
    "BaselineVariableTable",
    "SimulationTable",
    "ReportTable",
    "ReportElementTable",
    "AggregateTable",
    "AggregateChangeTable",
    "UserTable",
    "UserPolicyTable",
    "UserDynamicTable",
    "UserDatasetTable",
    "UserSimulationTable",
    "UserReportTable",
    # Links
    "model_table_link",
    "model_version_table_link",
    "dataset_table_link",
    "versioned_dataset_table_link",
    "policy_table_link",
    "dynamic_table_link",
    "parameter_table_link",
    "parameter_value_table_link",
    "baseline_parameter_value_table_link",
    "baseline_variable_table_link",
    "simulation_table_link",
    "report_table_link",
    "report_element_table_link",
    "aggregate_table_link",
    "aggregate_change_table_link",
    "user_table_link",
    "user_policy_table_link",
    "user_dynamic_table_link",
    "user_dataset_table_link",
    "user_simulation_table_link",
    "user_report_table_link",
]
