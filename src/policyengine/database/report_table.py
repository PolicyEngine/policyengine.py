import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel
from typing import TYPE_CHECKING

from policyengine.models.report import Report

from .link import TableLink

if TYPE_CHECKING:
    from .database import Database


class ReportTable(SQLModel, table=True, extend_existing=True):
    __tablename__ = "reports"

    id: str = Field(
        primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    label: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def convert_from_model(cls, model: Report, database: "Database" = None) -> "ReportTable":
        """Convert a Report instance to a ReportTable instance."""
        report_table = cls(
            id=model.id,
            label=model.label,
            created_at=model.created_at,
        )

        # Handle nested report elements if database is provided
        if database and model.elements:
            from .report_element_table import ReportElementTable
            from sqlmodel import select

            # First ensure the report table is saved to the database
            # This is necessary so the foreign key constraint is satisfied
            # Check if it already exists
            existing_report = database.session.exec(
                select(ReportTable).where(ReportTable.id == model.id)
            ).first()

            if not existing_report:
                database.session.add(report_table)
                database.session.flush()

            # Track which element IDs we want to keep
            desired_elem_ids = {elem.id for elem in model.elements}

            # Delete only elements linked to this report that are NOT in the new list
            existing_elems = database.session.exec(
                select(ReportElementTable).where(ReportElementTable.report_id == model.id)
            ).all()
            for elem in existing_elems:
                if elem.id not in desired_elem_ids:
                    database.session.delete(elem)

            # Now save/update the elements
            for i, element in enumerate(model.elements):
                # Check if this element already exists in the database
                existing_elem = database.session.exec(
                    select(ReportElementTable).where(ReportElementTable.id == element.id)
                ).first()

                if existing_elem:
                    # Update existing element
                    elem_table = ReportElementTable.convert_from_model(element, database)
                    existing_elem.report_id = model.id
                    existing_elem.position = i
                    existing_elem.label = elem_table.label
                    existing_elem.type = elem_table.type
                    existing_elem.markdown_content = elem_table.markdown_content
                    existing_elem.chart_type = elem_table.chart_type
                    existing_elem.x_axis_variable = elem_table.x_axis_variable
                    existing_elem.y_axis_variable = elem_table.y_axis_variable
                    existing_elem.baseline_simulation_id = elem_table.baseline_simulation_id
                    existing_elem.reform_simulation_id = elem_table.reform_simulation_id
                else:
                    # Create new element
                    elem_table = ReportElementTable.convert_from_model(element, database)
                    elem_table.report_id = model.id  # Link to this report
                    elem_table.position = i  # Maintain order
                    database.session.add(elem_table)
            database.session.flush()

        return report_table

    def convert_to_model(self, database: "Database" = None) -> Report:
        """Convert this ReportTable instance to a Report instance."""
        # Load nested report elements if database is provided
        elements = []
        if database:
            from .report_element_table import ReportElementTable
            from sqlmodel import select

            # Query for all elements linked to this report, ordered by position
            elem_tables = database.session.exec(
                select(ReportElementTable)
                .where(ReportElementTable.report_id == self.id)
                .order_by(ReportElementTable.position)
            ).all()

            # Convert each one to a model
            for elem_table in elem_tables:
                elements.append(elem_table.convert_to_model(database))

        return Report(
            id=self.id,
            label=self.label,
            created_at=self.created_at,
            elements=elements,
        )


report_table_link = TableLink(
    model_cls=Report,
    table_cls=ReportTable,
)
