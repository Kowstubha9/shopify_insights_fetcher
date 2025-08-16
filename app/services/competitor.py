# app/services/competitor.py
from __future__ import annotations
from typing import List

from sqlalchemy.orm import Session, selectinload

from app.models.db_models import Brand, CompetitorMap


class CompetitorService:
    """
    Service for managing and retrieving competitor relationships.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_competitor_brands(self, brand_id: int) -> List[Brand]:
        """
        Fetch all competitors for a given brand ID along with their full relationships
        (products, policies, FAQs, socials, contacts, links) to avoid lazy-loading.
        """
        competitors = (
            self.db.query(Brand)
            .join(CompetitorMap, CompetitorMap.competitor_brand_id == Brand.id)
            .options(
                selectinload(Brand.products),
                selectinload(Brand.policies),
                selectinload(Brand.faqs),
                selectinload(Brand.social_handles),
                selectinload(Brand.contact_details),
                selectinload(Brand.links),
            )
            .filter(CompetitorMap.brand_id == brand_id)
            .all()
        )
        return competitors

    def add_competitor(self, brand_id: int, competitor_id: int) -> bool:
        """
        Add a competitor mapping. Returns True if added, False if already exists.
        """
        existing = (
            self.db.query(CompetitorMap)
            .filter(
                CompetitorMap.brand_id == brand_id,
                CompetitorMap.competitor_brand_id == competitor_id,
            )
            .first()
        )
        if existing:
            return False

        mapping = CompetitorMap(brand_id=brand_id, competitor_brand_id=competitor_id)
        self.db.add(mapping)
        self.db.commit()
        return True

    def remove_competitor(self, brand_id: int, competitor_id: int) -> bool:
        """
        Remove a competitor mapping. Returns True if removed, False if not found.
        """
        mapping = (
            self.db.query(CompetitorMap)
            .filter(
                CompetitorMap.brand_id == brand_id,
                CompetitorMap.competitor_brand_id == competitor_id,
            )
            .first()
        )
        if not mapping:
            return False

        self.db.delete(mapping)
        self.db.commit()
        return True
