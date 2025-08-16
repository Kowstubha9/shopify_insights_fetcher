# app/models/schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from app.models.db_models import PolicyType, ContactType, SocialPlatform, LinkType


# ---------- Common ----------

class APIMessage(BaseModel):
    message: str


class WebsiteIn(BaseModel):
    website_url: HttpUrl = Field(..., description="Root URL of the Shopify store")


# ---------- Product ----------

class Product(BaseModel):
    id: Optional[int] = Field(None, description="Internal DB id")
    title: str
    url: Optional[HttpUrl] = None
    handle: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    is_hero: bool = False
    image_url: Optional[HttpUrl] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic v2 (works as orm_mode in v1)


# ---------- Policy ----------

class Policy(BaseModel):
    type: PolicyType
    url: Optional[HttpUrl] = None
    content: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- FAQ ----------

class FAQ(BaseModel):
    question: str
    answer: Optional[str] = None
    url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True


# ---------- Social ----------

class SocialHandle(BaseModel):
    platform: SocialPlatform
    handle_or_url: str

    class Config:
        from_attributes = True


# ---------- Contacts ----------

class ContactDetail(BaseModel):
    type: ContactType
    value: str  # email or phone; validate format at parsing layer

    class Config:
        from_attributes = True


# ---------- Links ----------

class ImportantLink(BaseModel):
    link_type: LinkType
    url: HttpUrl
    label: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Brand Context (main response) ----------

class BrandContext(BaseModel):
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    website_url: HttpUrl
    about: Optional[str] = None

    product_catalog: List[Product] = []
    hero_products: List[Product] = []

    policies: List[Policy] = []
    faqs: List[FAQ] = []
    social_handles: List[SocialHandle] = []
    contact_details: List[ContactDetail] = []
    important_links: List[ImportantLink] = []

    scraped_at: datetime = Field(default_factory=datetime.utcnow)


# ---------- Competitor (bonus) ----------

class CompetitorResponse(BaseModel):
    brand: BrandContext
    competitors: List[BrandContext] = []


# ---------- Error Schemas ----------

class ErrorResponse(BaseModel):
    detail: str
