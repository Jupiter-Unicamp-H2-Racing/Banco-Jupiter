from sqlalchemy import CHAR, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base


class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True)
    customer_key = Column(CHAR(36), nullable=False, unique=True)
    status_id = Column(Integer, ForeignKey("customer_status.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    document_number = Column(String(18), nullable=False, unique=True)
    birthdate = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    status = relationship("CustomerStatus", back_populates="customers", lazy="selectin")
    status_events = relationship("CustomerStatusEvent", back_populates="customer", order_by="CustomerStatusEvent.event_datetime", cascade="all, delete-orphan", lazy="selectin")
