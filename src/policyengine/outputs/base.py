from pydantic import BaseModel


class Output(BaseModel):
    """Base class for all output templates."""

    def run(self):
        """Calculate and populate the output fields.

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement run()")
