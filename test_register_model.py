import pytest
from policyengine.database import Database
from policyengine.models.policyengine_uk import (
    policyengine_uk_model,
    policyengine_uk_latest_version,
)


def test_register_model_version_adds_all_parameters():
    """Test that register_model_version adds all parameters, not just one."""
    # Setup database
    db = Database(
        url="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )
    db.reset()

    # Register the model version
    db.register_model_version(policyengine_uk_latest_version)

    # Get the seed objects to check expected counts
    seed_objects = policyengine_uk_model.create_seed_objects(
        policyengine_uk_latest_version
    )
    expected_parameter_count = len(seed_objects.parameters)
    expected_baseline_param_value_count = len(
        seed_objects.baseline_parameter_values
    )
    expected_baseline_variable_count = len(seed_objects.baseline_variables)

    # Check that all parameters were added
    from policyengine.database.parameter_table import ParameterTable
    from policyengine.database.baseline_parameter_value_table import (
        BaselineParameterValueTable,
    )
    from policyengine.database.baseline_variable_table import (
        BaselineVariableTable,
    )
    from sqlmodel import select

    # Count parameters in database
    with db.session as session:
        actual_parameter_count = session.exec(
            select(ParameterTable).where(
                ParameterTable.model_id == policyengine_uk_model.id
            )
        ).all()

        actual_baseline_param_value_count = session.exec(
            select(BaselineParameterValueTable).where(
                BaselineParameterValueTable.model_version_id
                == policyengine_uk_latest_version.id
            )
        ).all()

        actual_baseline_variable_count = session.exec(
            select(BaselineVariableTable).where(
                BaselineVariableTable.model_version_id
                == policyengine_uk_latest_version.id
            )
        ).all()

    assert len(actual_parameter_count) == expected_parameter_count, (
        f"Expected {expected_parameter_count} parameters but only {len(actual_parameter_count)} were added"
    )

    assert (
        len(actual_baseline_param_value_count)
        == expected_baseline_param_value_count
    ), (
        f"Expected {expected_baseline_param_value_count} baseline parameter values but only {len(actual_baseline_param_value_count)} were added"
    )

    assert (
        len(actual_baseline_variable_count) == expected_baseline_variable_count
    ), (
        f"Expected {expected_baseline_variable_count} baseline variables but only {len(actual_baseline_variable_count)} were added"
    )


if __name__ == "__main__":
    test_register_model_version_adds_all_parameters()
