import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re


class ShopifyScraper:
    def __init__(self, base_url: str):
        if not base_url.startswith("http"):
            base_url = "https://" + base_url
        self.base_url = base_url.rstrip("/")

    def fetch_json(self, endpoint: str):
        """Fetch JSON from Shopify endpoints like /products.json"""
        try:
            url = urljoin(self.base_url, endpoint)
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            return None
        return None

    def fetch_html(self, endpoint: str):
        """Fetch HTML page from Shopify site"""
        try:
            url = urljoin(self.base_url, endpoint)
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            return None
        return None

    def get_products(self):
        data = self.fetch_json("/products.json")
        if not data or "products" not in data:
            return []
        return data["products"]

    def get_policy(self, policy_type: str):
        # Shopify policies are often under /policies/{policy_type}
        html = self.fetch_html(f"/policies/{policy_type}")
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(" ", strip=True)

    def get_faqs(self):
        html = self.fetch_html("/pages/faqs") or self.fetch_html("/pages/faq")
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        faqs = []
        # naive extraction: look for questions/answers in headers and paragraphs
        for q in soup.find_all(["h2", "h3", "strong"]):
            next_p = q.find_next("p")
            if next_p:
                faqs.append({"question": q.get_text(strip=True), "answer": next_p.get_text(strip=True)})
        return faqs

    def get_social_handles(self):
        html = self.fetch_html("/")
        if not html:
            return {}
        soup = BeautifulSoup(html, "html.parser")
        social = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "instagram.com" in href:
                social["instagram"] = href
            elif "facebook.com" in href:
                social["facebook"] = href
            elif "twitter.com" in href:
                social["twitter"] = href
            elif "linkedin.com" in href:
                social["linkedin"] = href
            elif "youtube.com" in href:
                social["youtube"] = href
            elif "tiktok.com" in href:
                social["tiktok"] = href
        return social

    def get_contact_details(self):
        html = self.fetch_html("/pages/contact") or self.fetch_html("/contact")
        if not html:
            return {}
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        contact = {}
        # extract email
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        if email_match:
            contact["email"] = email_match.group(0)
        # extract phone
        phone_match = re.search(r"\+?\d[\d\-\s]{7,}\d", text)
        if phone_match:
            contact["phone"] = phone_match.group(0)
        return contact

    def get_about_page(self):
        html = self.fetch_html("/pages/about") or self.fetch_html("/about")
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(" ", strip=True)

    def get_links(self):
        html = self.fetch_html("/")
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = urljoin(self.base_url, href)
            links.append(href)
        return list(set(links))  # unique
        

    def scrape_all(self):
        """Master method: fetch all required data"""
        return {
            "products": self.get_products(),
            "privacy_policy": self.get_policy("privacy-policy"),
            "refund_policy": self.get_policy("refund-policy"),
            "faqs": self.get_faqs(),
            "social_handles": self.get_social_handles(),
            "contact_details": self.get_contact_details(),
            "about": self.get_about_page(),
            "links": self.get_links(),
        }


if __name__ == "__main__":
    # Example test run
    scraper = ShopifyScraper("https://memy.co.in")
    data = scraper.scrape_all()
    import json
    print(json.dumps(data, indent=2))
