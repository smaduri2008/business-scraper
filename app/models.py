"""
SQLAlchemy ORM models.
"""
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    niche = Column(String(100))
    location = Column(String(255))
    website = Column(String(500))
    phone = Column(String(50))
    address = Column(String(500))
    rating = Column(Float)
    reviews_count = Column(Integer)
    hours = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    instagram = relationship(
        "InstagramData", back_populates="business", uselist=False, cascade="all, delete-orphan"
    )
    analysis = relationship(
        "Analysis", back_populates="business", uselist=False, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "niche": self.niche,
            "location": self.location,
            "website": self.website,
            "phone": self.phone,
            "address": self.address,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "hours": self.hours,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "instagram": self.instagram.to_dict() if self.instagram else None,
            "analysis": self.analysis.to_dict() if self.analysis else None,
        }


class InstagramData(Base):
    __tablename__ = "instagram_data"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    username = Column(String(100))
    followers = Column(Integer)
    following = Column(Integer)
    posts = Column(Integer)
    engagement_rate = Column(Float)
    bio = Column(Text)
    is_verified = Column(Boolean, default=False)
    is_business = Column(Boolean, default=False)

    business = relationship("Business", back_populates="instagram")

    def to_dict(self):
        return {
            "username": self.username,
            "followers": self.followers,
            "following": self.following,
            "posts": self.posts,
            "engagement_rate": self.engagement_rate,
            "bio": self.bio,
            "is_verified": self.is_verified,
            "is_business": self.is_business,
        }


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    revenue_streams = Column(Text)  # JSON string
    estimated_revenue_tier = Column(String(50))
    pricing_strategy = Column(String(50))
    service_quality_score = Column(Float)
    competitive_assessment = Column(Text)
    niche_specific_insights = Column(Text)

    business = relationship("Business", back_populates="analysis")

    def to_dict(self):
        revenue_streams = None
        if self.revenue_streams:
            try:
                revenue_streams = json.loads(self.revenue_streams)
            except (json.JSONDecodeError, TypeError):
                revenue_streams = self.revenue_streams
        return {
            "revenue_streams": revenue_streams,
            "estimated_revenue_tier": self.estimated_revenue_tier,
            "pricing_strategy": self.pricing_strategy,
            "service_quality_score": self.service_quality_score,
            "competitive_assessment": self.competitive_assessment,
            "niche_specific_insights": self.niche_specific_insights,
        }
