"""
LLM Data Tools - DataGateway-backed tools for LLM data access
Reference: temporal.md §8 Phase 4

This module defines tools that the LLM can use to access external data.
ALL data access MUST go through DataGateway - no direct API calls allowed.

Key principle: LLM can only access data that has been:
1. Routed through DataGateway
2. Subject to cutoff enforcement (in backtest mode)
3. Recorded in the data manifest

Usage:
    tools = LLMDataTools(gateway, context)
    result = await tools.get_demographic_data(region="US", year=2023)

Note: These tools are designed to be called via function_call in the LLM API.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.services.data_gateway import (
    DataGateway,
    DataGatewayContext,
    DataGatewayResponse,
    SourceBlockedError,
    SourceNotFoundError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Schemas (for LLM function_call)
# =============================================================================

class ToolResult(BaseModel):
    """Result from an LLM data tool call."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    source_name: Optional[str] = None
    record_count: int = 0
    filtered_count: int = 0
    payload_hash: Optional[str] = None
    manifest_entry_id: Optional[str] = None


class DemographicDataParams(BaseModel):
    """Parameters for get_demographic_data tool."""
    region: str = Field(..., description="Region code (e.g., 'US', 'EU', 'APAC')")
    year: Optional[int] = Field(None, description="Year for historical data")
    metric: Optional[str] = Field(None, description="Specific metric to retrieve")


class RegionalStatisticsParams(BaseModel):
    """Parameters for get_regional_statistics tool."""
    region_code: str = Field(..., description="Region identifier")
    category: Optional[str] = Field(None, description="Statistics category")
    start_year: Optional[int] = Field(None, description="Start year for range")
    end_year: Optional[int] = Field(None, description="End year for range")


class EconomicIndicatorParams(BaseModel):
    """Parameters for get_economic_indicators tool."""
    country: str = Field(..., description="Country code (ISO 3166-1)")
    indicator: str = Field(..., description="Indicator code (e.g., 'GDP', 'CPI')")
    year: Optional[int] = Field(None, description="Year for data")


# =============================================================================
# Tool Definitions (for LLM API)
# =============================================================================

LLM_DATA_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_demographic_data",
            "description": "Fetch demographic data for a region. Use this when you need population, age distribution, income levels, or similar demographic information. Data is subject to temporal cutoff in backtest mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Region code (e.g., 'US', 'EU', 'APAC', 'US-CA' for California)"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year for historical data (optional, defaults to latest available)"
                    },
                    "metric": {
                        "type": "string",
                        "description": "Specific metric to retrieve (e.g., 'population', 'median_income', 'age_distribution')"
                    }
                },
                "required": ["region"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_regional_statistics",
            "description": "Fetch regional statistics and market data. Use this for market size, adoption rates, or regional economic indicators. Data is subject to temporal cutoff in backtest mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region_code": {
                        "type": "string",
                        "description": "Region identifier (e.g., 'north_america', 'europe', 'asia_pacific')"
                    },
                    "category": {
                        "type": "string",
                        "description": "Statistics category (e.g., 'market_size', 'adoption_rate', 'growth_rate')"
                    },
                    "start_year": {
                        "type": "integer",
                        "description": "Start year for historical range"
                    },
                    "end_year": {
                        "type": "integer",
                        "description": "End year for historical range"
                    }
                },
                "required": ["region_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_economic_indicators",
            "description": "Fetch economic indicators for a country. Use this for GDP, inflation, unemployment, or other macroeconomic data. Data is subject to temporal cutoff in backtest mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "Country code (ISO 3166-1 alpha-2, e.g., 'US', 'GB', 'DE')"
                    },
                    "indicator": {
                        "type": "string",
                        "description": "Indicator code (e.g., 'GDP', 'CPI', 'UNEMPLOYMENT')"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year for the data"
                    }
                },
                "required": ["country", "indicator"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_census_data",
            "description": "Fetch census data for population characteristics. Use this for detailed demographic breakdowns, household data, or census tract level information. Data is subject to temporal cutoff in backtest mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state_code": {
                        "type": "string",
                        "description": "US state FIPS code or abbreviation"
                    },
                    "variables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Census variables to retrieve (e.g., ['B01001_001E', 'B19013_001E'])"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Census year (e.g., 2020, 2021)"
                    },
                    "dataset": {
                        "type": "string",
                        "description": "Census dataset (e.g., 'acs5', 'decennial')"
                    }
                },
                "required": ["state_code"]
            }
        }
    }
]


# =============================================================================
# LLM Data Tools Service
# =============================================================================

