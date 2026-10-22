from pydantic import BaseModel, Field


class Entity(BaseModel):
    """One entity of a country model, such as a person or a household.

    Records what a household builder needs to place its inputs: the key that
    ``Variable.entity`` names, the plural that groups a household's members of
    this entity, and whether it is the person entity. Entity labels,
    descriptions and roles are not recorded.
    """

    key: str = Field(description="Entity key, as named by Variable.entity")
    plural: str = Field(
        description="Plural key grouping a household's entities of this kind"
    )
    is_person: bool = Field(description="Whether this is the person entity")
