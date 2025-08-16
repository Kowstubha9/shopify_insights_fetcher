from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import CompetitorResponse, BrandContext, Product, Policy, FAQ, SocialHandle, ContactDetail, ImportantLink
from app.models.db_models import Brand
from app.services.competitor import CompetitorService

router = APIRouter(prefix="/api/competitors", tags=["competitors"])


def _brand_to_context(brand: Brand) -> BrandContext:
    """
    Convert full Brand ORM object into BrandContext with all relationships.
    """
    return BrandContext(
        brand_id=brand.id,
        brand_name=brand.name,
        website_url=brand.website_url,
        about=brand.about,
        product_catalog=[Product.from_attributes(p) for p in brand.products],
        hero_products=[Product.from_attributes(p) for p in brand.products if p.is_hero],
        policies=[Policy.from_attributes(p) for p in brand.policies],
        faqs=[FAQ.from_attributes(f) for f in brand.faqs],
        social_handles=[SocialHandle.from_attributes(s) for s in brand.social_handles],
        contact_details=[ContactDetail.from_attributes(c) for c in brand.contact_details],
        important_links=[ImportantLink.from_attributes(l) for l in brand.links],
    )


@router.get("/{brand_id}", response_model=CompetitorResponse)
def get_brand_competitors(brand_id: int, db: Session = Depends(get_db)):
    """
    Fetch competitors for a given brand ID.
    Returns the brand and its competitors as fully detailed BrandContext objects.
    """
    # Fetch main brand
    brand: Brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {brand_id} not found",
        )

    # Fetch competitors using service
    service = CompetitorService(db)
    competitor_brands: List[Brand] = service.get_competitor_brands(brand_id)

    # Convert ORM to BrandContext
    main_context = _brand_to_context(brand)
    competitors_context = [_brand_to_context(c) for c in competitor_brands]

    # Return response
    return CompetitorResponse(
        brand=main_context,
        competitors=competitors_context,
    )
