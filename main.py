import os
import re
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import Category as CategorySchema, Article as ArticleSchema

app = FastAPI(title="News API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


@app.get("/")
def read_root():
    return {"message": "News API running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ===== Categories =====
class CategoryIn(CategorySchema):
    pass


@app.get("/api/categories")
def list_categories():
    items = get_documents("category", {"is_active": True}) if db else []
    # Sort by name
    items = sorted(items, key=lambda x: x.get("name", ""))
    # Map _id to string
    for it in items:
        it["_id"] = str(it.get("_id"))
    return {"categories": items}


@app.post("/api/categories")
def create_category(payload: CategoryIn):
    data = payload.model_dump()
    if not data.get("slug"):
        data["slug"] = slugify(data["name"])
    # Ensure unique slug
    existing = db["category"].find_one({"slug": data["slug"]}) if db else None
    if existing:
        raise HTTPException(status_code=400, detail="Category with this slug already exists")
    new_id = create_document("category", data)
    created = db["category"].find_one({"_id": ObjectId(new_id)})
    created["_id"] = str(created["_id"])
    return created


# ===== Articles =====
class ArticleIn(ArticleSchema):
    pass


@app.get("/api/articles")
def list_articles(
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    query = {"is_published": True}
    if category:
        query["$or"] = [
            {"category": category},
            {"tags": {"$in": [category]}},
        ]
    if q:
        query["$text"] = {"$search": q}
    items = get_documents("article", query, limit=limit) if db else []
    # Sort newest first
    items.sort(key=lambda x: x.get("published_at") or x.get("created_at"), reverse=True)
    # Map ids and truncate content
    for it in items:
        it["_id"] = str(it.get("_id"))
        if it.get("content"):
            it["content"] = str(it["content"])[:500] + ("..." if len(str(it["content"])) > 500 else "")
    return {"articles": items}


@app.get("/api/articles/{slug}")
def get_article(slug: str):
    doc = db["article"].find_one({"slug": slug}) if db else None
    if not doc:
        raise HTTPException(status_code=404, detail="Article not found")
    doc["_id"] = str(doc["_id"])
    return doc


@app.get("/api/articles/id/{item_id}")
def get_article_by_id(item_id: str):
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db["article"].find_one({"_id": oid}) if db else None
    if not doc:
        raise HTTPException(status_code=404, detail="Article not found")
    doc["_id"] = str(doc["_id"])
    return doc


@app.post("/api/articles")
def create_article(payload: ArticleIn):
    data = payload.model_dump()
    if not data.get("slug"):
        data["slug"] = slugify(data["title"])[:120]
    if not data.get("published_at"):
        data["published_at"] = datetime.utcnow()
    existing = db["article"].find_one({"slug": data["slug"]}) if db else None
    if existing:
        raise HTTPException(status_code=400, detail="Article with this slug already exists")
    new_id = create_document("article", data)
    created = db["article"].find_one({"_id": ObjectId(new_id)})
    created["_id"] = str(created["_id"])
    return created


# ===== Seed sample data =====
@app.post("/api/seed")
def seed_sample():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    categories = [
        {"name": "World", "slug": "world"},
        {"name": "Business", "slug": "business"},
        {"name": "Technology", "slug": "technology"},
        {"name": "Sports", "slug": "sports"},
        {"name": "Entertainment", "slug": "entertainment"},
    ]

    for c in categories:
        if not db["category"].find_one({"slug": c["slug"]}):
            create_document("category", {**c, "is_active": True})

    samples = [
        {
            "title": "Tech giants unveil next-gen AI chips",
            "summary": "A new wave of processors promises faster, greener AI.",
            "content": "Major semiconductor companies announced...",
            "author": "News Desk",
            "category": "technology",
            "image_url": "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=1200&auto=format&fit=crop",
            "tags": ["ai", "chips", "semiconductor"],
        },
        {
            "title": "Markets rally as inflation cools",
            "summary": "Global markets see gains after latest CPI data.",
            "content": "Stocks across major indices rose today...",
            "author": "Finance Team",
            "category": "business",
            "image_url": "https://images.unsplash.com/photo-1559526324-593bc073d938?q=80&w=1200&auto=format&fit=crop",
            "tags": ["markets", "inflation"],
        },
        {
            "title": "Historic win in championship final",
            "summary": "An underdog story captures fans worldwide.",
            "content": "In a thrilling finale, the underdogs clinched...",
            "author": "Sports Desk",
            "category": "sports",
            "image_url": "https://images.unsplash.com/photo-1502877338535-766e1452684a?q=80&w=1200&auto=format&fit=crop",
            "tags": ["final", "championship"],
        },
    ]

    created_count = 0
    for s in samples:
        slug = slugify(s["title"])[:120]
        if not db["article"].find_one({"slug": slug}):
            create_document("article", {**s, "slug": slug, "is_published": True, "published_at": datetime.utcnow()})
            created_count += 1

    return {"status": "ok", "created": created_count}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
