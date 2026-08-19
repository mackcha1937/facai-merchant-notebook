"""SQLAlchemy ORM 数据模型。

字段设计遵循 03 文档第 4 节核心数据模型。
剩余次数不落库，由 total_count - used_count 计算，避免字段矛盾。
价格使用整数“分”存储，避免浮点误差。
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """返回 naive UTC 时间，便于 SQLite 存取与比较。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    aliases = relationship(
        "CustomerAlias", back_populates="customer", cascade="all, delete-orphan"
    )
    packages = relationship("Package", back_populates="customer")
    ledger_entries = relationship("LedgerEntry", back_populates="customer")


class CustomerAlias(Base):
    __tablename__ = "customer_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="aliases")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    packages = relationship("Package", back_populates="service")


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchased_on: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="packages")
    service = relationship("Service", back_populates="packages")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(30), nullable=False)
    package_id: Mapped[int | None] = mapped_column(ForeignKey("packages.id"), nullable=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_on: Mapped[str | None] = mapped_column(String(20), nullable=True)
    original_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_prompt_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="ledger_entries")
    service = relationship("Service")
