"""
Advanced Persona Models
Comprehensive persona system with 100+ nuanced traits for realistic simulation.
Supports multi-region data and topic-aware generation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PersonaSourceType(str, Enum):
    """How the persona was created."""
    AI_GENERATED = "ai_generated"  # Auto-generated from real data
    MANUAL_UPLOAD = "manual_upload"  # Uploaded via CSV/Excel
    AI_RESEARCHED = "ai_researched"  # AI researched based on topic
    HYBRID = "hybrid"  # Combination of sources


class RegionType(str, Enum):
    """Geographic regions supported."""
    US = "us"
    EUROPE = "europe"
    SOUTHEAST_ASIA = "southeast_asia"
    CHINA = "china"
    GLOBAL = "global"
    CUSTOM = "custom"


class PersonaTemplate(Base):
    """
    Persona template for a specific market/topic combination.
    Defines the structure and attributes for generating personas.
    """

    __tablename__ = "persona_templates"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Template identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Market configuration
    region: Mapped[str] = mapped_column(String(50), nullable=False)  # us, europe, southeast_asia, china, global
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Specific country
    sub_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # State/Province/City

    # Topic/Industry configuration
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Source configuration
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ai_generated, manual_upload, ai_researched
    data_sources: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # List of data source IDs used

    # Attribute configuration (which attributes to include)
    demographic_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    psychographic_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    behavioral_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    professional_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cultural_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Distribution settings
    distributions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #   "age": {"18-24": 0.15, "25-34": 0.25, ...},
    #   "income": {...},
    #   "education": {...},
    #   ...
    # }

    # Quality metrics
    data_completeness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    validation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Share with other users

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    personas = relationship("PersonaRecord", back_populates="template", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PersonaTemplate {self.name} ({self.region})>"


class PersonaRecord(Base):
    """
    Individual persona record with comprehensive attributes.
    Over 100 nuanced traits for realistic simulation.
    """

    __tablename__ = "persona_records"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_templates.id", ondelete="SET NULL"), nullable=True
    )

    # ============= DEMOGRAPHICS (20+ attributes) =============
    demographics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure:
    # {
    #   "age": 35,
    #   "age_bracket": "35-44",
    #   "gender": "Female",
    #   "gender_identity": "Cisgender",
    #   "ethnicity": "Asian",
    #   "nationality": "Singaporean",
    #   "country": "Singapore",
    #   "region": "Southeast Asia",
    #   "city": "Singapore",
    #   "urban_rural": "Urban",
    #   "marital_status": "Married",
    #   "household_size": 4,
    #   "children": 2,
    #   "children_ages": [8, 12],
    #   "housing_type": "Condominium",
    #   "housing_ownership": "Owner",
    #   "income_personal": "$75,000 - $100,000",
    #   "income_household": "$150,000 - $200,000",
    #   "wealth_bracket": "Upper Middle Class",
    #   "language_primary": "English",
    #   "languages_spoken": ["English", "Mandarin", "Malay"],
    #   "religion": "Buddhist",
    #   "generation": "Millennial"
    # }

    # ============= PROFESSIONAL BACKGROUND (20+ attributes) =============
    professional: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure:
    # {
    #   "employment_status": "Full-time",
    #   "occupation": "Marketing Manager",
    #   "industry": "Technology",
    #   "company_size": "Enterprise (1000+)",
    #   "seniority_level": "Senior",
    #   "years_experience": 12,
    #   "education_level": "Master's Degree",
    #   "education_field": "Business Administration",
    #   "university": "National University of Singapore",
    #   "certifications": ["Google Analytics", "PMP"],
    #   "skills": ["Digital Marketing", "Team Leadership", "Data Analysis"],
    #   "career_stage": "Mid-Career",
    #   "job_satisfaction": 7,
    #   "career_ambition": "Executive Leadership",
    #   "work_style": "Collaborative",
    #   "remote_work_preference": "Hybrid",
    #   "commute_method": "Public Transit",
    #   "professional_network_size": "500+",
    #   "industry_involvement": ["Conference Speaker", "Industry Association Member"],
    #   "entrepreneurial_experience": false
    # }

    # ============= PSYCHOGRAPHICS (30+ attributes) =============
    psychographics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure:
    # {
    #   "values_primary": ["Family", "Career Success", "Health"],
    #   "values_orientation": "Progressive",
    #   "personality_type": "ENTJ",
    #   "big_five": {
    #     "openness": 0.75,
    #     "conscientiousness": 0.85,
    #     "extraversion": 0.65,
    #     "agreeableness": 0.70,
    #     "neuroticism": 0.35
    #   },
    #   "risk_tolerance": 7,
    #   "change_readiness": 8,
    #   "innovation_adoption": "Early Adopter",
    #   "decision_style": "Analytical",
    #   "information_processing": "Detail-oriented",
    #   "social_influence_susceptibility": 5,
    #   "brand_loyalty_tendency": "Moderate",
    #   "price_sensitivity": 4,
    #   "quality_consciousness": 8,
    #   "status_seeking": 6,
    #   "environmental_consciousness": 7,
    #   "health_consciousness": 8,
    #   "time_orientation": "Future-focused",
    #   "locus_of_control": "Internal",
    #   "achievement_motivation": 9,
    #   "need_for_uniqueness": 6,
    #   "nostalgia_proneness": 4,
    #   "impulsivity": 3,
    #   "materialism": 5,
    #   "life_satisfaction": 7,
    #   "stress_level": 5,
    #   "optimism": 7,
    #   "trust_in_institutions": 6,
    #   "political_orientation": "Center-Left",
    #   "religiosity": 5
    # }

    # ============= BEHAVIORAL PATTERNS (25+ attributes) =============
    behavioral: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure:
    # {
    #   "media_consumption": {
    #     "social_media_hours_daily": 2.5,
    #     "platforms": ["LinkedIn", "Instagram", "TikTok"],
    #     "content_preferences": ["Business News", "Lifestyle", "Tech Reviews"],
    #     "news_sources": ["CNA", "Bloomberg", "TechCrunch"],
    #     "streaming_services": ["Netflix", "Disney+"],
    #     "podcast_listener": true,
    #     "podcast_genres": ["Business", "True Crime"]
    #   },
    #   "shopping_behavior": {
    #     "online_vs_offline": 0.7,
    #     "research_before_purchase": true,
    #     "review_dependency": 8,
    #     "brand_discovery": ["Social Media", "Word of Mouth"],
    #     "payment_preferences": ["Credit Card", "Mobile Payment"],
    #     "subscription_services": ["Amazon Prime", "Spotify"],
    #     "impulse_purchase_frequency": "Occasional"
    #   },
    #   "technology_usage": {
    #     "devices": ["iPhone", "MacBook", "iPad"],
    #     "primary_device": "Smartphone",
    #     "tech_savviness": 8,
    #     "app_usage_daily": 4,
    #     "smart_home_adoption": true,
    #     "wearables": ["Apple Watch"],
    #     "ai_tool_usage": ["ChatGPT", "Copilot"]
    #   },
    #   "financial_behavior": {
    #     "savings_rate": 0.25,
    #     "investment_active": true,
    #     "investment_types": ["Stocks", "ETFs", "Real Estate"],
    #     "credit_usage": "Moderate",
    #     "financial_planning": "Structured",
    #     "insurance_coverage": ["Health", "Life", "Home"]
    #   },
    #   "health_behavior": {
    #     "exercise_frequency": "4x/week",
    #     "diet_type": "Balanced",
    #     "sleep_hours": 7,
    #     "wellness_apps": ["Calm", "MyFitnessPal"],
    #     "preventive_care": true
    #   },
    #   "social_behavior": {
    #     "social_circle_size": "Medium (20-50)",
    #     "networking_frequency": "Monthly",
    #     "community_involvement": ["Parent Association", "Industry Groups"],
    #     "volunteering": "Occasional"
    #   }
    # }

    # ============= INTERESTS & LIFESTYLE (15+ attributes) =============
    interests: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure:
    # {
    #   "hobbies": ["Travel", "Reading", "Cooking", "Yoga"],
    #   "sports": ["Swimming", "Tennis"],
    #   "entertainment": ["Movies", "Concerts", "Theatre"],
    #   "travel_frequency": "4-6 trips/year",
    #   "travel_style": "Luxury/Comfort",
    #   "travel_destinations": ["Japan", "Europe", "Maldives"],
    #   "food_preferences": ["Asian Fusion", "Mediterranean"],
    #   "dining_frequency": "2-3x/week",
    #   "fashion_style": "Business Casual",
    #   "fashion_spending": "Above Average",
    #   "automotive": "Electric SUV",
    #   "pet_ownership": ["Dog"],
    #   "gardening": false,
    #   "art_collector": false,
    #   "philanthropy_causes": ["Education", "Environment"]
    # }

    # ============= TOPIC-SPECIFIC KNOWLEDGE (Dynamic) =============
    topic_knowledge: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure varies by topic:
    # For "smartphone purchase":
    # {
    #   "current_phone": "iPhone 14 Pro",
    #   "brand_preference": "Apple",
    #   "upgrade_cycle": "2 years",
    #   "important_features": ["Camera", "Battery", "Performance"],
    #   "price_willing_to_pay": "$1000-1500",
    #   "carrier": "Singtel",
    #   "phone_usage_primary": "Work and Personal",
    #   "previous_brands": ["Samsung", "Apple"],
    #   "awareness_level": "Expert"
    # }

    # ============= CULTURAL CONTEXT =============
    cultural_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #   "cultural_values": ["Collectivism", "Hierarchy Respect", "Face-saving"],
    #   "communication_style": "High-context",
    #   "gift_giving_customs": true,
    #   "holiday_celebrations": ["Chinese New Year", "Deepavali", "Christmas"],
    #   "superstitions": ["Lucky numbers: 8", "Avoid 4"],
    #   "food_taboos": [],
    #   "negotiation_style": "Relationship-first",
    #   "formality_preference": "Moderate",
    #   "punctuality_expectation": "Strict",
    #   "personal_space": "Moderate"
    # }

    # ============= METADATA =============
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ai_generated, manual_upload, ai_researched
    data_sources: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    generation_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Topic, market, etc.

    # Full prompt for LLM
    full_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    template = relationship("PersonaTemplate", back_populates="personas")

    def __repr__(self) -> str:
        return f"<PersonaRecord {self.id}>"


class PersonaUpload(Base):
    """
    Track persona uploads from CSV/Excel files.
    """

    __tablename__ = "persona_uploads"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_templates.id", ondelete="SET NULL"), nullable=True
    )

    # File information
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # csv, xlsx
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, processing, completed, failed
    records_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Mapping configuration (column to attribute mapping)
    column_mapping: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Errors
    errors: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<PersonaUpload {self.file_name} ({self.status})>"


class AIResearchJob(Base):
    """
    Track AI research jobs for automatic persona data gathering.
    """

    __tablename__ = "ai_research_jobs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Research configuration
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Research parameters
    research_depth: Mapped[str] = mapped_column(
        String(50), default="standard", nullable=False
    )  # quick, standard, comprehensive
    data_sources_to_use: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    target_persona_count: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, researching, generating, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Results
    sources_found: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    demographics_discovered: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    insights: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    personas_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<AIResearchJob {self.topic} ({self.status})>"


# =============================================================================
# STEP 3: PersonaSnapshot Model (Immutable Persona Set for Runs)
# =============================================================================

class PersonaSnapshot(Base):
    """
    STEP 3: Immutable snapshot of personas used for a simulation run.

    Requirements:
    - Created when a Run is created
    - IMMUTABLE after creation
    - Contains complete persona data (not just references)
    - Has unique personas_snapshot_id
    - Referenced by RunSpec

    This ensures runs always use the exact same personas,
    regardless of any future modifications to the source personas.
    """

    __tablename__ = "persona_snapshots"

    # Identity
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_specs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Source reference (which template/set was snapshotted)
    source_template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Snapshot metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Total population size
    total_personas: Mapped[int] = mapped_column(Integer, nullable=False)

    # Segment summary (STEP 3 requirement: explicit weights/proportions)
    # Structure:
    # {
    #   "segments": [
    #     {"name": "Young Professionals", "count": 30, "weight": 0.30, "criteria": {...}},
    #     {"name": "Seniors", "count": 20, "weight": 0.20, "criteria": {...}},
    #     ...
    #   ],
    #   "demographics_summary": {
    #     "age_distribution": {"18-24": 0.15, "25-34": 0.25, ...},
    #     "gender_distribution": {"Male": 0.48, "Female": 0.52},
    #     ...
    #   }
    # }
    segment_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Full persona data (immutable copy)
    # Structure: list of complete persona objects
    personas_data: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Hash of persona data for integrity verification
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Validation report reference (STEP 3 requirement)
    validation_report_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_validation_reports.id", ondelete="SET NULL", use_alter=True), nullable=True
    )

    # Confidence/quality metrics
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    data_completeness: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Immutability marker (set to True after first run uses it)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<PersonaSnapshot {self.id} total={self.total_personas}>"

    def to_dict(self) -> dict:
        """Return dictionary representation for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "project_id": str(self.project_id),
            "source_template_id": str(self.source_template_id) if self.source_template_id else None,
            "name": self.name,
            "description": self.description,
            "total_personas": self.total_personas,
            "segment_summary": self.segment_summary,
            "data_hash": self.data_hash,
            "confidence_score": self.confidence_score,
            "data_completeness": self.data_completeness,
            "is_locked": self.is_locked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# STEP 3: PersonaValidationReport Model
