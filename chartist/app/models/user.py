from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from app.models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, unique=True, index=True)
    email = Column(String, unique=True, nullable=True)
    phone_number = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=True)
    telegram_username = Column(String, nullable=True)
    total_requests = Column(Integer, default=0)
    is_referred = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Plan fields (time-based subscription)
    plan_end_date = Column(DateTime(timezone=True), nullable=True)
    plan_status = Column(String, default="trial")  # "trial", "active", "expired"
    plan_updated_at = Column(DateTime(timezone=True), nullable=True)

    analysis_history = relationship("AnalysisHistory", back_populates="user")
    plan_history = relationship("PlanHistory", back_populates="user")
    notification_logs = relationship("NotificationLog", back_populates="user")

    @property
    def remaining_days(self) -> int:
        """Get remaining days of the plan."""
        from app.utils.plan_utils import get_remaining_days
        return get_remaining_days(self.plan_end_date)

    @property
    def remaining_time_human(self) -> str:
        """Get human-readable remaining time of the plan."""
        from app.utils.plan_utils import get_remaining_time_human
        return get_remaining_time_human(self.plan_end_date)

    @property
    def plan_end_date_human(self) -> str:
        """Get human-readable plan end date in Persian."""
        from app.utils.plan_utils import format_datetime_human
        return format_datetime_human(self.plan_end_date)
