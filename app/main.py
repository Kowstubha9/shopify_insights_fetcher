# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.brand import router as brand_router
from app.routes.competitors import router as competitors_router

from app.database import Base, engine

# ---------- Create all tables if not exist ----------
Base.metadata.create_all(bind=engine)

# ---------- FastAPI app ----------
app = FastAPI(
    title="Shopify Brand Insights API",
    description="Fetch and manage Shopify brand data, products, policies, FAQs, social handles, contacts, links, and competitors",
    version="1.0.0",
)

# ---------- Middleware ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Include routes ----------

app.include_router(brand_router)
#app.include_router(competitors_router)

# ---------- Root endpoint ----------
@app.get("/", tags=["root"])
def root():
    return {"message": "Welcome to Shopify Brand Insights API. Use /docs for API documentation."}
