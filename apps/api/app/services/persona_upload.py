"""
Persona Upload Service
Handles CSV/Excel file uploads for manual persona creation.
Supports mapping columns to persona attributes.
"""

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from uuid import UUID, uuid4

import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.persona import (
    PersonaTemplate,
    PersonaRecord,
    PersonaUpload,
    PersonaSourceType,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============= Schema Models =============

class ColumnMapping(BaseModel):
    """Mapping between file columns and persona attributes."""
    # Demographics
    age: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    income: Optional[str] = None
    education: Optional[str] = None
    marital_status: Optional[str] = None
    household_size: Optional[str] = None
    ethnicity: Optional[str] = None

    # Professional
    occupation: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    years_experience: Optional[str] = None
    employment_status: Optional[str] = None

    # Psychographics
    personality_type: Optional[str] = None
    values: Optional[str] = None
    risk_tolerance: Optional[str] = None
    brand_loyalty: Optional[str] = None

    # Behavioral
    social_media_platforms: Optional[str] = None
    shopping_preference: Optional[str] = None
    tech_savviness: Optional[str] = None

    # Interests
    hobbies: Optional[str] = None
    travel_frequency: Optional[str] = None

    # Custom columns (for topic-specific)
    custom_columns: Optional[dict[str, str]] = Field(default_factory=dict)


class UploadResult(BaseModel):
    """Result of an upload operation."""
    upload_id: UUID
    status: str
    records_total: int
    records_processed: int
    records_failed: int
    errors: list[dict[str, Any]] = Field(default_factory=list)
    sample_records: list[dict[str, Any]] = Field(default_factory=list)


class ColumnInfo(BaseModel):
    """Information about a column in the uploaded file."""
    name: str
    sample_values: list[str]
    data_type: str
    unique_count: int
    null_count: int
    suggested_mapping: Optional[str] = None


class FileAnalysis(BaseModel):
    """Analysis of an uploaded file."""
    file_name: str
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    suggested_mappings: dict[str, str]


# ============= Value Normalization =============

class ValueNormalizer:
    """Normalize values from uploaded files to standard formats."""

    GENDER_MAPPINGS = {
        # Male variants
        "m": "Male", "male": "Male", "man": "Male", "boy": "Male",
        "masculine": "Male", "m.": "Male", "1": "Male",
        # Female variants
        "f": "Female", "female": "Female", "woman": "Female", "girl": "Female",
        "feminine": "Female", "f.": "Female", "2": "Female",
        # Non-binary
        "nb": "Non-binary", "non-binary": "Non-binary", "nonbinary": "Non-binary",
        "other": "Other", "prefer not to say": "Prefer not to say",
    }

    EDUCATION_MAPPINGS = {
        "high school": "High School",
        "hs": "High School",
        "secondary": "High School",
        "some college": "Some College",
        "associate": "Associate's Degree",
        "associates": "Associate's Degree",
        "bachelor": "Bachelor's Degree",
        "bachelors": "Bachelor's Degree",
        "bs": "Bachelor's Degree",
        "ba": "Bachelor's Degree",
        "undergraduate": "Bachelor's Degree",
        "master": "Master's Degree",
        "masters": "Master's Degree",
        "ms": "Master's Degree",
        "ma": "Master's Degree",
        "mba": "Master's Degree",
        "graduate": "Master's Degree",
        "phd": "Doctorate",
        "doctorate": "Doctorate",
        "doctoral": "Doctorate",
        "md": "Professional Degree",
        "jd": "Professional Degree",
    }

    EMPLOYMENT_MAPPINGS = {
        "full time": "Full-time",
        "full-time": "Full-time",
        "fulltime": "Full-time",
        "ft": "Full-time",
        "part time": "Part-time",
        "part-time": "Part-time",
        "parttime": "Part-time",
        "pt": "Part-time",
        "self employed": "Self-employed",
        "self-employed": "Self-employed",
        "freelance": "Freelance",
        "freelancer": "Freelance",
        "contractor": "Freelance",
        "unemployed": "Unemployed",
        "retired": "Retired",
        "student": "Student",
    }

    MARITAL_MAPPINGS = {
        "single": "Single",
        "never married": "Single",
        "unmarried": "Single",
        "married": "Married",
        "in relationship": "In Relationship",
        "engaged": "Engaged",
        "divorced": "Divorced",
        "separated": "Separated",
        "widowed": "Widowed",
        "widow": "Widowed",
        "widower": "Widowed",
    }

    @classmethod
    def normalize_gender(cls, value: Any) -> str:
        if pd.isna(value):
            return "Unknown"
        normalized = cls.GENDER_MAPPINGS.get(str(value).lower().strip())
        return normalized or str(value).title()

    @classmethod
    def normalize_education(cls, value: Any) -> str:
        if pd.isna(value):
            return "Unknown"
        normalized = cls.EDUCATION_MAPPINGS.get(str(value).lower().strip())
        return normalized or str(value).title()

    @classmethod
    def normalize_employment(cls, value: Any) -> str:
        if pd.isna(value):
            return "Unknown"
        normalized = cls.EMPLOYMENT_MAPPINGS.get(str(value).lower().strip())
        return normalized or str(value).title()

    @classmethod
    def normalize_marital(cls, value: Any) -> str:
        if pd.isna(value):
            return "Unknown"
        normalized = cls.MARITAL_MAPPINGS.get(str(value).lower().strip())
        return normalized or str(value).title()

    @classmethod
    def normalize_age(cls, value: Any) -> Optional[int]:
        if pd.isna(value):
            return None
        try:
            age = int(float(value))
            return age if 0 < age < 120 else None
        except (ValueError, TypeError):
            return None

    @classmethod
    def normalize_list(cls, value: Any, delimiter: str = ",") -> list[str]:
        if pd.isna(value):
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value]
        return [v.strip() for v in str(value).split(delimiter) if v.strip()]

    @classmethod
    def normalize_numeric(cls, value: Any, min_val: float = 0, max_val: float = 10) -> Optional[float]:
        if pd.isna(value):
            return None
        try:
            num = float(value)
            return max(min_val, min(max_val, num))
        except (ValueError, TypeError):
            return None


