"""
Data Sources API Endpoints
Manage real-world data sources for persona generation.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_admin_user
from app.models.user import User
from app.models.data_source import DataSource, CensusData, RegionalProfile
from app.services.census import CensusDataService, US_STATE_FIPS
from app.core.config import settings


router = APIRouter()


# ============= Pydantic Schemas =============

class DataSourceBase(BaseModel):
    name: str
    description: Optional[str] = None
    source_type: str
    source_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    coverage_region: Optional[str] = None
    coverage_year: Optional[int] = None


class DataSourceCreate(DataSourceBase):
    config: dict[str, Any] = {}


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    coverage_region: Optional[str] = None
    coverage_year: Optional[int] = None
    config: Optional[dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class DataSourceResponse(DataSourceBase):
    id: UUID
    status: str
    is_enabled: bool
    accuracy_score: Optional[float]
    validation_status: Optional[str]
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    config: dict[str, Any]

    class Config:
        from_attributes = True


class CensusDataResponse(BaseModel):
    id: UUID
    data_source_id: UUID
    country: str
    state: Optional[str]
    county: Optional[str]
    data_category: str
    distribution: dict[str, float]
    survey_year: int
    survey_name: str
    margin_of_error: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class RegionalProfileResponse(BaseModel):
    id: UUID
    data_source_id: UUID
    region_code: str
    region_name: str
    region_type: str
    demographics: dict[str, Any]
    psychographics: Optional[dict[str, Any]]
    data_completeness: float
    confidence_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class CensusSyncRequest(BaseModel):
    state: Optional[str] = None  # State FIPS code or abbreviation
    county: Optional[str] = None  # County FIPS code
    year: int = 2022


class DemographicDistributionResponse(BaseModel):
    category: str
    distribution: dict[str, float]
    total_population: int
    source_year: int
    source_survey: str
    margin_of_error: Optional[float] = None


# ============= Data Source CRUD =============

@router.get("/", response_model=list[DataSourceResponse])
async def list_data_sources(
    skip: int = 0,
    limit: int = 100,
    source_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available data sources."""
    query = select(DataSource)

    if source_type:
        query = query.where(DataSource.source_type == source_type)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{data_source_id}", response_model=DataSourceResponse)
async def get_data_source(
    data_source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific data source."""
    result = await db.execute(
        select(DataSource).where(DataSource.id == data_source_id)
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )

    return data_source


@router.post("/", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),  # Admin only
):
    """Create a new data source (admin only)."""
    data_source = DataSource(
        name=data.name,
        description=data.description,
        source_type=data.source_type,
        source_url=data.source_url,
        api_endpoint=data.api_endpoint,
        coverage_region=data.coverage_region,
        coverage_year=data.coverage_year,
        config=data.config,
        status="pending",
    )

    db.add(data_source)
    await db.flush()
    await db.refresh(data_source)

    return data_source


@router.put("/{data_source_id}", response_model=DataSourceResponse)
async def update_data_source(
    data_source_id: UUID,
    data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update a data source (admin only)."""
    result = await db.execute(
        select(DataSource).where(DataSource.id == data_source_id)
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(data_source, field, value)

    await db.flush()
    await db.refresh(data_source)

    return data_source


@router.delete("/{data_source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    data_source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Delete a data source (admin only)."""
    result = await db.execute(
        select(DataSource).where(DataSource.id == data_source_id)
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )

    await db.delete(data_source)


# ============= Census Data Endpoints =============

@router.get("/census/states", response_model=dict[str, str])
async def get_us_states(
    current_user: User = Depends(get_current_user),
):
    """Get list of US states with FIPS codes."""
    return US_STATE_FIPS


@router.get("/census/demographics/{category}")
async def get_census_demographics(
    category: str,
    state: Optional[str] = None,
    county: Optional[str] = None,
    year: int = 2022,
    current_user: User = Depends(get_current_user),
):
    """
    Fetch real-time demographic distribution from Census Bureau.

    Categories: age, gender, income, education, occupation
    """
    valid_categories = ["age", "gender", "income", "education", "occupation"]
    if category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {valid_categories}"
        )

    # Convert state abbreviation to FIPS if needed
    state_fips = None
    if state:
        if state.upper() in US_STATE_FIPS:
            state_fips = US_STATE_FIPS[state.upper()]
        elif len(state) == 2 and state.isdigit():
            state_fips = state
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state. Use 2-letter abbreviation (e.g., 'CA') or FIPS code"
            )

    try:
        census_service = CensusDataService(api_key=settings.CENSUS_API_KEY)
        distribution = await census_service.get_demographic_distribution(
            category=category,
            state=state_fips,
            county=county,
            year=year,
        )

        return {
            "category": distribution.category,
            "distribution": distribution.distribution,
            "total_population": distribution.total_population,
            "source_year": distribution.source_year,
            "source_survey": distribution.source_survey,
            "margin_of_error": distribution.margin_of_error,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch census data: {str(e)}"
        )


@router.get("/census/profile")
async def get_census_profile(
    state: Optional[str] = None,
    county: Optional[str] = None,
    year: int = 2022,
    current_user: User = Depends(get_current_user),
):
    """
    Fetch complete demographic profile from Census Bureau.

    Returns all demographic categories for a region.
    """
    # Convert state abbreviation to FIPS if needed
    state_fips = None
    if state:
        if state.upper() in US_STATE_FIPS:
            state_fips = US_STATE_FIPS[state.upper()]
        elif len(state) == 2 and state.isdigit():
            state_fips = state
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state. Use 2-letter abbreviation (e.g., 'CA') or FIPS code"
            )

    try:
        census_service = CensusDataService(api_key=settings.CENSUS_API_KEY)
        profile = await census_service.get_full_demographic_profile(
            state=state_fips,
            county=county,
            year=year,
        )

        return {
            "region": {
                "state": state,
                "county": county,
            },
            "demographics": {
                cat: {
                    "distribution": dist.distribution,
                    "total_population": dist.total_population,
                    "source_year": dist.source_year,
                    "source_survey": dist.source_survey,
                }
                for cat, dist in profile.items()
            },
            "source": "US Census Bureau ACS 5-Year",
            "year": year,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch census profile: {str(e)}"
        )


