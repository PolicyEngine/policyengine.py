"""Tests for the data-only behavior input boundary."""

from typing import Optional

import pandas as pd
import pytest
from microdf import MicroDataFrame
from pydantic import ValidationError

import policyengine.core as core
from policyengine.core import BehaviorInputBinding, BehaviorInputs
from policyengine.core.behavior import _resolve_behavior_inputs
from policyengine.tax_benefit_models.be.datasets import BEYearData

BEHAVIOR_COLUMN = "microcosm_latent_claim_flag"


@pytest.fixture
def be_year_data() -> BEYearData:
    """Build Belgian year data entirely in memory, without source runtimes."""
    person = pd.DataFrame(
        {
            "person_id": [30, 10, 20],
            "person_household_id": [300, 100, 200],
            "person_weight": [1.0, 2.0, 3.0],
            BEHAVIOR_COLUMN: pd.Series(
                [True, pd.NA, False],
                dtype="boolean",
            ),
        }
    )
    household = pd.DataFrame(
        {
            "household_id": [100, 200, 300],
            "household_weight": [2.0, 3.0, 1.0],
        }
    )
    return BEYearData(
        person=MicroDataFrame(person, weights="person_weight"),
        household=MicroDataFrame(household, weights="household_weight"),
    )


def _binding(
    *,
    role: str = "observed_claim",
    entity: str = "person",
    column: str = BEHAVIOR_COLUMN,
) -> BehaviorInputBinding:
    return BehaviorInputBinding(role=role, entity=entity, column=column)


def _inputs(binding: Optional[BehaviorInputBinding] = None) -> BehaviorInputs:
    return BehaviorInputs(bindings=(_binding() if binding is None else binding,))


def _replace_person(
    year_data: BEYearData,
    person: pd.DataFrame,
) -> BEYearData:
    return BEYearData(
        person=MicroDataFrame(person, weights="person_weight"),
        household=year_data.household,
    )


def test_configuration_models_round_trip_through_json() -> None:
    inputs = BehaviorInputs(
        bindings=(
            _binding(),
            _binding(
                role="household_signal",
                entity="household",
                column="household_weight",
            ),
        )
    )

    restored = BehaviorInputs.model_validate_json(inputs.model_dump_json())

    assert restored == inputs
    assert isinstance(restored.bindings, tuple)
    assert restored.model_dump(mode="json") == {
        "bindings": [
            {
                "role": "observed_claim",
                "entity": "person",
                "column": BEHAVIOR_COLUMN,
            },
            {
                "role": "household_signal",
                "entity": "household",
                "column": "household_weight",
            },
        ]
    }


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            BehaviorInputBinding,
            {
                "role": "observed_claim",
                "entity": "person",
                "column": BEHAVIOR_COLUMN,
                "values": [True, False],
            },
        ),
        (
            BehaviorInputs,
            {
                "bindings": [],
                "adapter": object(),
            },
        ),
    ],
)
def test_configuration_models_reject_unknown_fields(model, payload) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model.model_validate(payload)


def test_configuration_models_are_frozen() -> None:
    binding = _binding()
    inputs = _inputs(binding)

    with pytest.raises(ValidationError, match="Instance is frozen"):
        binding.role = "changed"
    with pytest.raises(ValidationError, match="Instance is frozen"):
        inputs.bindings = ()


def test_behavior_input_roles_must_be_unique() -> None:
    with pytest.raises(ValidationError, match="duplicate.*observed_claim"):
        BehaviorInputs(
            bindings=(
                _binding(),
                _binding(column="another_population_column"),
            )
        )


def test_core_exports_only_behavior_configuration_models() -> None:
    assert core.BehaviorInputBinding is BehaviorInputBinding
    assert core.BehaviorInputs is BehaviorInputs
    assert not hasattr(core, "ResolvedBehaviorInputs")
    assert not hasattr(core, "resolve_behavior_inputs")


def test_resolution_requires_loaded_year_data() -> None:
    with pytest.raises(ValueError, match="loaded YearData"):
        _resolve_behavior_inputs(_inputs(), None)


def test_resolution_rejects_missing_entity(be_year_data: BEYearData) -> None:
    binding = _binding(entity="benefit_unit")

    with pytest.raises(ValueError, match="missing entity 'benefit_unit'"):
        _resolve_behavior_inputs(_inputs(binding), be_year_data)


