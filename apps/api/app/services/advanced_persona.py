"""
Advanced Persona Generator
Generates comprehensive personas with 100+ nuanced traits.
Supports multi-region data, topic-specific knowledge, and multiple input methods.
"""

import json
import random
import logging
from typing import Any, Optional
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.regional_data import (
    MultiRegionDataService,
    RegionalDemographics,
    get_regional_service
)
from app.models.persona import (
    PersonaTemplate,
    PersonaRecord,
    PersonaSourceType,
    RegionType,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============= Configuration Models =============

class PersonaGenerationConfig(BaseModel):
    """Configuration for persona generation."""
    region: str  # us, europe, southeast_asia, china
    country: Optional[str] = None
    sub_region: Optional[str] = None

    # Topic configuration
    topic: Optional[str] = None
    industry: Optional[str] = None
    keywords: Optional[list[str]] = None

    # Generation settings
    count: int = 100
    source_type: str = "ai_generated"
    year: Optional[int] = None

    # Trait depth
    include_psychographics: bool = True
    include_behavioral: bool = True
    include_cultural: bool = True
    include_topic_knowledge: bool = True


class GeneratedPersona(BaseModel):
    """Generated persona with all attributes."""
    demographics: dict[str, Any]
    professional: dict[str, Any]
    psychographics: dict[str, Any]
    behavioral: dict[str, Any]
    interests: dict[str, Any]
    topic_knowledge: Optional[dict[str, Any]] = None
    cultural_context: Optional[dict[str, Any]] = None
    full_prompt: str
    confidence_score: float


# ============= Trait Libraries =============

class TraitLibrary:
    """Libraries of traits for persona generation."""

    # Big Five personality distributions
    PERSONALITY_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]

    # Value orientations
    VALUES = [
        "Family", "Career Success", "Financial Security", "Health & Wellness",
        "Adventure", "Creativity", "Learning", "Social Impact",
        "Independence", "Tradition", "Status", "Relationships",
        "Spirituality", "Work-Life Balance", "Achievement", "Community",
        "Innovation", "Stability", "Freedom", "Recognition"
    ]

    # Decision styles
    DECISION_STYLES = [
        "Analytical", "Intuitive", "Deliberate", "Impulsive",
        "Collaborative", "Independent", "Risk-taking", "Conservative"
    ]

    # Innovation adoption categories
    INNOVATION_ADOPTION = [
        "Innovator", "Early Adopter", "Early Majority", "Late Majority", "Laggard"
    ]

    # Social media platforms by region
    SOCIAL_PLATFORMS = {
        "us": ["Facebook", "Instagram", "TikTok", "Twitter/X", "LinkedIn", "YouTube", "Snapchat", "Reddit", "Pinterest"],
        "europe": ["Facebook", "Instagram", "TikTok", "Twitter/X", "LinkedIn", "WhatsApp", "YouTube", "Snapchat"],
        "southeast_asia": ["Facebook", "Instagram", "TikTok", "YouTube", "WhatsApp", "LINE", "Shopee", "Grab"],
        "china": ["WeChat", "Weibo", "Douyin", "Xiaohongshu", "Bilibili", "Taobao", "Zhihu", "QQ"],
    }

    # News sources by region
    NEWS_SOURCES = {
        "us": ["CNN", "Fox News", "MSNBC", "New York Times", "Washington Post", "WSJ", "NPR", "Bloomberg", "Vice"],
        "europe": ["BBC", "The Guardian", "Le Monde", "Der Spiegel", "Reuters", "Financial Times", "Euronews"],
        "southeast_asia": ["CNA", "The Straits Times", "Bangkok Post", "Kompas", "VnExpress", "Manila Bulletin"],
        "china": ["Xinhua", "CCTV", "People's Daily", "Global Times", "Caixin", "The Paper", "NetEase"],
    }

    # Hobbies by category
    HOBBIES = {
        "active": ["Running", "Swimming", "Hiking", "Cycling", "Gym", "Yoga", "Tennis", "Golf", "Martial Arts"],
        "creative": ["Painting", "Photography", "Writing", "Music", "Crafts", "Cooking", "Gardening"],
        "social": ["Traveling", "Dining Out", "Parties", "Volunteering", "Book Clubs", "Sports Teams"],
        "indoor": ["Reading", "Gaming", "Movies", "Podcasts", "Collecting", "Home Improvement"],
        "tech": ["Coding", "3D Printing", "VR/AR", "Gadgets", "Investing"],
    }

    # Cultural values by region
    CULTURAL_VALUES = {
        "us": ["Individualism", "Achievement", "Equality", "Direct Communication", "Innovation"],
        "europe": ["Work-Life Balance", "Social Welfare", "Cultural Heritage", "Environmental Consciousness"],
        "southeast_asia": ["Family Harmony", "Respect for Elders", "Face-saving", "Community", "Hospitality"],
        "china": ["Filial Piety", "Collective Harmony", "Education", "Hard Work", "Face/Mianzi", "Guanxi"],
    }

    # Topic-specific knowledge templates
    TOPIC_KNOWLEDGE_TEMPLATES = {
        "smartphone": {
            "current_device": ["iPhone 15 Pro", "iPhone 14", "Samsung Galaxy S24", "Google Pixel 8", "OnePlus 12", "Xiaomi 14"],
            "brand_preference": ["Apple", "Samsung", "Google", "OnePlus", "Xiaomi", "No preference"],
            "important_features": ["Camera", "Battery", "Performance", "Display", "Storage", "5G", "AI Features"],
            "upgrade_cycle": ["Every year", "Every 2 years", "Every 3+ years", "When broken"],
            "budget_range": ["Under $500", "$500-$800", "$800-$1200", "$1200+"],
        },
        "automotive": {
            "current_vehicle": ["Sedan", "SUV", "Truck", "EV", "Hybrid", "Luxury", "No vehicle"],
            "brand_preference": ["Toyota", "Honda", "Ford", "Tesla", "BMW", "Mercedes", "No preference"],
            "important_factors": ["Price", "Fuel Efficiency", "Safety", "Technology", "Brand", "Reliability"],
            "purchase_timeline": ["Within 6 months", "1-2 years", "2-5 years", "No plans"],
            "financing_preference": ["Cash", "Loan", "Lease"],
        },
        "finance": {
            "investment_experience": ["Beginner", "Intermediate", "Advanced", "Expert"],
            "investment_types": ["Stocks", "ETFs", "Bonds", "Real Estate", "Crypto", "Mutual Funds"],
            "risk_appetite": ["Very Conservative", "Conservative", "Moderate", "Aggressive", "Very Aggressive"],
            "financial_goals": ["Retirement", "Wealth Building", "Income", "Emergency Fund", "Education"],
            "advisor_usage": ["DIY", "Robo-advisor", "Human Advisor", "Mixed"],
        },
        "healthcare": {
            "health_status": ["Excellent", "Good", "Fair", "Poor"],
            "conditions": ["None", "Chronic", "Acute", "Multiple"],
            "healthcare_usage": ["Rarely", "Annual checkups", "Regular", "Frequent"],
            "health_priorities": ["Prevention", "Treatment", "Wellness", "Mental Health"],
            "insurance_type": ["Private", "Employer", "Government", "None"],
        },
        "travel": {
            "frequency": ["Rarely", "1-2 trips/year", "3-5 trips/year", "Monthly+"],
            "style": ["Budget", "Mid-range", "Luxury", "Adventure"],
            "planning": ["Spontaneous", "Last minute", "Advance planner", "Meticulously planned"],
            "booking_preference": ["OTA", "Direct", "Travel Agent", "Package Deals"],
            "priorities": ["Price", "Experience", "Convenience", "Authenticity"],
        },
        "food_beverage": {
            "dietary_preference": ["No restrictions", "Vegetarian", "Vegan", "Pescatarian", "Keto", "Halal", "Kosher"],
            "cooking_frequency": ["Daily", "Several times/week", "Rarely", "Never"],
            "dining_out_frequency": ["Rarely", "Weekly", "Several times/week", "Daily"],
            "food_priorities": ["Taste", "Health", "Convenience", "Price", "Sustainability"],
            "cuisine_preferences": ["Local", "Asian", "Western", "Mediterranean", "Fusion"],
        },
        "election": {
            "political_engagement": ["Very active", "Moderately active", "Passive", "Disengaged"],
            "voting_history": ["Always vote", "Usually vote", "Sometimes vote", "Rarely vote"],
            "information_sources": ["Traditional media", "Social media", "Direct from candidates", "Friends/Family"],
            "issue_priorities": ["Economy", "Healthcare", "Environment", "Immigration", "Education", "Security"],
            "party_affiliation": ["Strong partisan", "Lean partisan", "Independent", "Undecided"],
        },
    }


