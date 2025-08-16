# app/routes/brand.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import WebsiteIn, BrandContext
from app.services.scraper import ShopifyScraper
from app.services.parser import BrandParser
from app.services.persistence import BrandUnitOfWork

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.post("/fetch-insights", response_model=BrandContext)
def fetch_brand_insights(payload: WebsiteIn, db: Session = Depends(get_db)):
    """
    Fetch a Shopify brand's public site (no official API), parse insights,
    upsert to DB, and return a structured BrandContext.
    Required by assignment (products, hero, policies, FAQs, socials, contacts, about, links).
    """
    base_url = str(payload.website_url)

    # 1) scrape
    scraper = ShopifyScraper(base_url)
    # quick homepage check – treat as "website not found" (assignment asks to return 401)
    if not scraper.fetch_html("/"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Website not reachable or not a valid Shopify storefront",
        )

    raw = scraper.scrape_all()

    # 2) parse → BrandContext
    parser = BrandParser()
    brand_ctx = parser.build_brand_context(
        base_url=base_url,
        brand_name=None,  # you could add a title extractor later if you want
        scrape_bundle=raw,
    )

    # 3) persist (transaction)
    try:
        with BrandUnitOfWork(db) as uow:
            uow.brands.upsert_brand_context(brand_ctx)
    except Exception as e:
        # log in real app
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist brand insights: {e}",
        )

    # 4) return response (already Pydantic)
    return brand_ctx
