from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    Column,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Many-to-many association table for items <-> tags
item_tags = Table(
    "item_tags",
    Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", server_default="ACTIVE",
    )
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="CNY", server_default="CNY",
    )
    purchase_channel: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    warranty_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_lifespan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retired_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary=item_tags, backref="items", lazy="selectin",
    )
    images: Mapped[list["ItemImage"]] = relationship(  # noqa: F821
        back_populates="item", lazy="selectin", cascade="all, delete-orphan",
    )
    additional_costs: Mapped[list["AdditionalCost"]] = relationship(  # noqa: F821
        back_populates="item", lazy="selectin", cascade="all, delete-orphan",
    )
