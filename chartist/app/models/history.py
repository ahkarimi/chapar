from sqlalchemy import Column, BigInteger, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.models.database import Base


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    method = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="success")  # e.g., "success", "failed"

    user = relationship("User", back_populates="analysis_history")


class PlanHistory(Base):
    __tablename__ = "plan_history"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    days_added = Column(Integer, nullable=False)
    plan_end_date_after = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="plan_history")


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String, nullable=False)  # "3_days", "1_day", "expired"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notification_logs")
