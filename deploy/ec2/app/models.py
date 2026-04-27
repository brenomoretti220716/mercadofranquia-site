"""
SQLAlchemy 2.0 models for Mercado Franquia — Postgres schema matching the
tables created by migrate.py.

Intended path on EC2: ~/mercadofranquia-api/app/models.py

Usage:
    from app.models import Base, User, Franchise, ...
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as s:
        ...
"""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Double,
    Enum as SQLEnum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums (Sprint 3)
# ---------------------------------------------------------------------------


class ProfileType(str, enum.Enum):
    """Perfil escolhido pelo user no cadastro — separação de jornadas."""

    INVESTOR = "INVESTOR"
    FRANCHISOR = "FRANCHISOR"


# ---------------------------------------------------------------------------
# Association table: m-to-m User ⟷ Franchise (franchisees)
# ---------------------------------------------------------------------------

franchise_franchisees = Table(
    "_FranchiseFranchisees",
    Base.metadata,
    Column(
        "A",
        String(191),
        ForeignKey("Franchise.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    ),
    Column(
        "B",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("A", "B", name="_FranchiseFranchisees_AB_unique"),
    Index("_FranchiseFranchisees_B_index", "B"),
)


# ---------------------------------------------------------------------------
# Users / auth
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "User"

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    email: Mapped[str] = mapped_column(String(191), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(191), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MEMBER", server_default="MEMBER"
    )
    profileType: Mapped[ProfileType] = mapped_column(
        "profileType",
        SQLEnum(ProfileType, name="ProfileType", native_enum=True, create_type=True),
        nullable=False,
        server_default="INVESTOR",
    )
    isActive: Mapped[bool] = mapped_column(
        "isActive", nullable=False, default=True, server_default="true"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    cpf: Mapped[Optional[str]] = mapped_column(String(191), unique=True)
    phone: Mapped[str] = mapped_column(String(191), nullable=False, unique=True)
    jobTitle: Mapped[Optional[str]] = mapped_column(
        "jobTitle",
        String(100),
        nullable=True,
    )
    hubspotContactId: Mapped[Optional[str]] = mapped_column(
        "hubspotContactId", String(100)
    )

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    quiz_submission: Mapped[Optional["QuizSubmission"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    franchises_owned: Mapped[list["Franchise"]] = relationship(
        back_populates="owner",
        foreign_keys="Franchise.ownerId",
    )
    franchises_as_franchisee: Mapped[list["Franchise"]] = relationship(
        secondary=franchise_franchisees, back_populates="franchisees"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    franchisor_profile: Mapped[Optional["FranchisorUser"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    franchisor_request: Mapped[Optional["FranchisorRequest"]] = relationship(
        back_populates="user",
        uselist=False,
        foreign_keys="FranchisorRequest.userId",
        cascade="all, delete-orphan",
    )
    news_comments: Mapped[list["NewsComment"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )


class UserProfile(Base):
    __tablename__ = "UserProfile"

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    userId: Mapped[str] = mapped_column(
        "userId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
    )
    city: Mapped[str] = mapped_column(String(191), nullable=False)
    interestSectors: Mapped[str] = mapped_column(
        "interestSectors", String(191), nullable=False
    )
    interestRegion: Mapped[str] = mapped_column(
        "interestRegion", String(191), nullable=False
    )
    investmentRange: Mapped[str] = mapped_column(
        "investmentRange", String(191), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class UserVerification(Base):
    __tablename__ = "UserVerification"

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(String(191), nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expiresAt: Mapped[datetime] = mapped_column(
        "expiresAt", DateTime(timezone=False), nullable=False
    )
    isUsed: Mapped[bool] = mapped_column(
        "isUsed", nullable=False, default=False, server_default="false"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    usedAt: Mapped[Optional[datetime]] = mapped_column(
        "usedAt", DateTime(timezone=False)
    )
    userData: Mapped[Optional[str]] = mapped_column("userData", Text)


# ---------------------------------------------------------------------------
# Contact / Franchise core
# ---------------------------------------------------------------------------

class ContactInfo(Base):
    __tablename__ = "ContactInfo"

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    phone: Mapped[str] = mapped_column(String(191), nullable=False)
    email: Mapped[str] = mapped_column(String(191), nullable=False)
    website: Mapped[Optional[str]] = mapped_column(Text)

    franchise: Mapped[Optional["Franchise"]] = relationship(
        back_populates="contact", uselist=False
    )


class Franchise(Base):
    __tablename__ = "Franchise"
    __table_args__ = (
        Index("Franchise_segment_idx", "segment"),
        Index("Franchise_slug_idx", "slug"),
        Index("Franchise_totalUnits_idx", "totalUnits"),
        Index("Franchise_averageRating_idx", "averageRating"),
        Index("Franchise_minimumInvestment_idx", "minimumInvestment"),
        Index("Franchise_maximumInvestment_idx", "maximumInvestment"),
        Index("Franchise_franchiseFee_idx", "franchiseFee"),
        Index("Franchise_averageMonthlyRevenue_idx", "averageMonthlyRevenue"),
        Index("Franchise_minimumReturnOnInvestment_idx", "minimumReturnOnInvestment"),
        Index("Franchise_isActive_idx", "isActive"),
        Index("Franchise_status_idx", "status"),
        Index("Franchise_isActive_segment_idx", "isActive", "segment"),
        Index("Franchise_isActive_totalUnits_idx", "isActive", "totalUnits"),
        Index("Franchise_isSponsored_idx", "isSponsored"),
        Index("Franchise_isActive_isSponsored_idx", "isActive", "isSponsored"),
        Index("Franchise_ownerId_fkey", "ownerId"),
        CheckConstraint(
            "\"unitsEvolution\" IN ('UP','DOWN','MAINTAIN')",
            name="Franchise_unitsEvolution_check",
        ),
    )

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(191))
    slug: Mapped[Optional[str]] = mapped_column(String(191), unique=True)
    headquarterState: Mapped[Optional[str]] = mapped_column(
        "headquarterState", String(191)
    )
    segment: Mapped[Optional[str]] = mapped_column(String(191))
    subsegment: Mapped[Optional[str]] = mapped_column(String(191))
    businessType: Mapped[Optional[str]] = mapped_column("businessType", Text)
    franchiseStartYear: Mapped[Optional[int]] = mapped_column("franchiseStartYear")
    abfSince: Mapped[Optional[int]] = mapped_column("abfSince")
    videoUrl: Mapped[Optional[str]] = mapped_column("videoUrl", Text)
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    contactId: Mapped[Optional[int]] = mapped_column(
        "contactId",
        Integer,
        ForeignKey("ContactInfo.id", ondelete="CASCADE", onupdate="CASCADE"),
        unique=True,
    )
    ownerId: Mapped[Optional[str]] = mapped_column(
        "ownerId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
    )
    isActive: Mapped[bool] = mapped_column(
        "isActive", nullable=False, default=True, server_default="true"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="APPROVED", server_default="APPROVED"
    )
    brandFoundationYear: Mapped[Optional[int]] = mapped_column("brandFoundationYear")
    description: Mapped[Optional[str]] = mapped_column(Text)
    detailedDescription: Mapped[Optional[str]] = mapped_column(
        "detailedDescription", Text
    )
    headquarter: Mapped[Optional[str]] = mapped_column(String(191))
    isAbfAssociated: Mapped[Optional[bool]] = mapped_column("isAbfAssociated")
    logoUrl: Mapped[Optional[str]] = mapped_column("logoUrl", String(191))
    totalUnits: Mapped[Optional[int]] = mapped_column("totalUnits")
    totalUnitsInBrazil: Mapped[Optional[int]] = mapped_column("totalUnitsInBrazil")
    thumbnailUrl: Mapped[Optional[str]] = mapped_column("thumbnailUrl", String(191))
    lastScrapedAt: Mapped[Optional[datetime]] = mapped_column(
        "lastScrapedAt", DateTime(timezone=False)
    )
    scrapedWebsite: Mapped[Optional[str]] = mapped_column(
        "scrapedWebsite", String(191)
    )
    calculationBaseAdFee: Mapped[Optional[str]] = mapped_column(
        "calculationBaseAdFee", String(191)
    )
    calculationBaseRoyaltie: Mapped[Optional[str]] = mapped_column(
        "calculationBaseRoyaltie", String(191)
    )
    galleryUrls: Mapped[Optional[str]] = mapped_column("galleryUrls", Text)
    isReview: Mapped[bool] = mapped_column(
        "isReview", nullable=False, default=True, server_default="true"
    )
    averageRating: Mapped[Optional[float]] = mapped_column("averageRating", Double)
    ratingSum: Mapped[int] = mapped_column(
        "ratingSum", nullable=False, default=0, server_default="0"
    )
    reviewCount: Mapped[int] = mapped_column(
        "reviewCount", nullable=False, default=0, server_default="0"
    )
    unitsEvolution: Mapped[Optional[str]] = mapped_column(
        "unitsEvolution", String(10)
    )
    favoritesCount: Mapped[int] = mapped_column(
        "favoritesCount", nullable=False, default=0, server_default="0"
    )
    isSponsored: Mapped[bool] = mapped_column(
        "isSponsored", nullable=False, default=False, server_default="false"
    )
    sponsorPlacements: Mapped[dict] = mapped_column(
        "sponsorPlacements", JSONB, nullable=False
    )
    minimumInvestment: Mapped[Optional[Decimal]] = mapped_column(
        "minimumInvestment", Numeric(15, 2)
    )
    maximumInvestment: Mapped[Optional[Decimal]] = mapped_column(
        "maximumInvestment", Numeric(15, 2)
    )
    minimumReturnOnInvestment: Mapped[Optional[int]] = mapped_column(
        "minimumReturnOnInvestment"
    )
    maximumReturnOnInvestment: Mapped[Optional[int]] = mapped_column(
        "maximumReturnOnInvestment"
    )
    franchiseFee: Mapped[Optional[Decimal]] = mapped_column(
        "franchiseFee", Numeric(15, 2)
    )
    averageMonthlyRevenue: Mapped[Optional[Decimal]] = mapped_column(
        "averageMonthlyRevenue", Numeric(15, 2)
    )
    royalties: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    advertisingFee: Mapped[Optional[Decimal]] = mapped_column(
        "advertisingFee", Numeric(5, 2)
    )
    setupCapital: Mapped[Optional[Decimal]] = mapped_column(
        "setupCapital", Numeric(15, 2)
    )
    workingCapital: Mapped[Optional[Decimal]] = mapped_column(
        "workingCapital", Numeric(15, 2)
    )
    storeArea: Mapped[Optional[int]] = mapped_column("storeArea")

    # Landing redesign — Fatia 0 (alembic 66a4e030b691). Todos nullable;
    # backend-acceptance habilitado na Fatia 0.5. Frontend consumira nas
    # fatias seguintes (UI do editor + landing publica nova).
    tagline: Mapped[Optional[str]] = mapped_column(String(200))
    differentials: Mapped[Optional[list]] = mapped_column(JSONB)
    idealFranchiseeProfile: Mapped[Optional[str]] = mapped_column(
        "idealFranchiseeProfile", Text
    )
    processSteps: Mapped[Optional[list]] = mapped_column("processSteps", JSONB)
    testimonials: Mapped[Optional[list]] = mapped_column(JSONB)
    bannerUrl: Mapped[Optional[str]] = mapped_column("bannerUrl", String(500))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    whatsapp: Mapped[Optional[str]] = mapped_column(String(20))
    publicEmail: Mapped[Optional[str]] = mapped_column("publicEmail", String(100))
    instagramUrl: Mapped[Optional[str]] = mapped_column("instagramUrl", String(200))
    facebookUrl: Mapped[Optional[str]] = mapped_column("facebookUrl", String(200))
    linkedinUrl: Mapped[Optional[str]] = mapped_column("linkedinUrl", String(200))
    totalUnitsUpdatedAt: Mapped[Optional[datetime]] = mapped_column(
        "totalUnitsUpdatedAt", DateTime(timezone=False)
    )
    totalUnitsLastConfirmedAt: Mapped[Optional[datetime]] = mapped_column(
        "totalUnitsLastConfirmedAt", DateTime(timezone=False)
    )

    # Relationships
    contact: Mapped[Optional["ContactInfo"]] = relationship(
        back_populates="franchise"
    )
    owner: Mapped[Optional["User"]] = relationship(
        back_populates="franchises_owned", foreign_keys=[ownerId]
    )
    franchisees: Mapped[list["User"]] = relationship(
        secondary=franchise_franchisees, back_populates="franchises_as_franchisee"
    )
    business_models: Mapped[list["BusinessModel"]] = relationship(
        back_populates="franchise", cascade="all, delete-orphan"
    )
    monthly_units: Mapped[list["FranchiseMonthlyUnits"]] = relationship(
        back_populates="franchise", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="franchise", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="franchise", cascade="all, delete-orphan"
    )


class Favorite(Base):
    __tablename__ = "Favorite"
    __table_args__ = (
        UniqueConstraint(
            "userId", "franchiseId", name="Favorite_userId_franchiseId_key"
        ),
        Index("Favorite_userId_idx", "userId"),
        Index("Favorite_franchiseId_idx", "franchiseId"),
    )

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    userId: Mapped[str] = mapped_column(
        "userId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    franchiseId: Mapped[str] = mapped_column(
        "franchiseId",
        String(191),
        ForeignKey("Franchise.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="favorites")
    franchise: Mapped["Franchise"] = relationship(back_populates="favorites")


class BusinessModel(Base):
    __tablename__ = "BusinessModel"
    __table_args__ = (Index("BusinessModel_franchiseId_idx", "franchiseId"),)

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    photoUrl: Mapped[str] = mapped_column("photoUrl", String(191), nullable=False)
    franchiseId: Mapped[str] = mapped_column(
        "franchiseId",
        String(191),
        ForeignKey("Franchise.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    # Fatia 1.8.1 — dataset financeiro por modelo (alembic c4d8e9a1b3f2).
    # Tipos espelham Franchise pra consistency. Todos nullable.
    franchiseFee: Mapped[Optional[Decimal]] = mapped_column(
        "franchiseFee", Numeric(15, 2)
    )
    royalties: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    advertisingFee: Mapped[Optional[Decimal]] = mapped_column(
        "advertisingFee", Numeric(5, 2)
    )
    workingCapital: Mapped[Optional[Decimal]] = mapped_column(
        "workingCapital", Numeric(15, 2)
    )
    setupCapital: Mapped[Optional[Decimal]] = mapped_column(
        "setupCapital", Numeric(15, 2)
    )
    averageMonthlyRevenue: Mapped[Optional[Decimal]] = mapped_column(
        "averageMonthlyRevenue", Numeric(15, 2)
    )
    storeArea: Mapped[Optional[int]] = mapped_column("storeArea")
    calculationBaseRoyaltie: Mapped[Optional[str]] = mapped_column(
        "calculationBaseRoyaltie", String(191)
    )
    calculationBaseAdFee: Mapped[Optional[str]] = mapped_column(
        "calculationBaseAdFee", String(191)
    )

    # Fatia 1.8.1 (alembic e7a3f1d8b9c2) — investment total + payback per
    # modelo. Sem name override porque colunas sao lowercase no DB
    # (mesmo padrao de royalties).
    investment: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    payback: Mapped[Optional[int]] = mapped_column()

    franchise: Mapped["Franchise"] = relationship(back_populates="business_models")


class FranchiseMonthlyUnits(Base):
    __tablename__ = "FranchiseMonthlyUnits"
    __table_args__ = (
        UniqueConstraint(
            "franchiseId",
            "period",
            name="FranchiseMonthlyUnits_franchiseId_period_key",
        ),
        Index(
            "FranchiseMonthlyUnits_period_franchiseId_idx",
            "period",
            "franchiseId",
        ),
        Index(
            "FranchiseMonthlyUnits_franchiseId_period_idx",
            "franchiseId",
            "period",
        ),
    )

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    franchiseId: Mapped[str] = mapped_column(
        "franchiseId",
        String(191),
        ForeignKey("Franchise.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    period: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
    units: Mapped[Optional[int]] = mapped_column(Integer)
    collectedAt: Mapped[datetime] = mapped_column(
        "collectedAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    source: Mapped[Optional[str]] = mapped_column(String(191))

    franchise: Mapped["Franchise"] = relationship(back_populates="monthly_units")


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

class Review(Base):
    __tablename__ = "Review"
    __table_args__ = (
        Index("Review_authorId_fkey", "authorId"),
        Index("Review_franchiseId_fkey", "franchiseId"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    anonymous: Mapped[bool] = mapped_column(nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    franchiseId: Mapped[str] = mapped_column(
        "franchiseId",
        String(191),
        ForeignKey("Franchise.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    isActive: Mapped[bool] = mapped_column(
        "isActive", nullable=False, default=True, server_default="true"
    )
    isFranchisee: Mapped[bool] = mapped_column(
        "isFranchisee", nullable=False, default=False, server_default="false"
    )
    authorId: Mapped[str] = mapped_column(
        "authorId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    franchise: Mapped["Franchise"] = relationship(back_populates="reviews")
    author: Mapped["User"] = relationship(back_populates="reviews")
    responses: Mapped[list["ReviewResponse"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ReviewResponse(Base):
    __tablename__ = "ReviewResponse"
    __table_args__ = (
        Index("ReviewResponse_authorId_fkey", "authorId"),
        Index("ReviewResponse_reviewId_fkey", "reviewId"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    reviewId: Mapped[int] = mapped_column(
        "reviewId",
        Integer,
        ForeignKey("Review.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    authorId: Mapped[str] = mapped_column(
        "authorId",
        String(191),
        ForeignKey("User.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )

    review: Mapped["Review"] = relationship(back_populates="responses")


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

class News(Base):
    __tablename__ = "News"

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(191), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    photoUrl: Mapped[Optional[str]] = mapped_column("photoUrl", String(191))
    isActive: Mapped[bool] = mapped_column(
        "isActive", nullable=False, default=True, server_default="true"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    comments: Mapped[list["NewsComment"]] = relationship(
        back_populates="news", cascade="all, delete-orphan"
    )


class NewsComment(Base):
    __tablename__ = "NewsComment"
    __table_args__ = (
        Index("NewsComment_newsId_idx", "newsId"),
        Index("NewsComment_authorId_idx", "authorId"),
    )

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    newsId: Mapped[str] = mapped_column(
        "newsId",
        String(191),
        ForeignKey("News.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    authorId: Mapped[str] = mapped_column(
        "authorId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    news: Mapped["News"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="news_comments")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "Notification"
    __table_args__ = (
        Index("Notification_userId_idx", "userId"),
        Index("Notification_userId_isRead_idx", "userId", "isRead"),
        Index("Notification_createdAt_idx", "createdAt"),
    )

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    userId: Mapped[str] = mapped_column(
        "userId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(191), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(191))
    isRead: Mapped[bool] = mapped_column(
        "isRead", nullable=False, default=False, server_default="false"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    readAt: Mapped[Optional[datetime]] = mapped_column(
        "readAt", DateTime(timezone=False)
    )

    user: Mapped["User"] = relationship(back_populates="notifications")


# ---------------------------------------------------------------------------
# Franchisor
# ---------------------------------------------------------------------------

class FranchisorUser(Base):
    __tablename__ = "FranchisorUser"

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    streamName: Mapped[str] = mapped_column("streamName", String(191), nullable=False)
    userId: Mapped[str] = mapped_column(
        "userId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="franchisor_profile")


class FranchisorRequest(Base):
    __tablename__ = "FranchisorRequest"
    __table_args__ = (
        Index("FranchisorRequest_status_idx", "status"),
        Index("FranchisorRequest_userId_idx", "userId"),
        Index("FranchisorRequest_reviewedBy_fkey", "reviewedBy"),
    )

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    userId: Mapped[str] = mapped_column(
        "userId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    streamName: Mapped[str] = mapped_column("streamName", String(191), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default="PENDING"
    )
    rejectionReason: Mapped[Optional[str]] = mapped_column("rejectionReason", Text)
    reviewedBy: Mapped[Optional[str]] = mapped_column(
        "reviewedBy",
        String(191),
        ForeignKey("User.id", ondelete="SET NULL", onupdate="CASCADE"),
    )
    reviewedAt: Mapped[Optional[datetime]] = mapped_column(
        "reviewedAt", DateTime(timezone=False)
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="NEW", server_default="NEW"
    )
    franchiseId: Mapped[Optional[str]] = mapped_column(
        "franchiseId",
        String(191),
        ForeignKey("Franchise.id", ondelete="SET NULL", onupdate="CASCADE"),
    )
    claimReason: Mapped[Optional[str]] = mapped_column("claimReason", Text)
    hubspotCompanyId: Mapped[Optional[str]] = mapped_column(
        "hubspotCompanyId", String(100)
    )

    user: Mapped["User"] = relationship(
        back_populates="franchisor_request", foreign_keys=[userId]
    )
    franchise: Mapped[Optional["Franchise"]] = relationship(
        foreign_keys=[franchiseId]
    )


# ---------------------------------------------------------------------------
# Quiz, rankings & stats
# ---------------------------------------------------------------------------

class QuizSubmission(Base):
    __tablename__ = "QuizSubmission"

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    userId: Mapped[str] = mapped_column(
        "userId",
        String(191),
        ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
    )
    answers: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="quiz_submission")


class RankingBugnumber(Base):
    __tablename__ = "RankingBugnumber"
    __table_args__ = (
        UniqueConstraint("year", "position", name="RankingBugnumber_year_position_key"),
        Index("RankingBugnumber_year_idx", "year"),
    )

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    growthPercentage: Mapped[Decimal] = mapped_column(
        "growthPercentage", Numeric(5, 2), nullable=False
    )
    isWorst: Mapped[bool] = mapped_column(
        "isWorst", nullable=False, default=False, server_default="false"
    )
    isHidden: Mapped[bool] = mapped_column(
        "isHidden", nullable=False, default=False, server_default="false"
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )


class AbfSegmentEntry(Base):
    __tablename__ = "AbfSegmentEntry"
    __table_args__ = (
        UniqueConstraint(
            "year",
            "quarter",
            "acronym",
            name="AbfSegmentEntry_year_quarter_acronym_key",
        ),
        Index("AbfSegmentEntry_year_quarter_idx", "year", "quarter"),
    )

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[str] = mapped_column(String(2), nullable=False)
    segment: Mapped[str] = mapped_column(String(191), nullable=False)
    acronym: Mapped[str] = mapped_column(String(10), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )


class PlatformStatistics(Base):
    __tablename__ = "PlatformStatistics"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, default=1, server_default="1"
    )
    franchisesReviewed: Mapped[int] = mapped_column(
        "franchisesReviewed", nullable=False, default=0, server_default="0"
    )
    totalReviews: Mapped[int] = mapped_column(
        "totalReviews", nullable=False, default=0, server_default="0"
    )
    totalSegments: Mapped[int] = mapped_column(
        "totalSegments", nullable=False, default=0, server_default="0"
    )
    medianRating: Mapped[Optional[float]] = mapped_column("medianRating", Double)
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )


# ---------------------------------------------------------------------------
# Macro / ABF pipeline (Fase 1A)
#
# Fed by the daily macro sync (services/macro_sync.py, wired via systemd
# timer). SQLite schema at api/database.py in the pipeline repo; these are
# PostgreSQL equivalents with PascalCase tables and camelCase columns to
# match the rest of the Prisma-era schema.
# ---------------------------------------------------------------------------


class SegmentAcronym(Base):
    __tablename__ = "SegmentAcronym"
    __table_args__ = (
        UniqueConstraint("segmento", name="SegmentAcronym_segmento_key"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    segmento: Mapped[str] = mapped_column(String(100), nullable=False)
    acronimo: Mapped[str] = mapped_column(String(10), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class AbfReport(Base):
    __tablename__ = "AbfReport"
    __table_args__ = (
        UniqueConstraint("periodo", name="AbfReport_periodo_key"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    periodo: Mapped[str] = mapped_column(String(10), nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    trimestre: Mapped[Optional[int]] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="trimestral"
    )
    arquivo: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="importado"
    )
    notas: Mapped[Optional[str]] = mapped_column(Text)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.current_timestamp(),
        onupdate=func.now(),
    )


class AbfRevenue(Base):
    __tablename__ = "AbfRevenue"
    __table_args__ = (
        UniqueConstraint(
            "periodo",
            "segmento",
            "tipoDado",
            name="AbfRevenue_periodo_segmento_tipoDado_key",
        ),
        Index("AbfRevenue_periodo_idx", "periodo"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    periodo: Mapped[str] = mapped_column(String(10), nullable=False)
    segmento: Mapped[str] = mapped_column(String(100), nullable=False)
    valorMm: Mapped[Decimal] = mapped_column(
        "valorMm", Numeric(18, 4), nullable=False
    )
    tipoDado: Mapped[str] = mapped_column(
        "tipoDado", String(20), nullable=False, server_default="trimestral"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class AbfIndicator(Base):
    __tablename__ = "AbfIndicator"
    __table_args__ = (
        UniqueConstraint("periodo", name="AbfIndicator_periodo_key"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    periodo: Mapped[str] = mapped_column(String(10), nullable=False)
    empregosDiretos: Mapped[Optional[int]] = mapped_column(
        "empregosDiretos", Integer
    )
    numRedes: Mapped[Optional[int]] = mapped_column("numRedes", Integer)
    numUnidades: Mapped[Optional[int]] = mapped_column("numUnidades", Integer)
    ticketMedio: Mapped[Optional[Decimal]] = mapped_column(
        "ticketMedio", Numeric(18, 4)
    )
    varEmpregosPct: Mapped[Optional[Decimal]] = mapped_column(
        "varEmpregosPct", Numeric(8, 4)
    )
    varRedesPct: Mapped[Optional[Decimal]] = mapped_column(
        "varRedesPct", Numeric(8, 4)
    )
    varUnidadesPct: Mapped[Optional[Decimal]] = mapped_column(
        "varUnidadesPct", Numeric(8, 4)
    )
    empregosPorUnidade: Mapped[Optional[int]] = mapped_column(
        "empregosPorUnidade", Integer
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class AbfUnitsRanking(Base):
    __tablename__ = "AbfUnitsRanking"
    __table_args__ = (
        UniqueConstraint(
            "ano", "posicao", name="AbfUnitsRanking_ano_posicao_key"
        ),
        Index("AbfUnitsRanking_ano_idx", "ano"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    posicao: Mapped[int] = mapped_column(Integer, nullable=False)
    posicaoAnt: Mapped[Optional[int]] = mapped_column("posicaoAnt", Integer)
    marca: Mapped[str] = mapped_column(String(150), nullable=False)
    segmento: Mapped[Optional[str]] = mapped_column(String(100))
    unidades: Mapped[Optional[int]] = mapped_column(Integer)
    unidadesAnt: Mapped[Optional[int]] = mapped_column("unidadesAnt", Integer)
    varPct: Mapped[Optional[Decimal]] = mapped_column("varPct", Numeric(8, 4))
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class AbfProjection(Base):
    __tablename__ = "AbfProjection"
    __table_args__ = (
        UniqueConstraint(
            "anoReferencia", name="AbfProjection_anoReferencia_key"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    anoReferencia: Mapped[int] = mapped_column(
        "anoReferencia", Integer, nullable=False
    )
    fatVarMinPct: Mapped[Optional[Decimal]] = mapped_column(
        "fatVarMinPct", Numeric(8, 4)
    )
    fatVarMaxPct: Mapped[Optional[Decimal]] = mapped_column(
        "fatVarMaxPct", Numeric(8, 4)
    )
    fatRealizadoPct: Mapped[Optional[Decimal]] = mapped_column(
        "fatRealizadoPct", Numeric(8, 4)
    )
    redesVarPct: Mapped[Optional[Decimal]] = mapped_column(
        "redesVarPct", Numeric(8, 4)
    )
    unidadesVarPct: Mapped[Optional[Decimal]] = mapped_column(
        "unidadesVarPct", Numeric(8, 4)
    )
    empregosVarPct: Mapped[Optional[Decimal]] = mapped_column(
        "empregosVarPct", Numeric(8, 4)
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class MacroBcb(Base):
    __tablename__ = "MacroBcb"
    __table_args__ = (
        UniqueConstraint(
            "data", "codigoSerie", name="MacroBcb_data_codigoSerie_key"
        ),
        Index("MacroBcb_codigoSerie_data_idx", "codigoSerie", "data"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    data: Mapped[str] = mapped_column(String(10), nullable=False)
    codigoSerie: Mapped[int] = mapped_column(
        "codigoSerie", Integer, nullable=False
    )
    nomeSerie: Mapped[str] = mapped_column(
        "nomeSerie", String(100), nullable=False
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    fonte: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="BCB"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class MacroIbge(Base):
    __tablename__ = "MacroIbge"
    __table_args__ = (
        UniqueConstraint(
            "data",
            "codigoAgregado",
            "variavel",
            "localidade",
            name="MacroIbge_data_agregado_variavel_localidade_key",
        ),
        Index("MacroIbge_codigoAgregado_data_idx", "codigoAgregado", "data"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    data: Mapped[str] = mapped_column(String(10), nullable=False)
    codigoAgregado: Mapped[int] = mapped_column(
        "codigoAgregado", Integer, nullable=False
    )
    variavel: Mapped[str] = mapped_column(String(200), nullable=False)
    localidade: Mapped[str] = mapped_column(String(200), nullable=False)
    valor: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    fonte: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="IBGE"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class MacroSyncLog(Base):
    __tablename__ = "MacroSyncLog"
    __table_args__ = (
        Index("MacroSyncLog_fonte_createdAt_idx", "fonte", "createdAt"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    fonte: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    registrosInseridos: Mapped[int] = mapped_column(
        "registrosInseridos", Integer, nullable=False, server_default="0"
    )
    duracaoMs: Mapped[int] = mapped_column(
        "duracaoMs", Integer, nullable=False, server_default="0"
    )
    erro: Mapped[Optional[str]] = mapped_column(Text)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class PmcIbge(Base):
    __tablename__ = "PmcIbge"
    __table_args__ = (
        UniqueConstraint(
            "data", "codigoSegmento", name="PmcIbge_data_codigoSegmento_key"
        ),
        Index("PmcIbge_codigoSegmento_data_idx", "codigoSegmento", "data"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    data: Mapped[str] = mapped_column(String(10), nullable=False)
    codigoSegmento: Mapped[str] = mapped_column(
        "codigoSegmento", String(20), nullable=False
    )
    nomeSegmento: Mapped[str] = mapped_column(
        "nomeSegmento", String(200), nullable=False
    )
    variacaoMensal: Mapped[Optional[Decimal]] = mapped_column(
        "variacaoMensal", Numeric(8, 4)
    )
    variacaoAnual: Mapped[Optional[Decimal]] = mapped_column(
        "variacaoAnual", Numeric(8, 4)
    )
    indice: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    fonte: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="IBGE/PMC"
    )
    urlFonte: Mapped[Optional[str]] = mapped_column("urlFonte", Text)
    dataColeta: Mapped[Optional[datetime]] = mapped_column(
        "dataColeta", DateTime(timezone=False)
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


class CagedBcb(Base):
    __tablename__ = "CagedBcb"
    __table_args__ = (
        UniqueConstraint(
            "data", "codigoBcb", name="CagedBcb_data_codigoBcb_key"
        ),
        Index("CagedBcb_codigoBcb_data_idx", "codigoBcb", "data"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1,
        ),
        primary_key=True,
    )
    data: Mapped[str] = mapped_column(String(10), nullable=False)
    estoque: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    saldo: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    setor: Mapped[str] = mapped_column(String(100), nullable=False)
    codigoBcb: Mapped[int] = mapped_column(
        "codigoBcb", Integer, nullable=False
    )
    fonte: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="MTE/CAGED via BCB"
    )
    urlFonte: Mapped[Optional[str]] = mapped_column("urlFonte", Text)
    dataColeta: Mapped[Optional[datetime]] = mapped_column(
        "dataColeta", DateTime(timezone=False)
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )


# ---------------------------------------------------------------------------
# Admin audit log (Sprint 3) — registra ações admin sensíveis
# ---------------------------------------------------------------------------


class AdminActionLog(Base):
    __tablename__ = "AdminActionLog"
    __table_args__ = (
        Index("idx_admin_action_log_target", "targetUserId"),
        Index("idx_admin_action_log_created", "createdAt"),
    )

    id: Mapped[str] = mapped_column(
        String(191),
        primary_key=True,
        server_default=func.gen_random_uuid().cast(String),
    )
    adminId: Mapped[str] = mapped_column(
        "adminId",
        String(191),
        ForeignKey("User.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    targetUserId: Mapped[Optional[str]] = mapped_column(
        "targetUserId",
        String(191),
        ForeignKey("User.id", ondelete="SET NULL", onupdate="CASCADE"),
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
    )
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.current_timestamp(),
    )
