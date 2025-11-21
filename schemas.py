"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- Article -> "article" collection
- Category -> "category" collection
- Comment -> "comment" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Category(BaseModel):
    """
    News categories
    Collection: "category"
    """
    name: str = Field(..., description="Category name, e.g., World, Business")
    slug: Optional[str] = Field(None, description="URL-friendly identifier")
    description: Optional[str] = Field(None, description="Optional category description")
    is_active: bool = Field(True, description="Whether this category is active")

class Article(BaseModel):
    """
    News articles
    Collection: "article"
    """
    title: str = Field(..., description="Headline")
    slug: Optional[str] = Field(None, description="URL-friendly identifier derived from title")
    summary: Optional[str] = Field(None, description="Short summary for cards")
    content: str = Field(..., description="Full article content (Markdown or HTML)")
    author: str = Field(..., description="Author name")
    category: Optional[str] = Field(None, description="Category slug or name")
    image_url: Optional[str] = Field(None, description="Hero image URL")
    tags: Optional[List[str]] = Field(default_factory=list, description="List of tags")
    published_at: Optional[datetime] = Field(None, description="Publish time; defaults to now")
    is_published: bool = Field(True, description="Whether the article is visible")

class Comment(BaseModel):
    """
    Article comments
    Collection: "comment"
    """
    article_id: str = Field(..., description="Related article _id as string")
    name: str = Field(..., description="Commenter name")
    message: str = Field(..., description="Comment body")
    is_approved: bool = Field(True, description="Whether comment is approved")
