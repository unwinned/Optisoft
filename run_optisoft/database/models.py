from database.base_models import BaseModel
from sqlalchemy import String, Float, Boolean
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy import Integer


class Base(DeclarativeBase):
    pass


class OPBaseModel(BaseModel):
    __tablename__ = "op_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    op_balance: Mapped[float] = mapped_column(Float, nullable=True)