def test_resolution_rejects_missing_behavior_column(
    be_year_data: BEYearData,
) -> None:
    binding = _binding(column="missing_population_flag")

    with pytest.raises(ValueError, match="missing column 'missing_population_flag'"):
        _resolve_behavior_inputs(_inputs(binding), be_year_data)


def test_resolution_requires_entity_id_column(be_year_data: BEYearData) -> None:
    person = pd.DataFrame(be_year_data.person).drop(columns="person_id")
    year_data = _replace_person(be_year_data, person)

    with pytest.raises(ValueError, match="required ID column 'person_id'"):
        _resolve_behavior_inputs(_inputs(), year_data)


def test_resolution_rejects_null_entity_ids(be_year_data: BEYearData) -> None:
    person = pd.DataFrame(be_year_data.person).copy()
    person.loc[1, "person_id"] = pd.NA
    year_data = _replace_person(be_year_data, person)

    with pytest.raises(ValueError, match="null.*'person_id'"):
        _resolve_behavior_inputs(_inputs(), year_data)


def test_resolution_rejects_duplicate_entity_ids(be_year_data: BEYearData) -> None:
    person = pd.DataFrame(be_year_data.person).copy()
    person.loc[1, "person_id"] = person.loc[0, "person_id"]
    year_data = _replace_person(be_year_data, person)

    with pytest.raises(ValueError, match="unique.*'person_id'.*30"):
        _resolve_behavior_inputs(_inputs(), year_data)


def test_resolution_is_id_keyed_when_source_rows_are_reordered(
    be_year_data: BEYearData,
) -> None:
    person = pd.DataFrame(be_year_data.person).iloc[[2, 0, 1]].reset_index(drop=True)
    reordered = _replace_person(be_year_data, person)

    original_values = _resolve_behavior_inputs(_inputs(), be_year_data)[
        "observed_claim"
    ]
    reordered_values = _resolve_behavior_inputs(_inputs(), reordered)["observed_claim"]

    assert original_values.index.name == "person_id"
    assert original_values.index.tolist() == [30, 10, 20]
    assert reordered_values.index.tolist() == [20, 30, 10]
    pd.testing.assert_series_equal(
        original_values.sort_index(),
        reordered_values.sort_index(),
    )


def test_resolution_keeps_each_role_on_its_declared_entity(
    be_year_data: BEYearData,
) -> None:
    inputs = BehaviorInputs(
        bindings=(
            _binding(),
            _binding(
                role="household_signal",
                entity="household",
                column="household_weight",
            ),
        )
    )

    resolved = _resolve_behavior_inputs(inputs, be_year_data)

    assert resolved["observed_claim"].index.name == "person_id"
    assert resolved["observed_claim"].index.tolist() == [30, 10, 20]
    assert resolved["household_signal"].index.name == "household_id"
    assert resolved["household_signal"].index.tolist() == [100, 200, 300]


def test_resolution_preserves_nullable_values_without_boolean_coercion(
    be_year_data: BEYearData,
) -> None:
    values = _resolve_behavior_inputs(_inputs(), be_year_data)["observed_claim"]

    assert values.dtype == pd.BooleanDtype()
    assert values.loc[30] == True  # noqa: E712
    assert pd.isna(values.loc[10])
    assert values.loc[20] == False  # noqa: E712


def test_resolution_accepts_column_absent_from_legal_registry(
    be_year_data: BEYearData,
) -> None:
    values = _resolve_behavior_inputs(_inputs(), be_year_data)["observed_claim"]

    assert values.name == BEHAVIOR_COLUMN
    assert values.index.tolist() == [30, 10, 20]


def test_resolution_copies_values_without_mutating_or_aliasing_source(
    be_year_data: BEYearData,
) -> None:
    source_before = pd.DataFrame(be_year_data.person).copy(deep=True)

    values = _resolve_behavior_inputs(_inputs(), be_year_data)["observed_claim"]

    pd.testing.assert_frame_equal(pd.DataFrame(be_year_data.person), source_before)
    values.loc[30] = False
    assert be_year_data.person.loc[0, BEHAVIOR_COLUMN] == True  # noqa: E712
    be_year_data.person[BEHAVIOR_COLUMN] = pd.Series(
        [pd.NA, pd.NA, pd.NA],
        dtype="boolean",
    )
    assert values.loc[30] == False  # noqa: E712