# ============= Column Mapping Suggestions =============

class ColumnMappingSuggester:
    """Suggest column mappings based on column names and sample values."""

    COLUMN_KEYWORDS = {
        "age": ["age", "years", "old", "birth", "dob"],
        "gender": ["gender", "sex", "male", "female"],
        "country": ["country", "nation", "location"],
        "region": ["region", "state", "province", "area"],
        "city": ["city", "town", "municipality"],
        "income": ["income", "salary", "earnings", "wage", "pay"],
        "education": ["education", "degree", "school", "qualification"],
        "occupation": ["occupation", "job", "role", "position", "title"],
        "industry": ["industry", "sector", "field"],
        "company_size": ["company", "organization", "size", "employees"],
        "years_experience": ["experience", "years", "tenure"],
        "employment_status": ["employment", "status", "working"],
        "marital_status": ["marital", "married", "single", "relationship"],
        "household_size": ["household", "family", "members"],
        "ethnicity": ["ethnicity", "race", "background"],
        "personality_type": ["personality", "mbti", "type"],
        "values": ["values", "priorities", "beliefs"],
        "risk_tolerance": ["risk", "tolerance", "appetite"],
        "brand_loyalty": ["brand", "loyalty", "preference"],
        "social_media_platforms": ["social", "media", "platform", "network"],
        "shopping_preference": ["shopping", "purchase", "buying"],
        "tech_savviness": ["tech", "technology", "digital"],
        "hobbies": ["hobbies", "interests", "activities"],
        "travel_frequency": ["travel", "trips", "vacation"],
    }

    @classmethod
    def suggest_mappings(cls, columns: list[str], df: pd.DataFrame) -> dict[str, str]:
        """Suggest mappings for each attribute based on column names."""
        suggestions = {}

        for attr, keywords in cls.COLUMN_KEYWORDS.items():
            for col in columns:
                col_lower = col.lower()
                for keyword in keywords:
                    if keyword in col_lower:
                        if attr not in suggestions:
                            suggestions[attr] = col
                        break

        return suggestions

    @classmethod
    def analyze_column(cls, col_name: str, series: pd.Series) -> ColumnInfo:
        """Analyze a column and provide information."""
        sample_values = series.dropna().head(5).astype(str).tolist()

        # Determine data type
        if pd.api.types.is_numeric_dtype(series):
            data_type = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            data_type = "datetime"
        else:
            data_type = "text"

        # Suggest mapping
        suggested = None
        col_lower = col_name.lower()
        for attr, keywords in cls.COLUMN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in col_lower:
                    suggested = attr
                    break
            if suggested:
                break

        return ColumnInfo(
            name=col_name,
            sample_values=sample_values,
            data_type=data_type,
            unique_count=series.nunique(),
            null_count=int(series.isna().sum()),
            suggested_mapping=suggested,
        )


