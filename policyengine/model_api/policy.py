from pydantic import BaseModel
import json

class Policy(BaseModel):
    parameter_changes: dict

    def __hash__(self):
        return hash(json.dumps(self.parameter_changes))

current_law = Policy(parameter_changes={})