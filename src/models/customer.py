from sqlalchemy import CHAR, Column, Date, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import relationship
from models.base import Base


class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True)
    customer_key = Column(CHAR(36), nullable=False, unique=True)
    status_id = Column(Integer, ForeignKey("customer_status.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    document_number = Column(String(18), nullable=False, unique=True)
    birthdate = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    status = relationship("CustomerStatus")
    accounts = relationship("Account", back_populates="customer")
    status_events = relationship("CustomerStatusEvent", back_populates="customer", order_by="CustomerStatusEvent.event_datetime", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_customer_email_lower", text("lower(email)"), unique=True),
        Index("ix_customer_created_at_id", created_at.desc(), id.desc()),
    )
