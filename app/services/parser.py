from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from pydantic import HttpUrl

from app.models.schemas import (
    BrandContext,
    ContactDetail,
    FAQ,
    ImportantLink,
    Policy,
    Product,
    SocialHandle,
)
from app.models.db_models import (
    ContactType,
    LinkType,
    PolicyType,
    SocialPlatform,
)


class BrandParser:
    """
    Transforms raw scraped content from ShopifyScraper into structured Pydantic models.
    """

    # public API 

    def build_brand_context(
        self,
        *,
        base_url: str,
        brand_name: Optional[str],
        scrape_bundle: Dict,
    ) -> BrandContext:
        """
        Orchestrates parsing of all sections and returns a BrandContext.
        :param base_url: canonical site root (e.g., https://memy.co.in)
        :param brand_name: optional brand display name (can be parsed elsewhere); persisted in Brand later
        :param scrape_bundle: dict from ShopifyScraper.scrape_all()
        """
        base_url = self._normalize_base(base_url)

        products_raw = scrape_bundle.get("products", []) or []
        homepage_links = scrape_bundle.get("links", []) or []

        products, hero_products = self._parse_products(
            base_url=base_url,
            products_json=products_raw,
            homepage_links=homepage_links,
        )

        policies = self._parse_policies(
            base_url=base_url,
            privacy_text=scrape_bundle.get("privacy_policy"),
            refund_text=scrape_bundle.get("refund_policy"),
        )

        faqs = self._parse_faqs(
            faqs_raw=scrape_bundle.get("faqs", []) or [],
            faq_page_url=self._guess_faq_page_url(base_url, homepage_links),
        )

        socials = self._parse_socials(scrape_bundle.get("social_handles", {}) or {})
        contacts = self._parse_contacts(scrape_bundle.get("contact_details", {}) or {})
        links = self._parse_links(base_url, homepage_links)

        brand = BrandContext(
            brand_name=brand_name,
            website_url=base_url,  # Pydantic will validate HttpUrl
            about=scrape_bundle.get("about"),
            product_catalog=products,
            hero_products=hero_products,
            policies=policies,
            faqs=faqs,
            social_handles=socials,
            contact_details=contacts,
            important_links=links,
        )
        return brand

    # products 

    def _parse_products(
        self,
        *,
        base_url: str,
        products_json: List[Dict],
        homepage_links: List[str],
    ) -> Tuple[List[Product], List[Product]]:
        """
        Map /products.json payload into Product schemas and detect 'hero' products
        by checking if a product URL appears on the homepage links.
        """
        # Precompute homepage product-url candidates
        homepage_product_paths = {
            self._canonicalize_product_path(link)
            for link in homepage_links
            if "/products/" in link
        }

        catalog: List[Product] = []
        heroes: List[Product] = []

        for p in products_json:
            # Shopify product fields are fairly standard
            handle = p.get("handle")
            title = p.get("title") or handle or "Untitled"
            shopify_id = str(p.get("id")) if p.get("id") is not None else None
            vendor = p.get("vendor")
            product_type = p.get("product_type")
            body_html = p.get("body_html")

            # URL for PDP
            url = self._product_url(base_url, handle) if handle else None

            # Basic price extraction (first variant)
            price, currency = self._extract_price_currency_from_variants(p.get("variants", []))

            # Image (first image)
            image_url = None
            if isinstance(p.get("images"), list) and p["images"]:
                image_url = p["images"][0].get("src")

            product_schema = Product(
                id=None,
                title=title,
                url=url,
                handle=handle,
                price=price,
                currency=currency,
                is_hero=False,  # set below
                image_url=image_url,
                vendor=vendor,
                product_type=product_type,
                description=self._strip_html(body_html) if body_html else None,
            )
            catalog.append(product_schema)

            # Detect hero: if its PDP path appears in homepage links
            if handle:
                pdp_path = f"/products/{handle}".lower()
                if pdp_path in homepage_product_paths:
                    product_schema.is_hero = True
                    heroes.append(product_schema)

        # Fallback: if no hero detected, consider top 4 products as hero candidates (common home sections)
        if not heroes:
            heroes = catalog[:4]
            for hp in heroes:
                hp.is_hero = True

        return catalog, heroes

    def _extract_price_currency_from_variants(self, variants: Iterable[Dict]) -> Tuple[Optional[float], Optional[str]]:
        if not variants:
            return None, None
        first = next(iter(variants), None)
        if not first:
            return None, None
        # price is often a string in Shopify JSON
        price_raw = first.get("price")
        try:
            price = float(price_raw) if price_raw is not None else None
        except (TypeError, ValueError):
            price = None
        currency = first.get("currency") or None  # not always present
        return price, currency

    # policies

    def _parse_policies(
        self,
        *,
        base_url: str,
        privacy_text: Optional[str],
        refund_text: Optional[str],
    ) -> List[Policy]:
        policies: List[Policy] = []

        if privacy_text:
            policies.append(
                Policy(
                    type=PolicyType.PRIVACY,
                    url=self._join(base_url, "/policies/privacy-policy"),
                    content=privacy_text,
                )
            )

        if refund_text:
            # Return + refund are frequently together; we mark as REFUND here
            policies.append(
                Policy(
                    type=PolicyType.REFUND,
                    url=self._join(base_url, "/policies/refund-policy"),
                    content=refund_text,
                )
            )

        # Add common placeholders (these might get filled by a second pass scraper)
        policies.extend(
            [
                Policy(type=PolicyType.SHIPPING, url=self._join(base_url, "/policies/shipping-policy")),
                Policy(type=PolicyType.TERMS, url=self._join(base_url, "/policies/terms-of-service")),
                Policy(type=PolicyType.RETURN, url=self._join(base_url, "/policies/return-policy")),
            ]
        )

        # Deduplicate by type, preferring ones that have content
        merged: Dict[PolicyType, Policy] = {}
        for pol in policies:
            existing = merged.get(pol.type)
            if not existing:
                merged[pol.type] = pol
            else:
                # prefer the one that has content
                if (not existing.content) and pol.content:
                    merged[pol.type] = pol

        return list(merged.values())

    # FAQs

    def _parse_faqs(self, *, faqs_raw: List[Dict], faq_page_url: Optional[str]) -> List[FAQ]:
        faqs: List[FAQ] = []
        for item in faqs_raw:
            q = (item.get("question") or "").strip()
            if not q:
                continue
            a = (item.get("answer") or "").strip() or None
            faqs.append(
                FAQ(
                    question=q,
                    answer=a,
                    url=faq_page_url,
                )
            )
        return faqs

    # socials

    def _parse_socials(self, social_map: Dict[str, str]) -> List[SocialHandle]:
        platform_map = {
            "instagram": SocialPlatform.INSTAGRAM,
            "facebook": SocialPlatform.FACEBOOK,
            "tiktok": SocialPlatform.TIKTOK,
            "twitter": SocialPlatform.TWITTER,
            "x": SocialPlatform.TWITTER,
            "youtube": SocialPlatform.YOUTUBE,
            "pinterest": SocialPlatform.PINTEREST,
            "linkedin": SocialPlatform.LINKEDIN,
        }
        results: List[SocialHandle] = []
        for key, url in social_map.items():
            key_norm = key.strip().lower()
            platform = platform_map.get(key_norm, SocialPlatform.OTHER)
            results.append(SocialHandle(platform=platform, handle_or_url=url))
        return results

    # contacts

    def _parse_contacts(self, contact_map: Dict[str, str]) -> List[ContactDetail]:
        out: List[ContactDetail] = []
        email = (contact_map.get("email") or "").strip()
        phone = (contact_map.get("phone") or "").strip()
        if email:
            out.append(ContactDetail(type=ContactType.EMAIL, value=email))
        if phone:
            out.append(ContactDetail(type=ContactType.PHONE, value=phone))
        return out

    # links

    def _parse_links(self, base_url: str, links: List[str]) -> List[ImportantLink]:
        result: List[ImportantLink] = []
        seen_types: set[LinkType] = set()

        def add(link_type: LinkType, url: str, label: Optional[str] = None):
            if link_type in seen_types:
                return
            result.append(ImportantLink(link_type=link_type, url=self._absolutize(base_url, url), label=label))
            seen_types.add(link_type)

        for href in links:
            h = href.lower()
            if "order" in h and "track" in h:
                add(LinkType.ORDER_TRACKING, href, "Order Tracking")
            elif "/contact" in h or "/pages/contact" in h:
                add(LinkType.CONTACT_US, href, "Contact Us")
            elif "/blog" in h:
                add(LinkType.BLOG, href, "Blog")
            elif "/pages/faq" in h or "/pages/faqs" in h or "/faq" in h:
                add(LinkType.FAQ, href, "FAQ")
            elif "/pages/about" in h or "/about" in h:
                add(LinkType.ABOUT, href, "About")
            elif h.rstrip("/") == base_url.rstrip("/"):
                add(LinkType.HOMEPAGE, href, "Homepage")

        # Always ensure homepage exists
        if LinkType.HOMEPAGE not in seen_types:
            add(LinkType.HOMEPAGE, base_url, "Homepage")

        return result

    # helpers 

    def _normalize_base(self, base_url: str) -> str:
        if not base_url.startswith("http"):
            base_url = "https://" + base_url
        return base_url.rstrip("/")

    def _join(self, base_url: str, path: str) -> str:
        return urljoin(base_url, path)

    def _absolutize(self, base_url: str, href: str) -> str:
        if href.startswith("http://") or href.startswith("https://"):
            return href
        return urljoin(base_url, href)

    def _product_url(self, base_url: str, handle: Optional[str]) -> Optional[str]:
        if not handle:
            return None
        return self._join(base_url, f"/products/{handle}")

    def _canonicalize_product_path(self, href: str) -> str:
        """
        Return just the lowercased path for PDP detection (e.g., '/products/handle').
        """
        try:
            parsed = urlparse(href)
            path = parsed.path or ""
        except Exception:
            path = href
        return path.rstrip("/").lower()

    def _strip_html(self, html: Optional[str]) -> Optional[str]:
        if not html:
            return None
        # very light strip; you may use BeautifulSoup if needed, but avoid heavy deps here
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _guess_faq_page_url(self, base_url: str, links: List[str]) -> Optional[str]:
        candidates = ["/pages/faq", "/pages/faqs", "/faq"]
        for href in links:
            low = href.lower()
            if any(c in low for c in candidates):
                return self._absolutize(base_url, href)
        return None
