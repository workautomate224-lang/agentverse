"""
Data source models for real-world data integration.
Supports census data, research datasets, and web-scraped data.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DataSourceType(str, Enum):
    """Types of data sources."""
    CENSUS = "census"
    RESEARCH = "research"
    WEB_SCRAPE = "web_scrape"
    SURVEY = "survey"
    PROPRIETARY = "proprietary"


class DataSourceStatus(str, Enum):
    """Status of data source."""
    ACTIVE = "active"
    PENDING = "pending"
    ERROR = "error"
    DEPRECATED = "deprecated"


class DataSource(Base):
    """
    Data source registry - tracks all integrated data sources.
    Provides provenance and metadata for data used in persona generation.
    """

    __tablename__ = "data_sources"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # census, research, web_scrape, survey, proprietary

    # Source identification
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Data details
    coverage_region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # US, UK, global, state:CA, etc.
    coverage_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Quality metrics
    accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    credentials_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # active, pending, error, deprecated
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    census_data = relationship("CensusData", back_populates="data_source", cascade="all, delete-orphan")
    regional_profiles = relationship("RegionalProfile", back_populates="data_source", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<DataSource {self.name} ({self.source_type})>"


class CensusData(Base):
    """
    Cached census data for demographic distributions.
    Stores processed data from US Census Bureau and other official sources.
    """

    __tablename__ = "census_data"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    data_source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )

    # Geographic scope
    country: Mapped[str] = mapped_column(String(10), default="US", nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    county: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metro_area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Data type
    data_category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # age, gender, income, education, occupation, marital_status

    # Distribution data (JSON format for flexibility)
    distribution: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Example: {"18-24": 0.12, "25-34": 0.18, "35-44": 0.16, ...}

    # Source metadata
    survey_year: Mapped[int] = mapped_column(Integer, nullable=False)
    survey_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # ACS 5-Year, Decennial Census, etc.
    margin_of_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Raw data reference
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    data_source = relationship("DataSource", back_populates="census_data")

    def __repr__(self) -> str:
        return f"<CensusData {self.data_category} ({self.country}/{self.state or 'national'})>"


class RegionalProfile(Base):
    """
    Comprehensive regional profiles combining multiple data categories.
    Used for generating geographically-accurate personas.
    """

    __tablename__ = "regional_profiles"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    data_source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )

    # Region identification
    region_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    region_name: Mapped[str] = mapped_column(String(255), nullable=False)
    region_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # country, state, county, metro, custom
    parent_region_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Combined demographic profile
    demographics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure:
    # {
    #   "age_distribution": {"18-24": 0.12, ...},
    #   "gender_distribution": {"Male": 0.49, "Female": 0.51},
    #   "income_distribution": {"<25k": 0.15, ...},
    #   "education_distribution": {"High school": 0.25, ...},
    #   "occupation_distribution": {...},
    #   "ethnicity_distribution": {...},
    #   "marital_status_distribution": {...}
    # }

    # Psychographic indicators (from research data)
    psychographics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #   "political_leaning": {"liberal": 0.4, "moderate": 0.35, "conservative": 0.25},
    #   "technology_adoption": {"innovator": 0.05, ...},
    #   "values_orientation": {...}
    # }

    # Behavioral patterns
    behavioral_patterns: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #   "media_consumption": {"social_media": 0.75, "tv": 0.6, ...},
    #   "shopping_preferences": {"online": 0.65, "in_store": 0.35},
    #   "brand_loyalty": {...}
    # }

    # Quality metrics
    data_completeness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    data_source = relationship("DataSource", back_populates="regional_profiles")

    def __repr__(self) -> str:
        return f"<RegionalProfile {self.region_name} ({self.region_type})>"


class ValidationResult(Base):
    """
    Track validation of simulation predictions against real-world outcomes.
    Essential for measuring and improving accuracy.
    """

    __tablename__ = "validation_results"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Reference to simulation
    simulation_run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )

    # Validation context
    validation_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # election, survey, product_launch, market_research

    # Prediction vs Reality
    predicted_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    actual_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Accuracy metrics
    correlation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    margin_of_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_interval: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Detailed analysis
    analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #   "demographic_accuracy": {"age": 0.92, "gender": 0.98, ...},
    #   "prediction_breakdown": {...},
    #   "error_analysis": {...}
    # }

    # External validation source
    validation_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    validation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, validated, inconclusive

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ValidationResult {self.validation_type} ({self.status})>"