# ============= File Parser =============

class PersonaFileParser:
    """Parse CSV/Excel files and convert to persona records."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

    @classmethod
    def parse_file(cls, file_content: bytes, file_name: str) -> pd.DataFrame:
        """Parse file content into a DataFrame."""
        ext = Path(file_name).suffix.lower()

        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {cls.SUPPORTED_EXTENSIONS}")

        if ext == ".csv":
            # Try different encodings
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    return pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError("Could not decode CSV file with any supported encoding")
        else:
            return pd.read_excel(io.BytesIO(file_content))

    @classmethod
    def analyze_file(cls, file_content: bytes, file_name: str) -> FileAnalysis:
        """Analyze an uploaded file and provide mapping suggestions."""
        df = cls.parse_file(file_content, file_name)

        columns_info = [
            ColumnMappingSuggester.analyze_column(col, df[col])
            for col in df.columns
        ]

        suggested_mappings = ColumnMappingSuggester.suggest_mappings(
            list(df.columns), df
        )

        return FileAnalysis(
            file_name=file_name,
            row_count=len(df),
            column_count=len(df.columns),
            columns=columns_info,
            suggested_mappings=suggested_mappings,
        )

    @classmethod
    def parse_to_personas(
        cls,
        file_content: bytes,
        file_name: str,
        mapping: ColumnMapping
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Parse file and convert to persona dictionaries."""
        df = cls.parse_file(file_content, file_name)

        personas = []
        errors = []

        for idx, row in df.iterrows():
            try:
                persona = cls._row_to_persona(row, mapping)
                personas.append(persona)
            except Exception as e:
                errors.append({
                    "row": idx + 2,  # +2 for header and 0-indexing
                    "error": str(e),
                    "data": row.to_dict()
                })

        return personas, errors

    @classmethod
    def _row_to_persona(cls, row: pd.Series, mapping: ColumnMapping) -> dict[str, Any]:
        """Convert a row to persona attributes."""
        normalizer = ValueNormalizer()

        demographics = {}
        professional = {}
        psychographics = {}
        behavioral = {}
        interests = {}

        # Demographics
        if mapping.age:
            demographics["age"] = normalizer.normalize_age(row.get(mapping.age))
        if mapping.gender:
            demographics["gender"] = normalizer.normalize_gender(row.get(mapping.gender))
        if mapping.country:
            demographics["country"] = str(row.get(mapping.country, "")).strip()
        if mapping.region:
            demographics["region"] = str(row.get(mapping.region, "")).strip()
        if mapping.city:
            demographics["city"] = str(row.get(mapping.city, "")).strip()
        if mapping.income:
            demographics["income_bracket"] = str(row.get(mapping.income, "")).strip()
        if mapping.education:
            demographics["education_level"] = normalizer.normalize_education(row.get(mapping.education))
        if mapping.marital_status:
            demographics["marital_status"] = normalizer.normalize_marital(row.get(mapping.marital_status))
        if mapping.household_size:
            demographics["household_size"] = normalizer.normalize_age(row.get(mapping.household_size))  # Reuse age normalizer
        if mapping.ethnicity:
            demographics["ethnicity"] = str(row.get(mapping.ethnicity, "")).strip()

        # Professional
        if mapping.occupation:
            professional["occupation"] = str(row.get(mapping.occupation, "")).strip()
        if mapping.industry:
            professional["industry"] = str(row.get(mapping.industry, "")).strip()
        if mapping.company_size:
            professional["company_size"] = str(row.get(mapping.company_size, "")).strip()
        if mapping.years_experience:
            professional["years_experience"] = normalizer.normalize_age(row.get(mapping.years_experience))
        if mapping.employment_status:
            professional["employment_status"] = normalizer.normalize_employment(row.get(mapping.employment_status))

        # Psychographics
        if mapping.personality_type:
            psychographics["personality_type"] = str(row.get(mapping.personality_type, "")).strip()
        if mapping.values:
            psychographics["values_primary"] = normalizer.normalize_list(row.get(mapping.values))
        if mapping.risk_tolerance:
            psychographics["risk_tolerance"] = normalizer.normalize_numeric(row.get(mapping.risk_tolerance))
        if mapping.brand_loyalty:
            psychographics["brand_loyalty_tendency"] = str(row.get(mapping.brand_loyalty, "")).strip()

        # Behavioral
        if mapping.social_media_platforms:
            behavioral["social_media_platforms"] = normalizer.normalize_list(row.get(mapping.social_media_platforms))
        if mapping.shopping_preference:
            behavioral["shopping_preference"] = str(row.get(mapping.shopping_preference, "")).strip()
        if mapping.tech_savviness:
            behavioral["tech_savviness"] = normalizer.normalize_numeric(row.get(mapping.tech_savviness))

        # Interests
        if mapping.hobbies:
            interests["hobbies"] = normalizer.normalize_list(row.get(mapping.hobbies))
        if mapping.travel_frequency:
            interests["travel_frequency"] = str(row.get(mapping.travel_frequency, "")).strip()

        # Custom columns
        topic_knowledge = {}
        if mapping.custom_columns:
            for attr_name, col_name in mapping.custom_columns.items():
                if col_name in row.index:
                    topic_knowledge[attr_name] = str(row.get(col_name, "")).strip()

        return {
            "demographics": demographics,
            "professional": professional,
            "psychographics": psychographics,
            "behavioral": {"patterns": behavioral},
            "interests": interests,
            "topic_knowledge": topic_knowledge if topic_knowledge else None,
        }


