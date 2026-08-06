from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime


class MonthlyAnalysisReport(BaseModel):
    month: str  # e.g., "2024-04"
    total_analyses: int


class MonthlyPlanSubscriptionReport(BaseModel):
    month: str  # e.g., "2024-04"
    package_days: int
    total_subscriptions: int


class WeeklyAnalysisReport(BaseModel):
    total_analyses: int


class NewUsersReport(BaseModel):
    last_hour: int
    last_day: int


class PlanStatusReport(BaseModel):
    active_users: int
    expired_users: int
    trial_users: int


class AdminReportsResponse(BaseModel):
    monthly_analyses: List[MonthlyAnalysisReport]
    monthly_plan_subscriptions: List[MonthlyPlanSubscriptionReport]
    weekly_analysis: WeeklyAnalysisReport
    new_users: NewUsersReport
    plan_status: PlanStatusReport
