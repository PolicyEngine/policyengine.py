from policyengine_uk.tax_benefit_system import parameters, variables
from .database import Database
from .tables import (
    ParameterDB,
    ParameterValueDB,
    VariableDB,
    DatasetDB,
    PolicyDB,
    DynamicsDB,
)
from sqlmodel import Session
from policyengine_core.parameters import Parameter
from policyengine_core.tools.hugging_face import download_huggingface_dataset
from policyengine_uk.data import UKSingleYearDataset
from policyengine.utils.dataframe_storage import (
    deserialise_dataframe_dict,
    serialise_dataframe_dict,
)


def add_basic_policies_to_db(database: Database):
    # Add current law
    current_law = PolicyDB(name="current law")
    database.session.add(current_law)
    database.session.commit()

    # Add no behavioural response
    no_behavioural_response = DynamicsDB(name="static")
    database.session.add(no_behavioural_response)
    database.session.commit()


def add_parameters_to_db(database: Database):
    # First, parameters
    parameter_name_to_db_model = {}
    parameter_name_to_param_obj = {}
    for parameter in parameters.get_descendants():
        db_parameter = ParameterDB(
            name=parameter.name,
            description=parameter.description,
            data_type=type(parameter.values_list[0].value).__name__
            if isinstance(parameter, Parameter)
            else None,
            label=parameter.metadata.get("label"),
            unit=parameter.metadata.get("unit"),
        )
        parameter_name_to_db_model[parameter.name] = db_parameter
        parameter_name_to_param_obj[parameter.name] = parameter

    for parameter_name, db_parameter in parameter_name_to_db_model.items():
        database.session.add(db_parameter)
    database.session.commit()

    for parameter_name in parameter_name_to_param_obj:
        if parameter_name_to_param_obj[parameter_name].parent is not None:
            parameter_name_to_db_model[
                parameter_name
            ].parent_id = parameter_name_to_db_model[
                parameter_name_to_param_obj[parameter_name].parent.name
            ].id
            database.session.add(parameter_name_to_db_model[parameter_name])
    database.session.commit()

    current_law = database.current_law

    for parameter_name in parameter_name_to_param_obj:
        param = parameter_name_to_param_obj[parameter_name]
        if isinstance(param, Parameter):
            values = param.values_list[::-1]  # chronological order
            for i in range(len(values)):
                start_date = values[i].instant_str
                if i + 1 < len(values):
                    end_date = values[i + 1].instant_str
                else:
                    end_date = None

                # start date of 0000-01-01 not supported, recast to 2000-01-01
                if start_date < "2000-01-01":
                    start_date = "2000-01-01"

                db_value = ParameterValueDB(
                    parameter_id=parameter_name_to_db_model[parameter_name].id,
                    start_date=start_date,
                    end_date=end_date,
                    value=param.values_list[i].value,
                    policy_id=current_law.id,
                )
                database.session.add(db_value)
    database.session.commit()


def add_variables_to_db(database: Database):
    for variable in variables.values():
        db_variable = VariableDB(
            name=variable.name,
            description=variable.documentation,
            value_type=type(variable).__name__,
            label=variable.label,
            unit=variable.unit,
            entity=variable.entity.key,
            definition_period=variable.definition_period,
        )
        database.session.add(db_variable)
    database.session.commit()


def get_dataset_encoding(
    repo: str,
    repo_filename: str,
    version: str,
) -> str:
    filepath = download_huggingface_dataset(
        repo=repo, repo_filename=repo_filename, version=version
    )
    uk_dataset = UKSingleYearDataset(file_path=filepath)
    data = {
        "person": uk_dataset.person,
        "benunit": uk_dataset.benunit,
        "household": uk_dataset.household,
    }
    return serialise_dataframe_dict(data)


def add_datasets_to_db(database: Database):
    frs_2023_24_data = get_dataset_encoding(
        repo="policyengine/policyengine-uk-data",
        repo_filename="frs_2023_24.h5",
        version="1.17.9",
    )

    dataset = DatasetDB(
        name="frs_2023_24",
        data=frs_2023_24_data,
        year=2023,
    )

    database.session.add(dataset)
    database.session.commit()
