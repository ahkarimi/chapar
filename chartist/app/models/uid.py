from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, func
from app.models.database import Base

class UIDTable(Base):
    __tablename__ = "uid_table"

    uid = Column(BigInteger, primary_key=True, unique=True, index=True)
    referral_code = Column(String, nullable=True)
    referral_uid = Column(String, nullable=True)
    deposit_amount_usdt = Column(Numeric(precision=18, scale=2), nullable=True)
    withdrawal_amount_usdt = Column(Numeric(precision=18, scale=2), nullable=True)
    spot_assets_usdt = Column(Numeric(precision=18, scale=2), nullable=True)
    total_assets_usdt = Column(Numeric(precision=18, scale=2), nullable=True)
    trading_volume_usdt = Column(Numeric(precision=18, scale=2), nullable=True)
