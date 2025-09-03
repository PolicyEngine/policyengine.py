from __future__ import annotations

from datetime import datetime

import pandas as pd

from policyengine.database import Database
from policyengine.models import (
    Dataset,
    Dynamics,
    OperationStatus,
    Parameter,
    ParameterValue,
    Policy,
    Simulation,
    DatasetType,
)
from policyengine.models.single_year_dataset import SingleYearDataset
from policyengine.models.user import User, UserPolicy
from uuid import uuid4


def _mk_db(tmp_path) -> Database:
    db_path = tmp_path / "pe_test.db"
    return Database(url=f"sqlite:///{db_path}")


def test_dataset_serialization_roundtrip(tmp_path):
    db = _mk_db(tmp_path)

    person = pd.DataFrame({"person_id": [1, 2], "age": [30, 40]})
    syd = SingleYearDataset(tables={"person": person}, year=2024)
    ds = Dataset(name="syd", data=syd, dataset_type=DatasetType.UK)

    row = db.add(ds)
    assert getattr(row, "id", None) is not None

    loaded = db.get(Dataset, row.id)  # type: ignore[arg-type]
    assert isinstance(loaded.data, SingleYearDataset)
    assert loaded.data.year == 2024
    pd.testing.assert_frame_equal(
        person.reset_index(drop=True),
        loaded.data.tables["person"].reset_index(drop=True),
    )


def test_simulation_with_result_dataset(tmp_path):
    db = _mk_db(tmp_path)

    # Input dataset
    household = pd.DataFrame({"household_id": [1], "household_weight": [1.0]})
    syd_in = SingleYearDataset(tables={"household": household}, year=2029)
    ds_in = Dataset(name="in", data=syd_in, dataset_type=DatasetType.UK)

    # Result dataset
    person = pd.DataFrame({"person_id": [1], "gov_tax": [123.0]})
    syd_out = SingleYearDataset(tables={"person": person}, year=2029)
    ds_out = Dataset(name="out", data=syd_out, dataset_type=DatasetType.UK)

    policy = Policy(name="p")
    dynamics = Dynamics(name="d")
    sim = Simulation(
        dataset=ds_in,
        policy=policy,
        dynamics=dynamics,
        country="uk",
        status=OperationStatus.PENDING,
    )
    sim.result = ds_out

    row = db.add(sim)
    assert getattr(row, "id", None) is not None

    loaded = db.get(Simulation, row.id)  # type: ignore[arg-type]
    assert isinstance(loaded.result, Dataset)
    assert isinstance(loaded.result.data, SingleYearDataset)
    assert "gov_tax" in loaded.result.data.tables.get("person", pd.DataFrame()).columns


def test_parameter_value_cascade(tmp_path):
    db = _mk_db(tmp_path)

    param = Parameter(name="threshold", data_type=int)
    policy = Policy(name="baseline")
    pv = ParameterValue(
        parameter=param,
        policy=policy,
        model_version="1.0",
        start_date=datetime(2024, 1, 1),
        value=100,
        country="uk",
    )

    row = db.add(pv)
    assert getattr(row, "id", None) is not None
    assert row.parameter_id is not None

    # Check hydration preserves fields
    loaded_list = db.list(ParameterValue)
    assert loaded_list and loaded_list[0].value == 100


def test_user_policy_association(tmp_path):
    db = _mk_db(tmp_path)

    uid = uuid4()
    user = User(id=uid, name="Alice", email="alice@example.com")
    db.add(user)

    pol = Policy(name="p1")
    link = UserPolicy(user=user, policy=pol, label="fav")

    row = db.add(link)
    assert getattr(row, "id", None) is not None
    assert row.user_id == uid
    assert row.policy_id is not None
