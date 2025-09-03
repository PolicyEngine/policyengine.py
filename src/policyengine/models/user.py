from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class User(BaseModel):
    id: UUID
    name: str
    email: str


class UserPolicy(BaseModel):
    user: User
    policy: "Policy"
    label: Optional[str] = None
    description: Optional[str] = None


class UserSimulation(BaseModel):
    user: User
    simulation: "Simulation"
    label: Optional[str] = None
    description: Optional[str] = None


class UserReport(BaseModel):
    user: User
    report: "Report"
    label: Optional[str] = None
    description: Optional[str] = None


class UserReportElement(BaseModel):
    user: User
    report_element: "ReportElement"
    label: Optional[str] = None
    description: Optional[str] = None