class LLMDataTools:
    """
    LLM data access tools that route ALL requests through DataGateway.

    This class provides tool implementations that the LLM can call via
    function_call. All data access is:
    1. Routed through DataGateway
    2. Subject to cutoff enforcement
    3. Recorded in the data manifest

    Reference: temporal.md §5 - DataGateway as single entry point
    """

    def __init__(
        self,
        gateway: DataGateway,
        context: DataGatewayContext,
    ):
        """
        Initialize LLM Data Tools.

        Args:
            gateway: DataGateway instance for data access
            context: DataGatewayContext with tenant, project, temporal settings
        """
        self.gateway = gateway
        self.context = context

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> ToolResult:
        """
        Execute a tool by name with given arguments.

        This is the main entry point for LLM tool calls.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments from LLM function_call

        Returns:
            ToolResult with data or error
        """
        tool_map = {
            "get_demographic_data": self.get_demographic_data,
            "get_regional_statistics": self.get_regional_statistics,
            "get_economic_indicators": self.get_economic_indicators,
            "get_census_data": self.get_census_data,
        }

        tool_fn = tool_map.get(tool_name)
        if not tool_fn:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )

        try:
            return await tool_fn(**arguments)
        except SourceBlockedError as e:
            logger.warning(
                f"LLM_DATA_TOOL: Source blocked - {e.source_name} at Level {e.isolation_level}"
            )
            return ToolResult(
                success=False,
                error=f"Data source '{e.source_name}' is not available at the current isolation level ({e.isolation_level}). This source cannot be used in backtest mode with strict isolation."
            )
        except SourceNotFoundError as e:
            logger.warning(f"LLM_DATA_TOOL: Source not found - {e.source_name}")
            return ToolResult(
                success=False,
                error=f"Data source '{e.source_name}' is not registered. Please use a known data source."
            )
        except Exception as e:
            logger.error(f"LLM_DATA_TOOL: Error executing {tool_name} - {str(e)}")
            return ToolResult(
                success=False,
                error=f"Error accessing data: {str(e)}"
            )

    async def get_demographic_data(
        self,
        region: str,
        year: Optional[int] = None,
        metric: Optional[str] = None,
    ) -> ToolResult:
        """
        Fetch demographic data through DataGateway.

        Args:
            region: Region code
            year: Optional year for historical data
            metric: Optional specific metric

        Returns:
            ToolResult with demographic data
        """
        # Determine source based on region
        if region.startswith("US"):
            source_name = "census_bureau"
        elif region in ["EU", "EUR"] or region.startswith("EU-"):
            source_name = "eurostat"
        else:
            source_name = "regional_static"

        params = {
            "region": region,
            "year": year,
            "metric": metric,
        }

        # Mock data fetcher for now - in production, this would call actual APIs
        async def fetch_data():
            # This would be replaced with actual API calls in production
            return [
                {
                    "region": region,
                    "year": year or 2023,
                    "metric": metric or "population",
                    "value": 330_000_000 if region == "US" else 100_000,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]

        response = await self.gateway.request(
            source_name=source_name,
            endpoint="/demographic",
            params=params,
            context=self.context,
            data_fetcher=fetch_data,
        )

        return ToolResult(
            success=True,
            data=response.data,
            source_name=response.source_name,
            record_count=response.record_count,
            filtered_count=response.filtered_count,
            payload_hash=response.payload_hash,
            manifest_entry_id=response.manifest_entry.id,
        )

    async def get_regional_statistics(
        self,
        region_code: str,
        category: Optional[str] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> ToolResult:
        """
        Fetch regional statistics through DataGateway.

        Args:
            region_code: Region identifier
            category: Optional statistics category
            start_year: Optional start year
            end_year: Optional end year

        Returns:
            ToolResult with regional statistics
        """
        source_name = "regional_static"

        params = {
            "region_code": region_code,
            "category": category,
            "start_year": start_year,
            "end_year": end_year,
        }

        async def fetch_data():
            return [
                {
                    "region_code": region_code,
                    "category": category or "market_size",
                    "year": end_year or 2023,
                    "value": 1_000_000,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]

        response = await self.gateway.request(
            source_name=source_name,
            endpoint="/regional_stats",
            params=params,
            context=self.context,
            data_fetcher=fetch_data,
        )

        return ToolResult(
            success=True,
            data=response.data,
            source_name=response.source_name,
            record_count=response.record_count,
            filtered_count=response.filtered_count,
            payload_hash=response.payload_hash,
            manifest_entry_id=response.manifest_entry.id,
        )

    async def get_economic_indicators(
        self,
        country: str,
        indicator: str,
        year: Optional[int] = None,
    ) -> ToolResult:
        """
        Fetch economic indicators through DataGateway.

        Args:
            country: Country code
            indicator: Indicator code
            year: Optional year

        Returns:
            ToolResult with economic data
        """
        # Determine source based on country
        if country == "US":
            source_name = "census_bureau"
        elif country in ["GB", "DE", "FR", "IT", "ES"]:
            source_name = "eurostat"
        else:
            source_name = "regional_static"

        params = {
            "country": country,
            "indicator": indicator,
            "year": year,
        }

        async def fetch_data():
            return [
                {
                    "country": country,
                    "indicator": indicator,
                    "year": year or 2023,
                    "value": 25_000_000_000_000 if indicator == "GDP" else 3.2,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]

        response = await self.gateway.request(
            source_name=source_name,
            endpoint="/economic_indicators",
            params=params,
            context=self.context,
            data_fetcher=fetch_data,
        )

        return ToolResult(
            success=True,
            data=response.data,
            source_name=response.source_name,
            record_count=response.record_count,
            filtered_count=response.filtered_count,
            payload_hash=response.payload_hash,
            manifest_entry_id=response.manifest_entry.id,
        )

    async def get_census_data(
        self,
        state_code: str,
        variables: Optional[List[str]] = None,
        year: Optional[int] = None,
        dataset: Optional[str] = None,
    ) -> ToolResult:
        """
        Fetch census data through DataGateway.

        Args:
            state_code: US state code
            variables: Census variables to retrieve
            year: Census year
            dataset: Census dataset

        Returns:
            ToolResult with census data
        """
        source_name = "census_bureau"

        params = {
            "state_code": state_code,
            "variables": variables or ["B01001_001E"],
            "year": year or 2021,
            "dataset": dataset or "acs5",
        }

        async def fetch_data():
            return [
                {
                    "state_code": state_code,
                    "variable": var,
                    "year": year or 2021,
                    "value": 1_000_000,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                for var in (variables or ["B01001_001E"])
            ]

        response = await self.gateway.request(
            source_name=source_name,
            endpoint="/census/acs",
            params=params,
            context=self.context,
            data_fetcher=fetch_data,
        )

        return ToolResult(
            success=True,
            data=response.data,
            source_name=response.source_name,
            record_count=response.record_count,
            filtered_count=response.filtered_count,
            payload_hash=response.payload_hash,
            manifest_entry_id=response.manifest_entry.id,
        )

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas for LLM function_call."""
        return LLM_DATA_TOOLS_SCHEMA


# =============================================================================
# Backtest Policy Injection
# =============================================================================

def get_backtest_policy_prompt(
    as_of_datetime: datetime,
    isolation_level: int,
    timezone: str = "UTC",
) -> str:
    """
    Generate backtest policy text for system prompt injection.

    This text is injected into system prompts when running in backtest mode
    to ensure the LLM respects temporal isolation.

    Reference: temporal.md §8 Phase 4 item 11

    Args:
        as_of_datetime: The temporal cutoff datetime
        isolation_level: Isolation strictness (1-3)
        timezone: Timezone for the cutoff

    Returns:
        Policy text to inject into system prompt
    """
    level_descriptions = {
        1: "Basic isolation - cutoff enforced, but you may reference general knowledge",
        2: "Strict isolation - you MUST ONLY use data returned by tools in this session",
        3: "Audit-first isolation - ALL claims will be audited against the data manifest",
    }

    level_desc = level_descriptions.get(isolation_level, level_descriptions[2])

    return f"""
================================================================================
TEMPORAL KNOWLEDGE ISOLATION ACTIVE
================================================================================

Mode: BACKTEST
As-of Datetime: {as_of_datetime.isoformat()}
Timezone: {timezone}
Isolation Level: {isolation_level} ({level_desc})

CRITICAL RULES:
1. You may ONLY use information returned by data tools in this session context.
2. Do NOT reference ANY facts, events, products, or data from AFTER {as_of_datetime.strftime('%Y-%m-%d %H:%M')} {timezone}.
3. If you are UNSURE whether something existed before the cutoff date, you MUST say you are unsure.
4. Do NOT use any knowledge about events after the cutoff - this would contaminate the backtest.
5. Final numeric predictions MUST come from the simulation engine, not from your knowledge.

ALLOWED DATA ACCESS:
- Use the provided data tools (get_demographic_data, get_regional_statistics, etc.)
- Reference ONLY the data returned by these tools
- All data will be automatically filtered to the as-of datetime

PROHIBITED:
- Web browsing or searching
- Referencing news, events, or developments after {as_of_datetime.strftime('%Y-%m-%d')}
- Making predictions based on future knowledge
- Hallucinating data not in the context

Your outputs will be audited against the data manifest. Non-compliant responses will be flagged.
================================================================================
"""


def inject_backtest_policy(
    system_prompt: str,
    context: DataGatewayContext,
) -> str:
    """
    Inject backtest policy into system prompt if running in backtest mode.

    Args:
        system_prompt: Original system prompt
        context: DataGatewayContext with temporal settings

    Returns:
        System prompt with policy injected (if backtest mode)
    """
    if context.temporal_mode != "backtest" or not context.cutoff_time:
        return system_prompt

    policy = get_backtest_policy_prompt(
        as_of_datetime=context.cutoff_time,
        isolation_level=context.isolation_level,
        timezone="UTC",  # Could be enhanced to use project timezone
    )

    return f"{policy}\n\n{system_prompt}"


# =============================================================================
# Factory Functions
# =============================================================================

def create_llm_data_tools(
    gateway: DataGateway,
    context: DataGatewayContext,
) -> LLMDataTools:
    """
    Create an LLMDataTools instance.

    Args:
        gateway: DataGateway instance
        context: DataGatewayContext

    Returns:
        Configured LLMDataTools instance
    """
    return LLMDataTools(gateway=gateway, context=context)