@router.post("/census/sync")
async def sync_census_data(
    request: CensusSyncRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Sync census data to database for offline use (admin only).

    This caches census data locally for faster persona generation.
    """
    # Convert state abbreviation to FIPS if needed
    state_fips = None
    if request.state:
        if request.state.upper() in US_STATE_FIPS:
            state_fips = US_STATE_FIPS[request.state.upper()]
        else:
            state_fips = request.state

    # Find or create census data source
    result = await db.execute(
        select(DataSource).where(
            DataSource.source_type == "census",
            DataSource.name == "US Census Bureau"
        )
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        data_source = DataSource(
            name="US Census Bureau",
            description="Official US Census Bureau demographic data",
            source_type="census",
            source_url="https://api.census.gov",
            api_endpoint="https://api.census.gov/data",
            coverage_region="US",
            coverage_year=request.year,
            status="active",
        )
        db.add(data_source)
        await db.flush()

    try:
        census_service = CensusDataService(api_key=settings.CENSUS_API_KEY)

        # Sync census data
        records = await census_service.sync_census_data(
            db=db,
            data_source_id=data_source.id,
            state=state_fips,
            county=request.county,
            year=request.year,
        )

        # Update data source status
        data_source.status = "active"
        data_source.last_synced_at = datetime.utcnow()

        return {
            "message": "Census data synced successfully",
            "records_created": len(records),
            "data_source_id": str(data_source.id),
            "region": {
                "state": request.state,
                "county": request.county,
            },
            "year": request.year,
        }

    except Exception as e:
        data_source.status = "error"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync census data: {str(e)}"
        )


# ============= Regional Profile Endpoints =============

@router.get("/profiles/", response_model=list[RegionalProfileResponse])
async def list_regional_profiles(
    skip: int = 0,
    limit: int = 100,
    region_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available regional profiles."""
    query = select(RegionalProfile)

    if region_type:
        query = query.where(RegionalProfile.region_type == region_type)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/profiles/{region_code}", response_model=RegionalProfileResponse)
async def get_regional_profile(
    region_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific regional profile."""
    result = await db.execute(
        select(RegionalProfile).where(RegionalProfile.region_code == region_code)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regional profile not found"
        )

    return profile


@router.post("/profiles/build")
async def build_regional_profile(
    region_code: str,
    region_name: str,
    state: Optional[str] = None,
    county: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Build a regional profile from census data (admin only).

    Creates a comprehensive profile combining all demographic categories.
    """
    # Convert state abbreviation to FIPS if needed
    state_fips = None
    if state:
        if state.upper() in US_STATE_FIPS:
            state_fips = US_STATE_FIPS[state.upper()]
        else:
            state_fips = state

    # Find or create census data source
    result = await db.execute(
        select(DataSource).where(
            DataSource.source_type == "census",
            DataSource.name == "US Census Bureau"
        )
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        data_source = DataSource(
            name="US Census Bureau",
            description="Official US Census Bureau demographic data",
            source_type="census",
            source_url="https://api.census.gov",
            coverage_region="US",
            status="active",
        )
        db.add(data_source)
        await db.flush()

    try:
        census_service = CensusDataService(api_key=settings.CENSUS_API_KEY)

        profile = await census_service.build_regional_profile(
            db=db,
            data_source_id=data_source.id,
            region_code=region_code,
            region_name=region_name,
            state=state_fips,
            county=county,
        )

        return {
            "message": "Regional profile built successfully",
            "profile_id": str(profile.id),
            "region_code": profile.region_code,
            "region_name": profile.region_name,
            "region_type": profile.region_type,
            "data_completeness": profile.data_completeness,
            "confidence_score": profile.confidence_score,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build regional profile: {str(e)}"
        )


# ============= Cached Census Data =============

@router.get("/cached/", response_model=list[CensusDataResponse])
async def list_cached_census_data(
    skip: int = 0,
    limit: int = 100,
    data_category: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List cached census data."""
    query = select(CensusData)

    if data_category:
        query = query.where(CensusData.data_category == data_category)

    if state:
        query = query.where(CensusData.state == state)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
