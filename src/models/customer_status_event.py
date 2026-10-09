from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship
from models.base import Base


class CustomerStatusEvent(Base):
    __tablename__ = "customer_status_event"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("customer_status.id"), nullable=False)
    event_datetime = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    customer = relationship("Customer", back_populates="status_events", foreign_keys=[customer_id])
    status = relationship("CustomerStatus", foreign_keys=[status_id], lazy="selectin")
