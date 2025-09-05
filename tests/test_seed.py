import importlib
import math
import pytest

from policyengine.database import Database
from policyengine.models import Parameter, ParameterValue, Variable
from datetime import datetime


def _has_pkg(mod_path: str) -> bool:
    try:
        importlib.import_module(mod_path)
        return True
    except Exception:
        return False


@pytest.mark.parametrize(
    "country,mod",
    [
        ("uk", "policyengine.countries.uk.metadata"),
        ("us", "policyengine.countries.us.metadata"),
    ],
)
def test_seed_country(tmp_path, country, mod):
    if not _has_pkg(mod.split(":")[0]):
        pytest.skip(f"Missing package for {country}")

    db_path = tmp_path / f"seed_{country}.db"
    db = Database(url=f"sqlite:///{db_path}")
    db.reset()
    db.seed([country])

    # Basic sanity: variables and parameter values exist
    vars_ = db.list(Variable)
    pvals = db.list(ParameterValue)
    assert len(vars_) > 0
    assert len(pvals) > 0


def test_parameter_value_infinity_roundtrip(tmp_path):
    db_path = tmp_path / "inf.db"
    db = Database(url=f"sqlite:///{db_path}")

    p = Parameter(name="x", data_type=float, country="uk")
    # Add the parameter first
    db.add(p)
    
    pv = ParameterValue(
        parameter=p,
        model_version="v",
        start_date=datetime(2020, 1, 1),
        value=float("inf"),
        country="uk",
    )
    db.add(pv)

    out = db.list(ParameterValue)[0]
    assert math.isinf(out.value) and out.value > 0
