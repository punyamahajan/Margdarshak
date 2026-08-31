import uuid

from app.schemas.base import ORMModel


class PlacementDriveCreate(ORMModel):
    """Schema for the external sync boundary, not application write endpoints."""

    company_name: str
    poc_name: str
    poc_contact: str
    policy_doc_ref: str
    status: str


class PlacementDriveRead(PlacementDriveCreate):
    id: uuid.UUID
