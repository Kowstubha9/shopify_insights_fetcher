from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import db_models as m
from app.models.schemas import BrandContext, Product, Policy, FAQ, SocialHandle, ContactDetail, ImportantLink


class BrandRepository:
    """
    Repository responsible for persisting a BrandContext into relational tables.
    Upsert strategy:
      - Brand: by website_url (unique)
      - Product: by (brand_id, handle) if handle exists, else by (brand_id, title)
      - Policy: by (brand_id, type)
      - FAQ: replace-all (simpler & consistent since pages change often)
      - SocialHandle: by (brand_id, platform)
      - ContactDetail: by (brand_id, type)
      - ImportantLink: by (brand_id, link_type)
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------- public API ----------

    def upsert_brand_context(self, ctx: BrandContext) -> m.Brand:
        brand = self._upsert_brand_metadata(ctx)

        self._upsert_products(brand, ctx.product_catalog)
        self._upsert_policies(brand, ctx.policies)
        self._replace_faqs(brand, ctx.faqs)
        self._upsert_socials(brand, ctx.social_handles)
        self._upsert_contacts(brand, ctx.contact_details)
        self._upsert_links(brand, ctx.important_links)

        self.db.flush()
        self.db.refresh(brand)
        return brand

    # ---------- brand ----------

    def _upsert_brand_metadata(self, ctx: BrandContext) -> m.Brand:
        brand = (
            self.db.query(m.Brand)
            .filter(m.Brand.website_url == str(ctx.website_url))
            .one_or_none()
        )
        if brand is None:
            brand = m.Brand(
                website_url=str(ctx.website_url),
                name=ctx.brand_name,
                about=ctx.about,
            )
            self.db.add(brand)
            self.db.flush()
        else:
            brand.name = ctx.brand_name or brand.name
            brand.about = ctx.about or brand.about
        return brand

    # ---------- products ----------

    def _product_key(self, p: Product) -> Tuple[str, str]:
        """
        Key used to find existing products. Prefer handle, fallback to title.
        """
        handle = (p.handle or "").strip().lower()
        title = (p.title or "").strip().lower()
        if handle:
            return ("handle", handle)
        return ("title", title)

    def _upsert_products(self, brand: m.Brand, products: Iterable[Product]) -> None:
        # Fetch existing for minimal queries
        existing = (
            self.db.query(m.Product)
            .filter(m.Product.brand_id == brand.id)
            .all()
        )

        by_handle: Dict[str, m.Product] = {}
        by_title: Dict[str, m.Product] = {}

        for e in existing:
            if e.handle:
                by_handle[e.handle.strip().lower()] = e
            if e.title:
                by_title[e.title.strip().lower()] = e

        seen: set[int] = set()
        for p in products:
            key_type, key_value = self._product_key(p)
            if key_type == "handle" and key_value in by_handle:
                row = by_handle[key_value]
            elif key_type == "title" and key_value in by_title:
                row = by_title[key_value]
            else:
                row = m.Product(brand_id=brand.id)
                self.db.add(row)

            # Update fields
            row.shopify_product_id = getattr(p, "id", None) or row.shopify_product_id
            row.title = p.title
            row.handle = p.handle
            row.url = str(p.url) if p.url else None
            row.price = p.price
            row.currency = p.currency
            row.is_hero = bool(p.is_hero)
            row.image_url = str(p.image_url) if p.image_url else None
            row.vendor = p.vendor
            row.product_type = p.product_type
            row.description = p.description

            self.db.flush()
            seen.add(row.id)

    # policies

    def _upsert_policies(self, brand: m.Brand, policies: Iterable[Policy]) -> None:
        existing = (
            self.db.query(m.Policy)
            .filter(m.Policy.brand_id == brand.id)
            .all()
        )
        by_type = {e.type: e for e in existing}

        for p in policies:
            row = by_type.get(p.type)
            if row is None:
                row = m.Policy(brand_id=brand.id, type=p.type)
                self.db.add(row)
            row.url = str(p.url) if p.url else row.url
            # Prefer new content if present
            if p.content:
                row.content = p.content

    # faqs 

    def _replace_faqs(self, brand: m.Brand, faqs: Iterable[FAQ]) -> None:
        self.db.query(m.FAQ).filter(m.FAQ.brand_id == brand.id).delete(synchronize_session=False)
        for f in faqs:
            self.db.add(
                m.FAQ(
                    brand_id=brand.id,
                    question=f.question,
                    answer=f.answer,
                    url=str(f.url) if f.url else None,
                )
            )

    # socials 

    def _upsert_socials(self, brand: m.Brand, socials: Iterable[SocialHandle]) -> None:
        existing = (
            self.db.query(m.SocialHandle)
            .filter(m.SocialHandle.brand_id == brand.id)
            .all()
        )
        by_platform = {e.platform: e for e in existing}

        for s in socials:
            row = by_platform.get(s.platform)
            if row is None:
                row = m.SocialHandle(brand_id=brand.id, platform=s.platform)
                self.db.add(row)
            row.handle_or_url = s.handle_or_url

    # contacts 

    def _upsert_contacts(self, brand: m.Brand, contacts: Iterable[ContactDetail]) -> None:
        existing = (
            self.db.query(m.ContactDetail)
            .filter(m.ContactDetail.brand_id == brand.id)
            .all()
        )
        by_type = {e.type: e for e in existing}

        for c in contacts:
            row = by_type.get(c.type)
            if row is None:
                row = m.ContactDetail(brand_id=brand.id, type=c.type)
                self.db.add(row)
            row.value = c.value

    # links 

    def _upsert_links(self, brand: m.Brand, links: Iterable[ImportantLink]) -> None:
        existing = (
            self.db.query(m.ImportantLink)
            .filter(m.ImportantLink.brand_id == brand.id)
            .all()
        )
        by_type = {e.link_type: e for e in existing}

        for l in links:
            row = by_type.get(l.link_type)
            if row is None:
                row = m.ImportantLink(brand_id=brand.id, link_type=l.link_type)
                self.db.add(row)
            row.url = str(l.url)
            row.label = l.label or row.label


class BrandUnitOfWork:
    """
    Thin UoW wrapper to own the transaction boundary.
    """

    def __init__(self, db: Session):
        self.db = db
        self.brands = BrandRepository(db)

    def __enter__(self) -> "BrandUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.db.rollback()
        else:
            self.db.commit()
       