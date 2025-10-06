from policyengine.database import Database
from policyengine.models.policyengine_uk import policyengine_uk_latest_version
from policyengine.utils.datasets import create_uk_dataset

# Load the dataset

uk_dataset = create_uk_dataset()

database = Database("postgresql://postgres:postgres@127.0.0.1:54322/postgres")

# These two lines are not usually needed, but you should use them the first time you set up a new database
database.reset()  # Drop and recreate all tables
database.register_model_version(
    policyengine_uk_latest_version
)  # Add in the model, model version, parameters and baseline parameter values and variables.
