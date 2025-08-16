# app/models/db_models.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, declarative_mixin

from app.database import Base


# ---------- Enums ----------

class PolicyType(str, Enum):
    PRIVACY = "privacy_policy"
    REFUND = "refund_policy"
    RETURN = "return_policy"
    SHIPPING = "shipping_policy"          # common on Shopify
    TERMS = "terms_of_service"            # common on Shopify


class ContactType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"


class SocialPlatform(str, Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    PINTEREST = "pinterest"
    LINKEDIN = "linkedin"
    OTHER = "other"


class LinkType(str, Enum):
    ORDER_TRACKING = "order_tracking"
    CONTACT_US = "contact_us"
    BLOG = "blog"
    FAQ = "faq"
    ABOUT = "about"
    HOMEPAGE = "homepage"
    OTHER = "other"


# ---------- Mixins ----------

@declarative_mixin
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------- Core Entities ----------

class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    website_url: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="brand", cascade="all, delete-orphan"
    )
    policies: Mapped[List["Policy"]] = relationship(
        "Policy", back_populates="brand", cascade="all, delete-orphan"
    )
    faqs: Mapped[List["FAQ"]] = relationship(
        "FAQ", back_populates="brand", cascade="all, delete-orphan"
    )
    social_handles: Mapped[List["SocialHandle"]] = relationship(
        "SocialHandle", back_populates="brand", cascade="all, delete-orphan"
    )
    contact_details: Mapped[List["ContactDetail"]] = relationship(
        "ContactDetail", back_populates="brand", cascade="all, delete-orphan"
    )
    links: Mapped[List["ImportantLink"]] = relationship(
        "ImportantLink", back_populates="brand", cascade="all, delete-orphan"
    )

    # Bonus: competitor graph (many-to-many via CompetitorMap)
    competitors: Mapped[List["Brand"]] = relationship(
        "Brand",
        secondary="competitor_map",
        primaryjoin="Brand.id==CompetitorMap.brand_id",
        secondaryjoin="Brand.id==CompetitorMap.competitor_brand_id",
        viewonly=True,
    )

    __table_args__ = (
        Index("ix_brand_name", "name"),
    )


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    shopify_product_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    handle: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_hero: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="products")

    __table_args__ = (
        UniqueConstraint("brand_id", "handle", name="uq_product_brand_handle"),
        Index("ix_product_title", "title"),
        Index("ix_product_is_hero", "is_hero"),
    )


class Policy(Base, TimestampMixin):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    type: Mapped[PolicyType] = mapped_column(SAEnum(PolicyType), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="policies")

    __table_args__ = (
        UniqueConstraint("brand_id", "type", name="uq_policy_brand_type"),
    )


class FAQ(Base, TimestampMixin):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(String(191),index=True, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # page where found

    brand: Mapped["Brand"] = relationship("Brand", back_populates="faqs")

    __table_args__ = (
        Index("ix_faq_question", "question"),
    )


class SocialHandle(Base, TimestampMixin):
    __tablename__ = "social_handles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    platform: Mapped[SocialPlatform] = mapped_column(SAEnum(SocialPlatform), nullable=False)
    handle_or_url: Mapped[str] = mapped_column(String(512), nullable=False)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="social_handles")

    __table_args__ = (
        UniqueConstraint("brand_id", "platform", name="uq_social_brand_platform"),
    )


class ContactDetail(Base, TimestampMixin):
    __tablename__ = "contact_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    type: Mapped[ContactType] = mapped_column(SAEnum(ContactType), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="contact_details")

    __table_args__ = (
        Index("ix_contact_type", "type"),
    )


class ImportantLink(Base, TimestampMixin):
    __tablename__ = "important_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    link_type: Mapped[LinkType] = mapped_column(SAEnum(LinkType), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="links")

    __table_args__ = (
        UniqueConstraint("brand_id", "link_type", name="uq_link_brand_type"),
    )


# ---------- Bonus: competitor mapping (self-referencing M2M) ----------

class CompetitorMap(Base, TimestampMixin):
    __tablename__ = "competitor_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    competitor_brand_id: Mapped[int] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )

    __table_args__ = (
        UniqueConstraint("brand_id", "competitor_brand_id", name="uq_competitor_pair"),
    )


# ---------- Optional: crawl bookkeeping (helps debugging/re-scrapes) ----------

class CrawlLog(Base, TimestampMixin):
    __tablename__ = "crawl_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
