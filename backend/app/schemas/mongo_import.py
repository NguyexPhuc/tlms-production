"""
Schemas for MongoDB User Import
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MongoDBUser(BaseModel):
    """
    User schema from MongoDB checkin_service
    Only contains fields needed for TLMS system
    """
    user_id: str = Field(..., alias="userId", description="S4H User ID - used as s4h_user_id")
    email: str = Field(..., description="User email")
    first_name: Optional[str] = Field(None, alias="firstName", description="First name")
    last_name: Optional[str] = Field(None, alias="lastName", description="Last name")
    student_id: Optional[str] = Field(None, alias="studentId", description="Student ID")
    phone: Optional[str] = Field(None, description="Phone number")
    zalo_uid: Optional[str] = Field(None, alias="zaloUid", description="Zalo UID")
    roles: Optional[List[str]] = Field(None, description="User roles")
    created_at: Optional[datetime] = Field(None, description="Created timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated timestamp")

    class Config:
        populate_by_name = True


class ImportProgress(BaseModel):
    """Progress tracking for import operation"""
    total: int = Field(..., description="Total users in MongoDB")
    imported: int = Field(0, description="Number of users imported")
    skipped: int = Field(0, description="Number of users skipped (already exists)")
    errors: int = Field(0, description="Number of errors")
    is_complete: bool = Field(False, description="Whether import is complete")


class ImportResult(BaseModel):
    """Result of import operation"""
    success: bool = True
    message: str
    total_in_mongodb: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[str] = []
