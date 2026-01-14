"""
Census Data Service
Integrates with US Census Bureau API and other official data sources.
Provides real demographic distributions for persona generation.

TEMPORAL ISOLATION (temporal.md §5):
- All external data access routes through DataGateway when in backtest mode
- DataGateway enforces cutoff timestamps via LeakageGuard
- Per-request manifest entries generated with payload hashes
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import httpx
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import CensusData, DataSource, RegionalProfile
from app.services.data_gateway import (
    DataGateway,
    DataGatewayContext,
    DataGatewayResponse,
    SourceBlockedError,
)


logger = logging.getLogger(__name__)


# Census Bureau API Constants
CENSUS_API_BASE = "https://api.census.gov/data"
ACS_5_YEAR = "acs/acs5"
LATEST_ACS_YEAR = 2022  # Most recent complete ACS 5-year data

# Source identifier for DataGateway
CENSUS_SOURCE_NAME = "census_bureau"


class CensusVariable(BaseModel):
    """Census variable mapping."""
    variable_id: str
    label: str
    category: str
    value: Optional[int] = None


class DemographicDistribution(BaseModel):
    """Processed demographic distribution."""
    category: str
    distribution: dict[str, float]
    total_population: int
    margin_of_error: Optional[float] = None
    source_year: int
    source_survey: str
    # Temporal isolation metadata
    payload_hash: Optional[str] = None
    manifest_entry_id: Optional[str] = None


# Census Variable Mappings
# Reference: https://api.census.gov/data/2022/acs/acs5/variables.html

AGE_VARIABLES = {
    # Male age groups
    "B01001_003E": "Under 5 years (Male)",
    "B01001_004E": "5 to 9 years (Male)",
    "B01001_005E": "10 to 14 years (Male)",
    "B01001_006E": "15 to 17 years (Male)",
    "B01001_007E": "18 and 19 years (Male)",
    "B01001_008E": "20 years (Male)",
    "B01001_009E": "21 years (Male)",
    "B01001_010E": "22 to 24 years (Male)",
    "B01001_011E": "25 to 29 years (Male)",
    "B01001_012E": "30 to 34 years (Male)",
    "B01001_013E": "35 to 39 years (Male)",
    "B01001_014E": "40 to 44 years (Male)",
    "B01001_015E": "45 to 49 years (Male)",
    "B01001_016E": "50 to 54 years (Male)",
    "B01001_017E": "55 to 59 years (Male)",
    "B01001_018E": "60 and 61 years (Male)",
    "B01001_019E": "62 to 64 years (Male)",
    "B01001_020E": "65 and 66 years (Male)",
    "B01001_021E": "67 to 69 years (Male)",
    "B01001_022E": "70 to 74 years (Male)",
    "B01001_023E": "75 to 79 years (Male)",
    "B01001_024E": "80 to 84 years (Male)",
    "B01001_025E": "85 years and over (Male)",
    # Female age groups
    "B01001_027E": "Under 5 years (Female)",
    "B01001_028E": "5 to 9 years (Female)",
    "B01001_029E": "10 to 14 years (Female)",
    "B01001_030E": "15 to 17 years (Female)",
    "B01001_031E": "18 and 19 years (Female)",
    "B01001_032E": "20 years (Female)",
    "B01001_033E": "21 years (Female)",
    "B01001_034E": "22 to 24 years (Female)",
    "B01001_035E": "25 to 29 years (Female)",
    "B01001_036E": "30 to 34 years (Female)",
    "B01001_037E": "35 to 39 years (Female)",
    "B01001_038E": "40 to 44 years (Female)",
    "B01001_039E": "45 to 49 years (Female)",
    "B01001_040E": "50 to 54 years (Female)",
    "B01001_041E": "55 to 59 years (Female)",
    "B01001_042E": "60 and 61 years (Female)",
    "B01001_043E": "62 to 64 years (Female)",
    "B01001_044E": "65 and 66 years (Female)",
    "B01001_045E": "67 to 69 years (Female)",
    "B01001_046E": "70 to 74 years (Female)",
    "B01001_047E": "75 to 79 years (Female)",
    "B01001_048E": "80 to 84 years (Female)",
    "B01001_049E": "85 years and over (Female)",
}

GENDER_VARIABLES = {
    "B01001_002E": "Male",
    "B01001_026E": "Female",
}

INCOME_VARIABLES = {
    "B19001_002E": "Less than $10,000",
    "B19001_003E": "$10,000 to $14,999",
    "B19001_004E": "$15,000 to $19,999",
    "B19001_005E": "$20,000 to $24,999",
    "B19001_006E": "$25,000 to $29,999",
    "B19001_007E": "$30,000 to $34,999",
    "B19001_008E": "$35,000 to $39,999",
    "B19001_009E": "$40,000 to $44,999",
    "B19001_010E": "$45,000 to $49,999",
    "B19001_011E": "$50,000 to $59,999",
    "B19001_012E": "$60,000 to $74,999",
    "B19001_013E": "$75,000 to $99,999",
    "B19001_014E": "$100,000 to $124,999",
    "B19001_015E": "$125,000 to $149,999",
    "B19001_016E": "$150,000 to $199,999",
    "B19001_017E": "$200,000 or more",
}

EDUCATION_VARIABLES = {
    "B15003_002E": "No schooling completed",
    "B15003_003E": "Nursery school",
    "B15003_004E": "Kindergarten",
    "B15003_005E": "1st grade",
    "B15003_006E": "2nd grade",
    "B15003_007E": "3rd grade",
    "B15003_008E": "4th grade",
    "B15003_009E": "5th grade",
    "B15003_010E": "6th grade",
    "B15003_011E": "7th grade",
    "B15003_012E": "8th grade",
    "B15003_013E": "9th grade",
    "B15003_014E": "10th grade",
    "B15003_015E": "11th grade",
    "B15003_016E": "12th grade, no diploma",
    "B15003_017E": "Regular high school diploma",
    "B15003_018E": "GED or alternative credential",
    "B15003_019E": "Some college, less than 1 year",
    "B15003_020E": "Some college, 1 or more years, no degree",
    "B15003_021E": "Associate's degree",
    "B15003_022E": "Bachelor's degree",
    "B15003_023E": "Master's degree",
    "B15003_024E": "Professional school degree",
    "B15003_025E": "Doctorate degree",
}

OCCUPATION_VARIABLES = {
    "C24010_003E": "Management, business, science, and arts occupations",
    "C24010_019E": "Service occupations",
    "C24010_027E": "Sales and office occupations",
    "C24010_034E": "Natural resources, construction, and maintenance occupations",
    "C24010_038E": "Production, transportation, and material moving occupations",
}


class CensusDataService:
    """
    Service for fetching and processing census data from official sources.

    Supports two modes:
    1. Direct mode: Fetches data directly via httpx (for live/non-backtest)
    2. DataGateway mode: Routes through DataGateway with temporal isolation (for backtest)

    In DataGateway mode:
    - Source capability is checked before requests
    - Cutoff timestamps are enforced via LeakageGuard
    - Manifest entries are generated with payload hashes
    - Requests are auditable and reproducible
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        data_gateway: Optional[DataGateway] = None,
        gateway_context: Optional[DataGatewayContext] = None,
    ):
        """
        Initialize the Census Data Service.

        Args:
            api_key: Optional Census Bureau API key (increases rate limits)
            data_gateway: Optional DataGateway for temporal isolation
            gateway_context: Optional context for DataGateway requests
        """
        self.api_key = api_key
        self.base_url = CENSUS_API_BASE
        self.timeout = httpx.Timeout(30.0)
        self.data_gateway = data_gateway
        self.gateway_context = gateway_context

    def with_gateway(
        self,
        data_gateway: DataGateway,
        gateway_context: DataGatewayContext,
    ) -> "CensusDataService":
        """
        Return a new CensusDataService configured with DataGateway.

        Args:
            data_gateway: DataGateway instance
            gateway_context: Context for DataGateway requests

        Returns:
            New CensusDataService with DataGateway configured
        """
        return CensusDataService(
            api_key=self.api_key,
            data_gateway=data_gateway,
            gateway_context=gateway_context,
        )

    def _is_gateway_mode(self) -> bool:
        """Check if DataGateway mode is enabled."""
        return self.data_gateway is not None and self.gateway_context is not None

    async def _fetch_direct(
        self,
        url: str,
        params: dict[str, Any],
    ) -> Any:
        """
        Fetch data directly via httpx (non-DataGateway mode).
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def fetch_census_data(
        self,
        variables: list[str],
        year: int = LATEST_ACS_YEAR,
        state: Optional[str] = None,
        county: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fetch data from Census Bureau API.

        Routes through DataGateway if configured (for temporal isolation).

        Args:
            variables: List of census variable IDs
            year: Survey year
            state: State FIPS code (optional)
            county: County FIPS code (optional, requires state)

        Returns:
            Raw census data response (with optional metadata in gateway mode)

        Raises:
            SourceBlockedError: If source is blocked at current isolation level
        """
        # Build the API URL
        url = f"{self.base_url}/{year}/{ACS_5_YEAR}"

        # Build geography parameter
        if county and state:
            geo = f"county:{county}&in=state:{state}"
        elif state:
            geo = f"state:{state}"
        else:
            geo = "us:*"

        # Build query parameters
        params = {
            "get": ",".join(["NAME"] + variables),
            "for": geo,
        }

        if self.api_key:
            params["key"] = self.api_key

        # Route through DataGateway if configured
        if self._is_gateway_mode():
            return await self._fetch_via_gateway(
                endpoint=f"/{year}/{ACS_5_YEAR}",
                params={
                    "variables": variables,
                    "year": year,
                    "state": state,
                    "county": county,
                    "geo": geo,
                },
                url=url,
                raw_params=params,
            )

        # Direct fetch mode
        try:
            return await self._fetch_direct(url, params)
        except httpx.HTTPError as e:
            logger.error(f"Census API error: {e}")
            raise

    async def _fetch_via_gateway(
        self,
        endpoint: str,
        params: dict[str, Any],
        url: str,
        raw_params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Fetch census data through DataGateway with temporal isolation.

        Args:
            endpoint: Logical endpoint identifier
            params: Normalized params for manifest
            url: Actual Census API URL
            raw_params: Raw query parameters

        Returns:
            Census data with gateway metadata

        Raises:
            SourceBlockedError: If source is blocked at isolation level
        """
        # Define the actual data fetcher
        async def data_fetcher():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=raw_params)
                response.raise_for_status()
                return response.json()

        # Route through DataGateway
        gateway_response: DataGatewayResponse = await self.data_gateway.request(
            source_name=CENSUS_SOURCE_NAME,
            endpoint=endpoint,
            params=params,
            context=self.gateway_context,
            data_fetcher=data_fetcher,
            timestamp_field="year",  # Census data keyed by year
        )

        logger.info(
            f"CENSUS via DataGateway: endpoint={endpoint} "
            f"records={gateway_response.record_count} "
            f"hash={gateway_response.payload_hash[:16]}..."
        )

        # Return raw data (metadata accessible via gateway)
        return gateway_response.data

    def _aggregate_age_groups(self, raw_data: dict[str, int]) -> dict[str, float]:
        """
        Aggregate detailed age groups into broader categories.
        """
        # Map detailed census variables to age ranges
        age_brackets = {
            "18-24": 0,
            "25-34": 0,
            "35-44": 0,
            "45-54": 0,
            "55-64": 0,
            "65+": 0,
        }

        # Age mapping for both male and female
        age_mapping = {
            "18-24": ["007", "008", "009", "010", "031", "032", "033", "034"],  # 18-24
            "25-34": ["011", "012", "035", "036"],  # 25-34
            "35-44": ["013", "014", "037", "038"],  # 35-44
            "45-54": ["015", "016", "039", "040"],  # 45-54
            "55-64": ["017", "018", "019", "041", "042", "043"],  # 55-64
            "65+": ["020", "021", "022", "023", "024", "025",
                    "044", "045", "046", "047", "048", "049"],  # 65+
        }

        for bracket, suffixes in age_mapping.items():
            for suffix in suffixes:
                var_key = f"B01001_{suffix}E"
                if var_key in raw_data:
                    value = raw_data[var_key]
                    if value and value != -666666666:  # Census missing data indicator
                        age_brackets[bracket] += value

        # Calculate total and convert to percentages
        total = sum(age_brackets.values())
        if total > 0:
            return {k: round(v / total, 4) for k, v in age_brackets.items()}
        return age_brackets

    def _aggregate_income_groups(self, raw_data: dict[str, int]) -> dict[str, float]:
        """
        Aggregate income into standard brackets.
        """
        income_brackets = {
            "Under $25,000": 0,
            "$25,000 - $50,000": 0,
            "$50,000 - $75,000": 0,
            "$75,000 - $100,000": 0,
            "$100,000 - $150,000": 0,
            "Over $150,000": 0,
        }

        # Map census variables to income brackets
        income_mapping = {
            "Under $25,000": ["002", "003", "004", "005"],
            "$25,000 - $50,000": ["006", "007", "008", "009", "010"],
            "$50,000 - $75,000": ["011", "012"],
            "$75,000 - $100,000": ["013"],
            "$100,000 - $150,000": ["014", "015"],
            "Over $150,000": ["016", "017"],
        }

        for bracket, suffixes in income_mapping.items():
            for suffix in suffixes:
                var_key = f"B19001_{suffix}E"
                if var_key in raw_data:
                    value = raw_data[var_key]
                    if value and value != -666666666:
                        income_brackets[bracket] += value

        total = sum(income_brackets.values())
        if total > 0:
            return {k: round(v / total, 4) for k, v in income_brackets.items()}
        return income_brackets

    def _aggregate_education_groups(self, raw_data: dict[str, int]) -> dict[str, float]:
        """
        Aggregate education levels into standard categories.
        """
        education_brackets = {
            "Less than high school": 0,
            "High school": 0,
            "Some college": 0,
            "Associate degree": 0,
            "Bachelor's degree": 0,
            "Graduate degree": 0,
        }

        # Map census variables to education levels
        education_mapping = {
            "Less than high school": ["002", "003", "004", "005", "006", "007",
                                       "008", "009", "010", "011", "012", "013",
                                       "014", "015", "016"],
            "High school": ["017", "018"],
            "Some college": ["019", "020"],
            "Associate degree": ["021"],
            "Bachelor's degree": ["022"],
            "Graduate degree": ["023", "024", "025"],
        }

        for bracket, suffixes in education_mapping.items():
            for suffix in suffixes:
                var_key = f"B15003_{suffix}E"
                if var_key in raw_data:
                    value = raw_data[var_key]
                    if value and value != -666666666:
                        education_brackets[bracket] += value

        total = sum(education_brackets.values())
        if total > 0:
            return {k: round(v / total, 4) for k, v in education_brackets.items()}
        return education_brackets

    def _aggregate_occupation_groups(self, raw_data: dict[str, int]) -> dict[str, float]:
        """
        Aggregate occupations into standard categories.
        """
        occupation_map = {
            "C24010_003E": "Professional",
            "C24010_019E": "Service",
            "C24010_027E": "Sales/Administrative",
            "C24010_034E": "Technical/Construction",
            "C24010_038E": "Manufacturing/Transportation",
        }

        occupations = {}
        for var_id, label in occupation_map.items():
            if var_id in raw_data:
                value = raw_data[var_id]
                if value and value != -666666666:
                    occupations[label] = value
                else:
                    occupations[label] = 0
            else:
                occupations[label] = 0

        total = sum(occupations.values())
        if total > 0:
            return {k: round(v / total, 4) for k, v in occupations.items()}
        return occupations

    async def get_demographic_distribution(
        self,
        category: str,
        state: Optional[str] = None,
        county: Optional[str] = None,
        year: int = LATEST_ACS_YEAR,
    ) -> DemographicDistribution:
        """
        Get processed demographic distribution for a category.

        Args:
            category: One of 'age', 'gender', 'income', 'education', 'occupation'
            state: Optional state FIPS code
            county: Optional county FIPS code
            year: Survey year

        Returns:
            Processed demographic distribution
        """
        # Select variables based on category
        variable_map = {
            "age": AGE_VARIABLES,
            "gender": GENDER_VARIABLES,
            "income": INCOME_VARIABLES,
            "education": EDUCATION_VARIABLES,
            "occupation": OCCUPATION_VARIABLES,
        }

        if category not in variable_map:
            raise ValueError(f"Unknown category: {category}")

        variables = list(variable_map[category].keys())

        # Fetch raw data (routes through DataGateway if configured)
        raw_response = await self.fetch_census_data(
            variables=variables,
            year=year,
            state=state,
            county=county,
        )

        # Parse response (first row is headers, second row is data)
        if len(raw_response) < 2:
            raise ValueError("No data returned from Census API")

        headers = raw_response[0]
        data_row = raw_response[1]

        # Convert to dict
        raw_data = {}
        for i, header in enumerate(headers):
            if header in variables:
                try:
                    raw_data[header] = int(data_row[i]) if data_row[i] else 0
                except (ValueError, TypeError):
                    raw_data[header] = 0

        # Process based on category
        aggregators = {
            "age": self._aggregate_age_groups,
            "gender": lambda d: {
                "Male": d.get("B01001_002E", 0),
                "Female": d.get("B01001_026E", 0),
            },
            "income": self._aggregate_income_groups,
            "education": self._aggregate_education_groups,
            "occupation": self._aggregate_occupation_groups,
        }

        distribution = aggregators[category](raw_data)

        # For gender, convert to percentages
        if category == "gender":
            total = sum(distribution.values())
            if total > 0:
                distribution = {k: round(v / total, 4) for k, v in distribution.items()}

        result = DemographicDistribution(
            category=category,
            distribution=distribution,
            total_population=sum(raw_data.values()),
            source_year=year,
            source_survey=f"ACS 5-Year ({year})",
        )

        # Add manifest metadata if in gateway mode
        if self._is_gateway_mode() and self.data_gateway:
            entries = self.data_gateway.get_manifest_entries()
            if entries:
                latest = entries[-1]
                result.payload_hash = latest.payload_hash
                result.manifest_entry_id = latest.id

        return result

    async def get_full_demographic_profile(
        self,
        state: Optional[str] = None,
        county: Optional[str] = None,
        year: int = LATEST_ACS_YEAR,
    ) -> dict[str, DemographicDistribution]:
        """
        Get complete demographic profile for a region.

        Returns distributions for all categories.
        """
        categories = ["age", "gender", "income", "education", "occupation"]

        # Fetch all categories in parallel
        tasks = [
            self.get_demographic_distribution(cat, state, county, year)
            for cat in categories
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        profile = {}
        for cat, result in zip(categories, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {cat}: {result}")
            else:
                profile[cat] = result

        return profile

    async def sync_census_data(
        self,
        db: AsyncSession,
        data_source_id: UUID,
        state: Optional[str] = None,
        county: Optional[str] = None,
        year: int = LATEST_ACS_YEAR,
    ) -> list[CensusData]:
        """
        Sync census data to database.

        Fetches and stores demographic distributions.
        """
        profile = await self.get_full_demographic_profile(state, county, year)

        census_records = []
        for category, dist in profile.items():
            # Check if record exists
            stmt = select(CensusData).where(
                CensusData.data_source_id == data_source_id,
                CensusData.data_category == category,
                CensusData.state == state,
                CensusData.county == county,
                CensusData.survey_year == year,
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.distribution = dist.distribution
                existing.margin_of_error = dist.margin_of_error
                existing.updated_at = datetime.utcnow()
                census_records.append(existing)
            else:
                # Create new record
                record = CensusData(
                    data_source_id=data_source_id,
                    country="US",
                    state=state,
                    county=county,
                    data_category=category,
                    distribution=dist.distribution,
                    survey_year=year,
                    survey_name=dist.source_survey,
                    margin_of_error=dist.margin_of_error,
                )
                db.add(record)
                census_records.append(record)

        await db.commit()
        return census_records

    async def build_regional_profile(
        self,
        db: AsyncSession,
        data_source_id: UUID,
        region_code: str,
        region_name: str,
        state: Optional[str] = None,
        county: Optional[str] = None,
    ) -> RegionalProfile:
        """
        Build a comprehensive regional profile from census data.
        """
        # Fetch all demographic distributions
        profile = await self.get_full_demographic_profile(state, county)

        # Combine into demographics dict
        demographics = {
            f"{cat}_distribution": dist.distribution
            for cat, dist in profile.items()
        }

        # Determine region type
        if county:
            region_type = "county"
        elif state:
            region_type = "state"
        else:
            region_type = "country"

        # Check if profile exists
        stmt = select(RegionalProfile).where(
            RegionalProfile.region_code == region_code
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.demographics = demographics
            existing.data_completeness = len(profile) / 5.0  # 5 categories
            existing.confidence_score = 0.9  # Census data is high confidence
            existing.updated_at = datetime.utcnow()
            await db.commit()
            return existing

        regional_profile = RegionalProfile(
            data_source_id=data_source_id,
            region_code=region_code,
            region_name=region_name,
            region_type=region_type,
            demographics=demographics,
            data_completeness=len(profile) / 5.0,
            confidence_score=0.9,
        )

        db.add(regional_profile)
        await db.commit()

        return regional_profile

    def get_manifest_entries(self) -> list:
        """
        Get manifest entries from DataGateway (if in gateway mode).

        Returns empty list if not in gateway mode.
        """
        if self._is_gateway_mode() and self.data_gateway:
            return self.data_gateway.get_manifest_entries()
        return []


# US State FIPS Codes for reference
US_STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
    "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
}


def get_census_service(
    api_key: Optional[str] = None,
    data_gateway: Optional[DataGateway] = None,
    gateway_context: Optional[DataGatewayContext] = None,
) -> CensusDataService:
    """
    Factory function to create CensusDataService.

    Args:
        api_key: Optional Census Bureau API key
        data_gateway: Optional DataGateway for temporal isolation
        gateway_context: Optional context for DataGateway requests

    Returns:
        CensusDataService instance
    """
    return CensusDataService(
        api_key=api_key,
        data_gateway=data_gateway,
        gateway_context=gateway_context,
    )


def create_census_service_with_gateway(
    db: AsyncSession,
    tenant_id: str,
    project_id: Optional[str] = None,
    run_id: Optional[str] = None,
    cutoff_time: Optional[datetime] = None,
    isolation_level: int = 1,
    temporal_mode: str = "live",
    api_key: Optional[str] = None,
) -> CensusDataService:
    """
    Factory function to create CensusDataService with DataGateway configured.

    Convenience function for creating a census service ready for backtest mode.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        project_id: Optional project UUID
        run_id: Optional run UUID
        cutoff_time: Optional cutoff timestamp for backtest
        isolation_level: Isolation level (1-3)
        temporal_mode: 'live' or 'backtest'
        api_key: Optional Census Bureau API key

    Returns:
        CensusDataService configured with DataGateway
    """
    from app.services.data_gateway import create_data_gateway

    context = DataGatewayContext(
        tenant_id=tenant_id,
        project_id=project_id,
        run_id=run_id,
        cutoff_time=cutoff_time,
        isolation_level=isolation_level,
        temporal_mode=temporal_mode,
    )

    gateway = create_data_gateway(db, context)

    return CensusDataService(
        api_key=api_key,
        data_gateway=gateway,
        gateway_context=context,
    )