# ============= Upload Service =============

class PersonaUploadService:
    """Service for handling persona file uploads."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_upload_record(
        self,
        user_id: UUID,
        file_name: str,
        file_type: str,
        file_size: int,
        template_id: Optional[UUID] = None,
    ) -> PersonaUpload:
        """Create an upload tracking record."""
        upload = PersonaUpload(
            user_id=user_id,
            template_id=template_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            status="pending",
        )
        self.db.add(upload)
        await self.db.commit()
        await self.db.refresh(upload)
        return upload

    async def analyze_upload(
        self,
        file_content: bytes,
        file_name: str
    ) -> FileAnalysis:
        """Analyze an uploaded file and return column information."""
        return PersonaFileParser.analyze_file(file_content, file_name)

    async def process_upload(
        self,
        upload_id: UUID,
        file_content: bytes,
        file_name: str,
        mapping: ColumnMapping,
        template_id: Optional[UUID] = None,
    ) -> UploadResult:
        """Process an uploaded file and create persona records."""
        # Update status to processing
        await self.db.execute(
            update(PersonaUpload)
            .where(PersonaUpload.id == upload_id)
            .values(status="processing")
        )
        await self.db.commit()

        try:
            # Parse file
            personas, errors = PersonaFileParser.parse_to_personas(
                file_content, file_name, mapping
            )

            # Create persona records
            created_records = []
            for persona_data in personas:
                record = PersonaRecord(
                    template_id=template_id,
                    demographics=persona_data["demographics"],
                    professional=persona_data["professional"],
                    psychographics=persona_data["psychographics"],
                    behavioral=persona_data["behavioral"],
                    interests=persona_data["interests"],
                    topic_knowledge=persona_data.get("topic_knowledge"),
                    source_type=PersonaSourceType.MANUAL_UPLOAD.value,
                    confidence_score=0.95,  # Manual uploads have high confidence
                )
                self.db.add(record)
                created_records.append(record)

            await self.db.commit()

            # Update upload record
            await self.db.execute(
                update(PersonaUpload)
                .where(PersonaUpload.id == upload_id)
                .values(
                    status="completed",
                    records_total=len(personas) + len(errors),
                    records_processed=len(personas),
                    records_failed=len(errors),
                    column_mapping=mapping.model_dump(),
                    errors=errors[:100] if errors else None,  # Store first 100 errors
                    completed_at=datetime.utcnow(),
                )
            )
            await self.db.commit()

            return UploadResult(
                upload_id=upload_id,
                status="completed",
                records_total=len(personas) + len(errors),
                records_processed=len(personas),
                records_failed=len(errors),
                errors=errors[:10],  # Return first 10 errors
                sample_records=[p for p in personas[:5]],  # Return first 5 records as sample
            )

        except Exception as e:
            logger.error(f"Upload processing failed: {e}")
            await self.db.execute(
                update(PersonaUpload)
                .where(PersonaUpload.id == upload_id)
                .values(
                    status="failed",
                    errors=[{"error": str(e)}],
                )
            )
            await self.db.commit()
            raise

    async def get_upload(self, upload_id: UUID) -> Optional[PersonaUpload]:
        """Get an upload record by ID."""
        result = await self.db.execute(
            select(PersonaUpload).where(PersonaUpload.id == upload_id)
        )
        return result.scalar_one_or_none()

    async def list_uploads(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> list[PersonaUpload]:
        """List uploads for a user."""
        result = await self.db.execute(
            select(PersonaUpload)
            .where(PersonaUpload.user_id == user_id)
            .order_by(PersonaUpload.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


# ============= Template Generator =============

def generate_upload_template() -> bytes:
    """Generate a CSV template for persona uploads."""
    template_data = {
        "age": [25, 35, 45, 55],
        "gender": ["Male", "Female", "Male", "Female"],
        "country": ["USA", "USA", "UK", "Germany"],
        "region": ["California", "New York", "London", "Berlin"],
        "income": ["$50,000-$75,000", "$75,000-$100,000", "£40,000-£60,000", "€45,000-€65,000"],
        "education": ["Bachelor's", "Master's", "Bachelor's", "Doctorate"],
        "occupation": ["Software Engineer", "Marketing Manager", "Data Analyst", "Research Scientist"],
        "industry": ["Technology", "Marketing", "Finance", "Biotech"],
        "employment_status": ["Full-time", "Full-time", "Full-time", "Full-time"],
        "marital_status": ["Single", "Married", "Single", "Married"],
        "household_size": [1, 4, 2, 3],
        "hobbies": ["Gaming, Reading", "Travel, Cooking", "Music, Hiking", "Art, Tennis"],
        "tech_savviness": [9, 7, 8, 6],
        "risk_tolerance": [7, 5, 6, 4],
    }

    df = pd.DataFrame(template_data)
    output = io.BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()