# =============================================================================

class PersonaValidationReport(Base):
    """
    STEP 3: Validation report for a persona set.

    Requirements:
    - Coverage gaps analysis
    - Duplication rate
    - Bias risk assessment
    - Uncertainty warnings
    - Stored in database
    - Referenced in confidence/reliability calculations
    """

    __tablename__ = "persona_validation_reports"

    # Identity
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Source reference
    snapshot_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Validation status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, passed, failed, warning

    # Overall validation score (0-100)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Coverage gaps analysis (STEP 3 requirement)
    # Structure:
    # {
    #   "gaps": [
    #     {"dimension": "age", "missing_segment": "65+", "severity": "high"},
    #     {"dimension": "income", "missing_segment": "Under $25k", "severity": "medium"},
    #   ],
    #   "coverage_score": 0.85
    # }
    coverage_gaps: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Duplication rate (STEP 3 requirement)
    # Structure:
    # {
    #   "exact_duplicates": 0,
    #   "near_duplicates": 5,
    #   "duplication_rate": 0.05,
    #   "duplicate_clusters": [...]
    # }
    duplication_analysis: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Bias risk assessment (STEP 3 requirement)
    # Structure:
    # {
    #   "risks": [
    #     {"type": "gender_bias", "severity": "low", "description": "Slight over-representation of males"},
    #     {"type": "age_bias", "severity": "medium", "description": "Under-representation of 65+"},
    #   ],
    #   "bias_score": 0.78
    # }
    bias_risk: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Uncertainty warnings (STEP 3 requirement)
    # Structure:
    # {
    #   "warnings": [
    #     {"type": "small_sample", "message": "Only 50 personas - results may have high variance"},
    #     {"type": "missing_data", "message": "15% of personas missing income data"},
    #   ],
    #   "uncertainty_level": "medium"
    # }
    uncertainty_warnings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Detailed statistics
    statistics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Recommendations for improvement
    recommendations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Impact on confidence (how much to adjust simulation confidence)
    confidence_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<PersonaValidationReport {self.id} status={self.status}>"

    def to_dict(self) -> dict:
        """Return dictionary representation for API responses."""
        return {
            "id": str(self.id),
            "snapshot_id": str(self.snapshot_id) if self.snapshot_id else None,
            "template_id": str(self.template_id) if self.template_id else None,
            "status": self.status,
            "overall_score": self.overall_score,
            "coverage_gaps": self.coverage_gaps,
            "duplication_analysis": self.duplication_analysis,
            "bias_risk": self.bias_risk,
            "uncertainty_warnings": self.uncertainty_warnings,
            "statistics": self.statistics,
            "recommendations": self.recommendations,
            "confidence_impact": self.confidence_impact,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