# ============= Advanced Persona Generator =============

class AdvancedPersonaGenerator:
    """
    Generates comprehensive personas with 100+ nuanced traits.
    Uses real demographic data and intelligent trait correlation.
    """

    def __init__(
        self,
        config: PersonaGenerationConfig,
        regional_demographics: Optional[RegionalDemographics] = None
    ):
        self.config = config
        self.regional_demographics = regional_demographics
        self.trait_library = TraitLibrary()
        self.multi_region_service = MultiRegionDataService()
        self._rng = random.Random()

    def set_seed(self, seed: int):
        """Set random seed for reproducibility."""
        self._rng = random.Random(seed)

    async def initialize(self):
        """Initialize with regional demographics if not provided."""
        if not self.regional_demographics:
            self.regional_demographics = await self.multi_region_service.get_demographics(
                region=self.config.region,
                country=self.config.country,
                sub_region=self.config.sub_region,
                year=self.config.year
            )

    def _weighted_choice(self, distribution: dict[str, float]) -> str:
        """Select from a weighted distribution."""
        items = list(distribution.keys())
        weights = list(distribution.values())
        return self._rng.choices(items, weights=weights, k=1)[0]

    def _generate_age_from_bracket(self, bracket: str) -> int:
        """Generate specific age from age bracket."""
        bracket_ranges = {
            "18-24": (18, 24), "25-34": (25, 34), "35-44": (35, 44),
            "45-54": (45, 54), "55-64": (55, 64), "65-74": (65, 74), "75+": (75, 90)
        }
        min_age, max_age = bracket_ranges.get(bracket, (25, 45))
        return self._rng.randint(min_age, max_age)

    def _generate_demographics(self) -> dict[str, Any]:
        """Generate comprehensive demographic attributes."""
        demo = self.regional_demographics

        age_bracket = self._weighted_choice(demo.age_distribution)
        age = self._generate_age_from_bracket(age_bracket)
        gender = self._weighted_choice(demo.gender_distribution)

        # Determine generation based on age
        generation_map = {
            (18, 27): "Gen Z",
            (28, 43): "Millennial",
            (44, 59): "Gen X",
            (60, 78): "Baby Boomer",
            (79, 100): "Silent Generation"
        }
        generation = "Millennial"
        for (min_age, max_age), gen in generation_map.items():
            if min_age <= age <= max_age:
                generation = gen
                break

        # Urban/Rural based on region
        urban_rural = "Urban"
        if demo.urban_rural_distribution:
            urban_rural = self._weighted_choice(demo.urban_rural_distribution)
        else:
            urban_rural = self._rng.choices(["Urban", "Suburban", "Rural"], weights=[0.6, 0.3, 0.1])[0]

        # Marital status (correlated with age)
        if age < 25:
            marital_status = self._rng.choices(["Single", "In relationship", "Married"], weights=[0.7, 0.2, 0.1])[0]
        elif age < 35:
            marital_status = self._rng.choices(["Single", "In relationship", "Married", "Divorced"], weights=[0.3, 0.2, 0.45, 0.05])[0]
        elif age < 55:
            marital_status = self._rng.choices(["Single", "Married", "Divorced", "Widowed"], weights=[0.15, 0.65, 0.15, 0.05])[0]
        else:
            marital_status = self._rng.choices(["Single", "Married", "Divorced", "Widowed"], weights=[0.1, 0.55, 0.15, 0.2])[0]

        # Children (correlated with age and marital status)
        has_children = False
        children_count = 0
        if marital_status in ["Married", "Divorced", "Widowed"] and age > 25:
            has_children = self._rng.random() < 0.75
            if has_children:
                children_count = self._rng.choices([1, 2, 3, 4], weights=[0.3, 0.45, 0.2, 0.05])[0]

        # Household size
        household_size = 1
        if marital_status == "Married":
            household_size = 2 + children_count
        elif has_children:
            household_size = 1 + children_count

        demographics = {
            "age": age,
            "age_bracket": age_bracket,
            "gender": gender,
            "gender_identity": gender,  # Can be expanded
            "generation": generation,
            "country": demo.country or self.config.country or "Unknown",
            "region": demo.region,
            "sub_region": demo.sub_region or self.config.sub_region,
            "urban_rural": urban_rural,
            "marital_status": marital_status,
            "household_size": household_size,
            "has_children": has_children,
            "children_count": children_count,
            "income_bracket": self._weighted_choice(demo.income_distribution),
            "housing_type": self._rng.choices(
                ["Apartment", "Condo", "House", "Townhouse"],
                weights=[0.35, 0.2, 0.35, 0.1]
            )[0],
            "housing_ownership": self._rng.choices(
                ["Rent", "Own", "Live with family"],
                weights=[0.45, 0.45, 0.1]
            )[0],
        }

        # Add ethnicity if available
        if demo.ethnicity_distribution:
            demographics["ethnicity"] = self._weighted_choice(demo.ethnicity_distribution)

        # Add religion if available
        if demo.religion_distribution:
            demographics["religion"] = self._weighted_choice(demo.religion_distribution)

        return demographics

    def _generate_professional(self, demographics: dict[str, Any]) -> dict[str, Any]:
        """Generate professional background attributes."""
        demo = self.regional_demographics
        age = demographics["age"]

        # Education level (correlated with income)
        education = self._weighted_choice(demo.education_distribution)

        # Years of experience (correlated with age)
        years_experience = max(0, age - 22 - self._rng.randint(0, 4))
        if years_experience < 0:
            years_experience = 0

        # Seniority level (correlated with experience)
        if years_experience < 3:
            seniority = "Entry-level"
        elif years_experience < 7:
            seniority = "Mid-level"
        elif years_experience < 12:
            seniority = "Senior"
        elif years_experience < 18:
            seniority = "Manager/Director"
        else:
            seniority = "Executive"

        # Company size
        company_sizes = ["Startup (1-50)", "Small (51-200)", "Medium (201-1000)", "Large (1001-5000)", "Enterprise (5000+)"]
        company_size = self._rng.choice(company_sizes)

        # Work style (correlated with generation)
        if demographics["generation"] in ["Gen Z", "Millennial"]:
            remote_pref = self._rng.choices(["Remote", "Hybrid", "In-office"], weights=[0.4, 0.45, 0.15])[0]
        else:
            remote_pref = self._rng.choices(["Remote", "Hybrid", "In-office"], weights=[0.2, 0.4, 0.4])[0]

        professional = {
            "employment_status": self._rng.choices(
                ["Full-time", "Part-time", "Self-employed", "Freelance", "Unemployed", "Retired", "Student"],
                weights=[0.6, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05]
            )[0],
            "occupation": self._weighted_choice(demo.occupation_distribution),
            "industry": self._rng.choice([
                "Technology", "Healthcare", "Finance", "Education", "Retail",
                "Manufacturing", "Government", "Media", "Hospitality", "Real Estate"
            ]),
            "company_size": company_size,
            "seniority_level": seniority,
            "years_experience": years_experience,
            "education_level": education,
            "education_field": self._rng.choice([
                "Business", "Engineering", "Arts", "Sciences", "Medicine",
                "Law", "Education", "Social Sciences", "Computer Science", "Other"
            ]),
            "career_stage": "Early Career" if years_experience < 5 else ("Mid-Career" if years_experience < 15 else "Late Career"),
            "job_satisfaction": self._rng.randint(3, 10),
            "career_ambition": self._rng.choice(["Executive Leadership", "Expert/Specialist", "Entrepreneur", "Work-Life Balance", "Career Change"]),
            "work_style": self._rng.choice(["Collaborative", "Independent", "Structured", "Flexible", "Creative"]),
            "remote_work_preference": remote_pref,
            "commute_method": self._rng.choice(["Drive", "Public Transit", "Walk/Bike", "Remote", "Mixed"]),
            "professional_network_size": self._rng.choice(["Small (<50)", "Medium (50-200)", "Large (200-500)", "Very Large (500+)"]),
            "entrepreneurial_experience": self._rng.random() < 0.2,
        }

        # Add skills based on industry/occupation
        professional["skills"] = self._rng.sample([
            "Leadership", "Communication", "Problem Solving", "Data Analysis",
            "Project Management", "Technical Skills", "Sales", "Marketing",
            "Customer Service", "Strategic Planning", "Team Management"
        ], k=self._rng.randint(3, 6))

        return professional

    def _generate_psychographics(self, demographics: dict[str, Any], professional: dict[str, Any]) -> dict[str, Any]:
        """Generate psychographic profile with 30+ attributes."""
        generation = demographics["generation"]

        # Personality type
        personality_type = self._rng.choice(self.trait_library.PERSONALITY_TYPES)

        # Big Five (0-1 scale)
        big_five = {
            "openness": round(self._rng.uniform(0.3, 0.9), 2),
            "conscientiousness": round(self._rng.uniform(0.4, 0.95), 2),
            "extraversion": round(self._rng.uniform(0.2, 0.85), 2),
            "agreeableness": round(self._rng.uniform(0.4, 0.9), 2),
            "neuroticism": round(self._rng.uniform(0.1, 0.6), 2),
        }

        # Values (select 3-5 primary values)
        primary_values = self._rng.sample(self.trait_library.VALUES, k=self._rng.randint(3, 5))

        # Innovation adoption (correlated with age/generation)
        if generation in ["Gen Z", "Millennial"]:
            innovation_weights = [0.15, 0.35, 0.35, 0.12, 0.03]
        else:
            innovation_weights = [0.05, 0.15, 0.35, 0.30, 0.15]
        innovation_adoption = self._rng.choices(self.trait_library.INNOVATION_ADOPTION, weights=innovation_weights)[0]

        psychographics = {
            "values_primary": primary_values,
            "values_orientation": self._rng.choice(["Progressive", "Moderate", "Traditional", "Mixed"]),
            "personality_type": personality_type,
            "big_five": big_five,
            "risk_tolerance": self._rng.randint(1, 10),
            "change_readiness": self._rng.randint(3, 10),
            "innovation_adoption": innovation_adoption,
            "decision_style": self._rng.choice(self.trait_library.DECISION_STYLES),
            "information_processing": self._rng.choice(["Detail-oriented", "Big-picture", "Data-driven", "Intuitive"]),
            "social_influence_susceptibility": self._rng.randint(1, 10),
            "brand_loyalty_tendency": self._rng.choice(["Very Loyal", "Loyal", "Moderate", "Switcher"]),
            "price_sensitivity": self._rng.randint(1, 10),
            "quality_consciousness": self._rng.randint(5, 10),
            "status_seeking": self._rng.randint(1, 10),
            "environmental_consciousness": self._rng.randint(3, 10),
            "health_consciousness": self._rng.randint(4, 10),
            "time_orientation": self._rng.choice(["Present-focused", "Future-focused", "Balanced"]),
            "locus_of_control": self._rng.choice(["Internal", "External", "Mixed"]),
            "achievement_motivation": self._rng.randint(4, 10),
            "need_for_uniqueness": self._rng.randint(2, 9),
            "nostalgia_proneness": self._rng.randint(1, 8),
            "impulsivity": self._rng.randint(1, 8),
            "materialism": self._rng.randint(2, 8),
            "life_satisfaction": self._rng.randint(4, 10),
            "stress_level": self._rng.randint(2, 8),
            "optimism": self._rng.randint(4, 9),
            "trust_in_institutions": self._rng.randint(2, 9),
            "trust_in_brands": self._rng.randint(3, 9),
            "political_engagement": self._rng.choice(["Very Active", "Active", "Moderate", "Low", "None"]),
        }

        return psychographics

    def _generate_behavioral(self, demographics: dict[str, Any], psychographics: dict[str, Any]) -> dict[str, Any]:
        """Generate behavioral patterns with 25+ attributes."""
        region = self.config.region
        generation = demographics["generation"]

        # Social media platforms (region-specific)
        platforms = self.trait_library.SOCIAL_PLATFORMS.get(region, self.trait_library.SOCIAL_PLATFORMS["us"])
        active_platforms = self._rng.sample(platforms, k=self._rng.randint(3, 6))

        # News sources (region-specific)
        news_sources = self.trait_library.NEWS_SOURCES.get(region, self.trait_library.NEWS_SOURCES["us"])
        preferred_news = self._rng.sample(news_sources, k=self._rng.randint(2, 4))

        # Social media hours (correlated with generation)
        if generation in ["Gen Z"]:
            social_media_hours = round(self._rng.uniform(3, 6), 1)
        elif generation == "Millennial":
            social_media_hours = round(self._rng.uniform(2, 4.5), 1)
        else:
            social_media_hours = round(self._rng.uniform(0.5, 2.5), 1)

        behavioral = {
            "media_consumption": {
                "social_media_hours_daily": social_media_hours,
                "platforms": active_platforms,
                "content_preferences": self._rng.sample([
                    "News", "Entertainment", "Education", "Sports", "Lifestyle",
                    "Tech", "Business", "Gaming", "Music", "DIY/Tutorials"
                ], k=self._rng.randint(3, 5)),
                "news_sources": preferred_news,
                "streaming_services": self._rng.sample([
                    "Netflix", "Disney+", "Amazon Prime", "HBO Max", "Hulu",
                    "YouTube Premium", "Spotify", "Apple Music"
                ], k=self._rng.randint(2, 4)),
                "podcast_listener": self._rng.random() < 0.6,
                "podcast_genres": self._rng.sample([
                    "Business", "True Crime", "Comedy", "News", "Education", "Tech"
                ], k=self._rng.randint(1, 3)) if self._rng.random() < 0.6 else [],
            },
            "shopping_behavior": {
                "online_vs_offline": round(self._rng.uniform(0.4, 0.9), 2),
                "research_before_purchase": self._rng.random() < 0.75,
                "review_dependency": self._rng.randint(5, 10),
                "brand_discovery": self._rng.sample([
                    "Social Media", "Word of Mouth", "Ads", "Influencers", "Search"
                ], k=self._rng.randint(2, 4)),
                "payment_preferences": self._rng.sample([
                    "Credit Card", "Debit Card", "Mobile Payment", "Cash", "Buy Now Pay Later"
                ], k=self._rng.randint(2, 3)),
                "impulse_purchase_frequency": self._rng.choice(["Rare", "Occasional", "Moderate", "Frequent"]),
            },
            "technology_usage": {
                "devices": self._rng.sample([
                    "iPhone", "Android Phone", "MacBook", "Windows PC", "iPad",
                    "Android Tablet", "Smart TV", "Smart Watch", "Smart Speaker"
                ], k=self._rng.randint(3, 5)),
                "primary_device": self._rng.choice(["Smartphone", "Laptop", "Desktop", "Tablet"]),
                "tech_savviness": self._rng.randint(4, 10),
                "app_usage_hours_daily": round(self._rng.uniform(2, 8), 1),
                "smart_home_adoption": self._rng.random() < 0.4,
                "wearables": self._rng.sample(["Smart Watch", "Fitness Tracker", "None"], k=1)[0],
                "ai_tool_usage": self._rng.sample(["ChatGPT", "Copilot", "Claude", "Gemini", "None"], k=self._rng.randint(0, 3)),
            },
            "financial_behavior": {
                "savings_rate": round(self._rng.uniform(0.05, 0.35), 2),
                "investment_active": self._rng.random() < 0.5,
                "investment_types": self._rng.sample([
                    "Stocks", "ETFs", "Bonds", "Real Estate", "Crypto", "Savings", "None"
                ], k=self._rng.randint(1, 4)),
                "credit_usage": self._rng.choice(["Minimal", "Moderate", "Heavy"]),
                "financial_planning": self._rng.choice(["Structured", "Semi-structured", "Informal", "None"]),
            },
            "health_behavior": {
                "exercise_frequency": self._rng.choice(["Daily", "4-5x/week", "2-3x/week", "Weekly", "Rarely"]),
                "diet_consciousness": self._rng.randint(3, 10),
                "sleep_hours": round(self._rng.uniform(5.5, 8.5), 1),
                "wellness_apps_usage": self._rng.random() < 0.5,
                "preventive_care": self._rng.random() < 0.6,
            },
            "social_behavior": {
                "social_circle_size": self._rng.choice(["Small (<10)", "Medium (10-30)", "Large (30-100)", "Very Large (100+)"]),
                "networking_frequency": self._rng.choice(["Weekly", "Monthly", "Quarterly", "Rarely"]),
                "community_involvement": self._rng.sample([
                    "None", "Religious", "Sports", "Professional", "Volunteer", "Parent Groups"
                ], k=self._rng.randint(0, 3)),
                "event_attendance": self._rng.choice(["Frequent", "Occasional", "Rare"]),
            },
        }

        return behavioral

    def _generate_interests(self, demographics: dict[str, Any]) -> dict[str, Any]:
        """Generate interests and lifestyle attributes."""
        # Select hobbies from different categories
        hobbies = []
        for category, hobby_list in self.trait_library.HOBBIES.items():
            if self._rng.random() < 0.7:  # 70% chance to have hobby from each category
                hobbies.extend(self._rng.sample(hobby_list, k=self._rng.randint(1, 2)))

        interests = {
            "hobbies": hobbies[:self._rng.randint(4, 8)],
            "sports": self._rng.sample([
                "Football/Soccer", "Basketball", "Tennis", "Golf", "Swimming",
                "Running", "Cycling", "Yoga", "None"
            ], k=self._rng.randint(1, 3)),
            "entertainment": self._rng.sample([
                "Movies", "TV Series", "Gaming", "Live Music", "Theatre",
                "Comedy Shows", "Museums", "Sports Events"
            ], k=self._rng.randint(2, 4)),
            "travel_frequency": self._rng.choice(["Rarely", "1-2 trips/year", "3-5 trips/year", "Monthly"]),
            "travel_style": self._rng.choice(["Budget", "Mid-range", "Luxury", "Adventure", "Cultural"]),
            "travel_preferences": self._rng.sample([
                "Beach", "City", "Nature", "Adventure", "Historical", "Culinary"
            ], k=self._rng.randint(2, 4)),
            "food_preferences": self._rng.sample([
                "Local Cuisine", "Asian", "Western", "Mediterranean", "Fusion", "Vegetarian", "Organic"
            ], k=self._rng.randint(2, 4)),
            "dining_out_frequency": self._rng.choice(["Rarely", "Weekly", "2-3x/week", "Daily"]),
            "fashion_style": self._rng.choice(["Casual", "Business Casual", "Formal", "Trendy", "Minimalist", "Eclectic"]),
            "fashion_spending": self._rng.choice(["Budget", "Moderate", "Above Average", "Luxury"]),
            "pet_ownership": self._rng.choice(["None", "Dog", "Cat", "Both", "Other"]),
            "reading_preference": self._rng.sample([
                "Fiction", "Non-fiction", "Business", "Self-help", "News", "None"
            ], k=self._rng.randint(1, 3)),
            "music_genres": self._rng.sample([
                "Pop", "Rock", "Hip-Hop", "Classical", "Jazz", "Electronic", "R&B", "Country"
            ], k=self._rng.randint(2, 4)),
        }

        return interests

    def _generate_topic_knowledge(self, demographics: dict[str, Any], topic: str) -> Optional[dict[str, Any]]:
        """Generate topic-specific knowledge and attitudes."""
        if not topic:
            return None

        topic_lower = topic.lower()
        template = None

        # Find matching template
        for key in self.trait_library.TOPIC_KNOWLEDGE_TEMPLATES:
            if key in topic_lower or topic_lower in key:
                template = self.trait_library.TOPIC_KNOWLEDGE_TEMPLATES[key]
                break

        if not template:
            # Generate generic topic knowledge
            return {
                "awareness_level": self._rng.choice(["Expert", "Knowledgeable", "Aware", "Limited", "None"]),
                "interest_level": self._rng.randint(1, 10),
                "purchase_intent": self._rng.randint(1, 10),
                "consideration_factors": self._rng.sample([
                    "Price", "Quality", "Brand", "Reviews", "Features", "Convenience"
                ], k=self._rng.randint(2, 4)),
                "information_sources": self._rng.sample([
                    "Online Research", "Friends/Family", "Experts", "Social Media", "Advertising"
                ], k=self._rng.randint(2, 3)),
            }

        # Generate from template
        topic_knowledge = {}
        for key, options in template.items():
            if isinstance(options, list):
                topic_knowledge[key] = self._rng.choice(options)
            else:
                topic_knowledge[key] = options

        # Add universal attributes
        topic_knowledge["awareness_level"] = self._rng.choice(["Expert", "Knowledgeable", "Aware", "Limited"])
        topic_knowledge["interest_level"] = self._rng.randint(5, 10)
        topic_knowledge["last_purchase_timeframe"] = self._rng.choice(["Within 6 months", "6-12 months", "1-2 years", "2+ years", "Never"])

        return topic_knowledge

    def _generate_cultural_context(self, demographics: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Generate cultural context attributes."""
        region = self.config.region

        cultural_values = self.trait_library.CULTURAL_VALUES.get(region, self.trait_library.CULTURAL_VALUES["us"])

        cultural_context = {
            "cultural_values": self._rng.sample(cultural_values, k=min(3, len(cultural_values))),
            "communication_style": self._rng.choice(["Direct", "Indirect", "High-context", "Low-context"]),
            "formality_preference": self._rng.choice(["Very Formal", "Formal", "Moderate", "Casual", "Very Casual"]),
            "punctuality_expectation": self._rng.choice(["Strict", "Moderate", "Flexible"]),
            "negotiation_style": self._rng.choice(["Competitive", "Collaborative", "Relationship-first", "Task-first"]),
            "gift_giving_importance": self._rng.randint(1, 10),
            "family_involvement_in_decisions": self._rng.randint(1, 10),
        }

        # Add region-specific attributes
        if region == "china":
            cultural_context["guanxi_importance"] = self._rng.randint(5, 10)
            cultural_context["face_consciousness"] = self._rng.randint(5, 10)
        elif region == "southeast_asia":
            cultural_context["harmony_orientation"] = self._rng.randint(5, 10)
            cultural_context["elder_respect"] = self._rng.randint(6, 10)
        elif region == "europe":
            cultural_context["work_life_balance_priority"] = self._rng.randint(6, 10)

        return cultural_context

    def _compile_prompt(
        self,
        demographics: dict[str, Any],
        professional: dict[str, Any],
        psychographics: dict[str, Any],
        behavioral: dict[str, Any],
        interests: dict[str, Any],
        topic_knowledge: Optional[dict[str, Any]],
        cultural_context: Optional[dict[str, Any]]
    ) -> str:
        """Compile all attributes into a comprehensive persona prompt."""
        prompt_parts = []

        # Core identity
        prompt_parts.append(f"""You are a {demographics['age']}-year-old {demographics['gender']} from {demographics['country']}.
You are a {demographics['generation']} living in a {demographics['urban_rural'].lower()} area.
Marital status: {demographics['marital_status']}, Household size: {demographics['household_size']}.""")

        # Professional background
        prompt_parts.append(f"""
PROFESSIONAL BACKGROUND:
- Current role: {professional['occupation']} in {professional['industry']}
- Seniority: {professional['seniority_level']} with {professional['years_experience']} years experience
- Education: {professional['education_level']} in {professional['education_field']}
- Work style: {professional['work_style']}, prefers {professional['remote_work_preference']}
- Career ambition: {professional['career_ambition']}
- Key skills: {', '.join(professional['skills'])}""")

        # Psychographic profile
        prompt_parts.append(f"""
PERSONALITY & VALUES:
- Personality type: {psychographics['personality_type']}
- Core values: {', '.join(psychographics['values_primary'])}
- Decision style: {psychographics['decision_style']}
- Innovation adoption: {psychographics['innovation_adoption']}
- Risk tolerance: {psychographics['risk_tolerance']}/10
- Brand loyalty: {psychographics['brand_loyalty_tendency']}
- Quality consciousness: {psychographics['quality_consciousness']}/10
- Price sensitivity: {psychographics['price_sensitivity']}/10
- Environmental consciousness: {psychographics['environmental_consciousness']}/10""")

        # Behavioral patterns
        prompt_parts.append(f"""
BEHAVIORAL PATTERNS:
- Social media: {behavioral['media_consumption']['social_media_hours_daily']} hours/day on {', '.join(behavioral['media_consumption']['platforms'][:3])}
- News sources: {', '.join(behavioral['media_consumption']['news_sources'][:2])}
- Shopping: {int(behavioral['shopping_behavior']['online_vs_offline']*100)}% online, research-driven: {behavioral['shopping_behavior']['research_before_purchase']}
- Tech savviness: {behavioral['technology_usage']['tech_savviness']}/10
- Primary device: {behavioral['technology_usage']['primary_device']}
- Exercise: {behavioral['health_behavior']['exercise_frequency']}
- Social circle: {behavioral['social_behavior']['social_circle_size']}""")

        # Interests
        prompt_parts.append(f"""
INTERESTS & LIFESTYLE:
- Hobbies: {', '.join(interests['hobbies'][:5])}
- Travel: {interests['travel_frequency']}, style: {interests['travel_style']}
- Dining: {interests['dining_out_frequency']}
- Fashion: {interests['fashion_style']}, spending: {interests['fashion_spending']}""")

        # Topic-specific knowledge
        if topic_knowledge:
            prompt_parts.append(f"""
TOPIC-SPECIFIC CONTEXT ({self.config.topic or 'General'}):
- Awareness level: {topic_knowledge.get('awareness_level', 'N/A')}
- Interest level: {topic_knowledge.get('interest_level', 'N/A')}/10
- Key factors: {json.dumps(topic_knowledge, indent=2)}""")

        # Cultural context
        if cultural_context:
            prompt_parts.append(f"""
CULTURAL CONTEXT:
- Values: {', '.join(cultural_context['cultural_values'])}
- Communication style: {cultural_context['communication_style']}
- Formality preference: {cultural_context['formality_preference']}""")

        # Data provenance
        prompt_parts.append(f"""
DATA PROVENANCE:
- Source: {self.regional_demographics.source}
- Year: {self.regional_demographics.source_year}
- Confidence: {self.regional_demographics.confidence_score:.0%}""")

        return "\n".join(prompt_parts)

    async def generate_persona(self, seed: Optional[int] = None) -> GeneratedPersona:
        """Generate a single comprehensive persona."""
        if seed is not None:
            self.set_seed(seed)

        await self.initialize()

        # Generate all attribute categories
        demographics = self._generate_demographics()
        professional = self._generate_professional(demographics)
        psychographics = self._generate_psychographics(demographics, professional)
        behavioral = self._generate_behavioral(demographics, psychographics)
        interests = self._generate_interests(demographics)
        topic_knowledge = self._generate_topic_knowledge(demographics, self.config.topic) if self.config.include_topic_knowledge else None
        cultural_context = self._generate_cultural_context(demographics) if self.config.include_cultural else None

        # Compile prompt
        full_prompt = self._compile_prompt(
            demographics, professional, psychographics,
            behavioral, interests, topic_knowledge, cultural_context
        )

        return GeneratedPersona(
            demographics=demographics,
            professional=professional,
            psychographics=psychographics,
            behavioral=behavioral,
            interests=interests,
            topic_knowledge=topic_knowledge,
            cultural_context=cultural_context,
            full_prompt=full_prompt,
            confidence_score=self.regional_demographics.confidence_score
        )

    async def generate_personas(self, count: Optional[int] = None) -> list[GeneratedPersona]:
        """Generate multiple personas."""
        count = count or self.config.count
        personas = []

        for i in range(count):
            persona = await self.generate_persona(seed=i)
            personas.append(persona)

        return personas


# ============= Database Integration =============

class PersonaService:
    """Service for managing personas in the database."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(
        self,
        user_id: UUID,
        config: PersonaGenerationConfig,
        name: str,
        description: Optional[str] = None
    ) -> PersonaTemplate:
        """Create a new persona template."""
        template = PersonaTemplate(
            user_id=user_id,
            name=name,
            description=description,
            region=config.region,
            country=config.country,
            sub_region=config.sub_region,
            industry=config.industry,
            topic=config.topic,
            keywords=config.keywords,
            source_type=config.source_type,
            is_active=True,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def generate_and_save_personas(
        self,
        template_id: UUID,
        config: PersonaGenerationConfig,
        count: Optional[int] = None
    ) -> list[PersonaRecord]:
        """Generate personas and save to database."""
        generator = AdvancedPersonaGenerator(config)
        generated = await generator.generate_personas(count)

        records = []
        for persona in generated:
            record = PersonaRecord(
                template_id=template_id,
                demographics=persona.demographics,
                professional=persona.professional,
                psychographics=persona.psychographics,
                behavioral=persona.behavioral,
                interests=persona.interests,
                topic_knowledge=persona.topic_knowledge,
                cultural_context=persona.cultural_context,
                source_type=config.source_type,
                confidence_score=persona.confidence_score,
                full_prompt=persona.full_prompt,
            )
            self.db.add(record)
            records.append(record)

        await self.db.commit()
        return records

    async def get_template(self, template_id: UUID) -> Optional[PersonaTemplate]:
        """Get a persona template by ID."""
        result = await self.db.execute(
            select(PersonaTemplate).where(PersonaTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_personas_by_template(
        self,
        template_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[PersonaRecord]:
        """Get personas for a template."""
        result = await self.db.execute(
            select(PersonaRecord)
            .where(PersonaRecord.template_id == template_id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
