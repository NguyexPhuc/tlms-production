"""
Profile Evidence Models for TLMS
- Task evidence (links, descriptions, proofs)
- Profile achievements and rewards tracking
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.core.database import Base


class EvidenceStatus(str, Enum):
    """Evidence verification status"""
    PENDING = "pending"        # Chờ xác nhận
    VERIFIED = "verified"      # Đã xác nhận
    REJECTED = "rejected"      # Bị từ chối


class ProfileEvidence(Base):
    """
    Evidence/Proof for tasks added to user profile
    Users can add links, descriptions, and proofs for their completed tasks
    """
    __tablename__ = "profile_evidence"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)  # Optional link to task
    
    # Evidence details
    title = Column(String(255), nullable=False)  # Tiêu đề minh chứng
    description = Column(Text, nullable=True)    # Mô tả chi tiết
    evidence_links = Column(ARRAY(String(500)), default=[], nullable=False)  # Links to proof (Github, Drive, etc.)
    tags = Column(ARRAY(String(50)), default=[], nullable=False)  # e.g., ['web-dev', 'backend', 'python']
    
    # Verification
    status = Column(
        SQLEnum(EvidenceStatus, values_callable=lambda x: [e.value for e in x]),
        default=EvidenceStatus.PENDING,
        nullable=False
    )
    verified_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Display settings
    is_public = Column(Boolean, default=True, nullable=False)  # Show on public profile?
    is_featured = Column(Boolean, default=False, nullable=False)  # Featured achievement?
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="profile_evidence")
    task = relationship("Task", backref="profile_evidence")
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    
    def __repr__(self):
        return f"<ProfileEvidence {self.title} by user={self.user_id}>"
