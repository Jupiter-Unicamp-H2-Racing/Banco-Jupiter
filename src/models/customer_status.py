from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base


class CustomerStatus(Base):
    __tablename__ = "customer_status"

    PENDING_KYC = "pending_kyc"
    ACTIVE = "active"
    BLOCKED = "blocked"
    INACTIVE = "inactive"
    ALLOWED = (PENDING_KYC, ACTIVE, BLOCKED, INACTIVE)

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    customers = relationship("Customer", back_populates="status", lazy="selectin")
