"""Test that register_model_version properly cleans up old data."""
from policyengine.database import Database
from policyengine.models.policyengine_uk import (
    policyengine_uk_model,
    policyengine_uk_latest_version,
)


def test_register_model_version_cleans_up_old_data():
    """Test that calling register_model_version twice doesn't cause duplicates."""
    # Setup database
    db = Database(
        url="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )
    db.reset()

    # Register the model version once
    db.register_model_version(policyengine_uk_latest_version)

    # Get initial counts
    from policyengine.database.parameter_table import ParameterTable
    from policyengine.database.baseline_parameter_value_table import (
        BaselineParameterValueTable,
    )
    from policyengine.database.baseline_variable_table import (
        BaselineVariableTable,
    )
    from sqlmodel import select

    with db.session as session:
        initial_param_count = len(session.exec(
            select(ParameterTable).where(
                ParameterTable.model_id == policyengine_uk_model.id
            )
        ).all())

        initial_bpv_count = len(session.exec(
            select(BaselineParameterValueTable).where(
                BaselineParameterValueTable.model_id == policyengine_uk_model.id
            )
        ).all())

        initial_bv_count = len(session.exec(
            select(BaselineVariableTable).where(
                BaselineVariableTable.model_id == policyengine_uk_model.id
            )
        ).all())

    print(f"Initial counts - Parameters: {initial_param_count}, BPV: {initial_bpv_count}, BV: {initial_bv_count}")

    # Register the same model version again - should replace, not duplicate
    db.register_model_version(policyengine_uk_latest_version)

    # Get final counts - should be the same as initial
    with db.session as session:
        final_param_count = len(session.exec(
            select(ParameterTable).where(
                ParameterTable.model_id == policyengine_uk_model.id
            )
        ).all())

        final_bpv_count = len(session.exec(
            select(BaselineParameterValueTable).where(
                BaselineParameterValueTable.model_id == policyengine_uk_model.id
            )
        ).all())

        final_bv_count = len(session.exec(
            select(BaselineVariableTable).where(
                BaselineVariableTable.model_id == policyengine_uk_model.id
            )
        ).all())

    print(f"Final counts - Parameters: {final_param_count}, BPV: {final_bpv_count}, BV: {final_bv_count}")

    assert initial_param_count == final_param_count, \
        f"Parameter count changed from {initial_param_count} to {final_param_count}"

    assert initial_bpv_count == final_bpv_count, \
        f"Baseline parameter value count changed from {initial_bpv_count} to {final_bpv_count}"

    assert initial_bv_count == final_bv_count, \
        f"Baseline variable count changed from {initial_bv_count} to {final_bv_count}"

    print("✅ Test passed - no duplicates when registering model version twice")


if __name__ == "__main__":
    test_register_model_version_cleans_up_old_data()