"""
Persona Generation Service
Generates synthetic personas for AI agent simulation.
Supports both random generation and real census-based data.
"""

import random
from typing import Any, Optional

from pydantic import BaseModel


# Standard mapping for census-compatible age brackets
CENSUS_AGE_BRACKETS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

# Standard mapping for census-compatible income brackets
CENSUS_INCOME_BRACKETS = [
    "Under $25,000",
    "$25,000 - $50,000",
    "$50,000 - $75,000",
    "$75,000 - $100,000",
    "$100,000 - $150,000",
    "Over $150,000",
]

# Standard mapping for census-compatible education levels
CENSUS_EDUCATION_LEVELS = [
    "Less than high school",
    "High school",
    "Some college",
    "Associate degree",
    "Bachelor's degree",
    "Graduate degree",
]


class Persona(BaseModel):
    """A synthetic persona for simulation."""
    index: int
    demographics: dict[str, Any]
    psychographics: dict[str, Any]
    behavioral_context: str
    full_prompt: str


class DemographicDistribution(BaseModel):
    """Distribution settings for demographics."""
    age_range: tuple[int, int] = (18, 65)
    age_distribution: str = "normal"  # normal, uniform, skewed_young, skewed_old

    genders: list[str] = ["Male", "Female", "Non-binary"]
    gender_weights: list[float] = [0.48, 0.48, 0.04]

    income_brackets: list[str] = [
        "Under $25,000",
        "$25,000 - $50,000",
        "$50,000 - $75,000",
        "$75,000 - $100,000",
        "$100,000 - $150,000",
        "Over $150,000",
    ]
    income_weights: list[float] = [0.15, 0.25, 0.25, 0.15, 0.12, 0.08]

    education_levels: list[str] = [
        "High school",
        "Some college",
        "Associate degree",
        "Bachelor's degree",
        "Master's degree",
        "Doctoral degree",
    ]
    education_weights: list[float] = [0.25, 0.20, 0.10, 0.28, 0.12, 0.05]

    regions: list[str] = ["Urban", "Suburban", "Rural"]
    region_weights: list[float] = [0.40, 0.45, 0.15]

    occupations: list[str] = [
        "Professional",
        "Technical",
        "Administrative",
        "Sales",
        "Service",
        "Manufacturing",
        "Student",
        "Retired",
        "Self-employed",
        "Unemployed",
    ]
    occupation_weights: list[float] = [0.20, 0.15, 0.12, 0.10, 0.12, 0.08, 0.08, 0.07, 0.05, 0.03]


class PsychographicProfile(BaseModel):
    """Psychographic attributes for personas."""
    values_orientation: str  # traditional, moderate, progressive
    risk_tolerance: int  # 1-10
    technology_adoption: str  # innovator, early_adopter, early_majority, late_majority, laggard
    decision_style: str  # analytical, intuitive, dependent, spontaneous
    brand_loyalty: str  # high, moderate, low


class PersonaGenerator:
    """Generate synthetic personas for simulation."""

    def __init__(
        self,
        distribution: Optional[DemographicDistribution] = None,
        seed: Optional[int] = None,
    ):
        self.distribution = distribution or DemographicDistribution()
        if seed is not None:
            random.seed(seed)

    def generate_demographics(self) -> dict[str, Any]:
        """Generate demographic attributes for a persona."""
        dist = self.distribution

        # Age generation based on distribution type
        if dist.age_distribution == "normal":
            age = int(random.gauss(
                (dist.age_range[0] + dist.age_range[1]) / 2,
                (dist.age_range[1] - dist.age_range[0]) / 4
            ))
        elif dist.age_distribution == "skewed_young":
            age = int(random.triangular(
                dist.age_range[0], dist.age_range[1],
                dist.age_range[0] + (dist.age_range[1] - dist.age_range[0]) * 0.3
            ))
        elif dist.age_distribution == "skewed_old":
            age = int(random.triangular(
                dist.age_range[0], dist.age_range[1],
                dist.age_range[0] + (dist.age_range[1] - dist.age_range[0]) * 0.7
            ))
        else:
            age = random.randint(*dist.age_range)

        age = max(dist.age_range[0], min(dist.age_range[1], age))

        return {
            "age": age,
            "gender": random.choices(dist.genders, weights=dist.gender_weights)[0],
            "income_bracket": random.choices(dist.income_brackets, weights=dist.income_weights)[0],
            "education": random.choices(dist.education_levels, weights=dist.education_weights)[0],
            "location_type": random.choices(dist.regions, weights=dist.region_weights)[0],
            "occupation": random.choices(dist.occupations, weights=dist.occupation_weights)[0],
        }

    def generate_psychographics(self, demographics: dict[str, Any]) -> dict[str, Any]:
        """Generate psychographic profile based on demographics."""
        age = demographics.get("age", 35)

        # Values tend to correlate with age
        if age < 30:
            values_weights = [0.2, 0.3, 0.5]
        elif age > 55:
            values_weights = [0.5, 0.3, 0.2]
        else:
            values_weights = [0.33, 0.34, 0.33]

        values_orientation = random.choices(
            ["traditional", "moderate", "progressive"],
            weights=values_weights
        )[0]

        # Technology adoption correlates with age
        if age < 30:
            tech_weights = [0.15, 0.35, 0.30, 0.15, 0.05]
        elif age < 45:
            tech_weights = [0.05, 0.20, 0.40, 0.25, 0.10]
        else:
            tech_weights = [0.02, 0.10, 0.30, 0.35, 0.23]

        technology_adoption = random.choices(
            ["innovator", "early_adopter", "early_majority", "late_majority", "laggard"],
            weights=tech_weights
        )[0]

        return {
            "values_orientation": values_orientation,
            "risk_tolerance": random.randint(1, 10),
            "technology_adoption": technology_adoption,
            "decision_style": random.choice(["analytical", "intuitive", "dependent", "spontaneous"]),
            "brand_loyalty": random.choice(["high", "moderate", "low"]),
        }

    def generate_behavioral_context(
        self,
        demographics: dict[str, Any],
        psychographics: dict[str, Any],
    ) -> str:
        """Generate a behavioral context statement."""
        age = demographics["age"]
        occupation = demographics["occupation"]
        income = demographics["income_bracket"]
        values = psychographics["values_orientation"]
        risk = psychographics["risk_tolerance"]

        contexts = []

        # Income-based context
        if "Under" in income or "$25,000" in income:
            contexts.append("budget-conscious and carefully considers purchases")
        elif "150,000" in income:
            contexts.append("has disposable income for quality products")

        # Risk-based context
        if risk <= 3:
            contexts.append("prefers established brands and avoids new products")
        elif risk >= 8:
            contexts.append("enjoys trying new products and experiences")

        # Values-based context
        if values == "traditional":
            contexts.append("values tradition and established practices")
        elif values == "progressive":
            contexts.append("open to new ideas and social change")

        # Occupation-based context
        if occupation == "Student":
            contexts.append("balancing education with limited budget")
        elif occupation == "Retired":
            contexts.append("has time for research and values quality")

        return "; ".join(contexts) if contexts else "typical consumer behavior"

    def compile_persona_prompt(
        self,
        demographics: dict[str, Any],
        psychographics: dict[str, Any],
        behavioral_context: str,
    ) -> str:
        """Compile the full persona prompt for LLM."""
        return f"""You are simulating a person with these characteristics:

DEMOGRAPHICS:
- Age: {demographics['age']} years old
- Gender: {demographics['gender']}
- Location: {demographics['location_type']} area
- Education: {demographics['education']}
- Income: {demographics['income_bracket']}
- Occupation: {demographics['occupation']}

PSYCHOGRAPHICS:
- Values: {psychographics['values_orientation']}
- Risk tolerance: {psychographics['risk_tolerance']}/10
- Technology adoption: {psychographics['technology_adoption']}
- Decision style: {psychographics['decision_style']}
- Brand loyalty: {psychographics['brand_loyalty']}

BEHAVIORAL CONTEXT:
This person {behavioral_context}.

INSTRUCTIONS:
Respond as this person would. Consider your demographics, values, and circumstances when making decisions. Provide realistic responses that reflect this persona's likely behavior. Be authentic to this character."""

    def generate_persona(self, index: int) -> Persona:
        """Generate a complete persona."""
        demographics = self.generate_demographics()
        psychographics = self.generate_psychographics(demographics)
        behavioral_context = self.generate_behavioral_context(demographics, psychographics)
        full_prompt = self.compile_persona_prompt(demographics, psychographics, behavioral_context)

        return Persona(
            index=index,
            demographics=demographics,
            psychographics=psychographics,
            behavioral_context=behavioral_context,
            full_prompt=full_prompt,
        )

    def generate_population(
        self,
        count: int,
        custom_distribution: Optional[dict] = None,
    ) -> list[Persona]:
        """Generate a population of personas.

        Handles both backend format (DemographicDistribution fields) and
        frontend format (age_distribution/gender_distribution as dicts).
        """
        if custom_distribution:
            # Check if it's frontend format (dict values in age_distribution/gender_distribution)
            if isinstance(custom_distribution.get("age_distribution"), dict):
                # Convert frontend format to backend format
                converted = self._convert_frontend_demographics(custom_distribution)
                self.distribution = DemographicDistribution(**converted)
            else:
                # Already in backend format
                self.distribution = DemographicDistribution(**custom_distribution)

        return [self.generate_persona(i) for i in range(count)]

    def _convert_frontend_demographics(self, frontend_demo: dict) -> dict:
        """Convert frontend demographics format to backend format."""
        result = {}

        # Convert age distribution
        age_dist = frontend_demo.get("age_distribution", {})
        if age_dist:
            # Calculate age range from keys like "18-24", "25-34", etc.
            ages = []
            for key in age_dist.keys():
                if "-" in key:
                    low, high = key.split("-")
                    ages.extend([int(low), int(high)])
                elif "+" in key:
                    # Handle "55+"
                    ages.append(int(key.replace("+", "")))
                    ages.append(75)  # Assume max age of 75
            if ages:
                result["age_range"] = (min(ages), max(ages))
            result["age_distribution"] = "normal"  # Default distribution

        # Convert gender distribution
        gender_dist = frontend_demo.get("gender_distribution", {})
        if gender_dist:
            genders = list(gender_dist.keys())
            total = sum(gender_dist.values())
            if total > 0:
                weights = [v / total for v in gender_dist.values()]
                result["genders"] = genders
                result["gender_weights"] = weights

        # Convert income distribution if present
        income_dist = frontend_demo.get("income_distribution", {})
        if income_dist:
            result["income_brackets"] = list(income_dist.keys())
            total = sum(income_dist.values())
            if total > 0:
                result["income_weights"] = [v / total for v in income_dist.values()]

        # Convert education distribution if present
        edu_dist = frontend_demo.get("education_distribution", {})
        if edu_dist:
            result["education_levels"] = list(edu_dist.keys())
            total = sum(edu_dist.values())
            if total > 0:
                result["education_weights"] = [v / total for v in edu_dist.values()]

        # Convert region distribution if present
        region_dist = frontend_demo.get("region_distribution", {})
        if region_dist:
            result["regions"] = list(region_dist.keys())
            total = sum(region_dist.values())
            if total > 0:
                result["region_weights"] = [v / total for v in region_dist.values()]

        return result


class CensusBasedDistribution(BaseModel):
    """Distribution settings based on real census data."""

    # Age distribution from census (percentages)
    age_distribution: dict[str, float] = {
        "18-24": 0.12,
        "25-34": 0.18,
        "35-44": 0.16,
        "45-54": 0.17,
        "55-64": 0.17,
        "65+": 0.20,
    }

    # Gender distribution from census
    gender_distribution: dict[str, float] = {
        "Male": 0.49,
        "Female": 0.51,
    }

    # Income distribution from census
    income_distribution: dict[str, float] = {
        "Under $25,000": 0.18,
        "$25,000 - $50,000": 0.21,
        "$50,000 - $75,000": 0.17,
        "$75,000 - $100,000": 0.13,
        "$100,000 - $150,000": 0.15,
        "Over $150,000": 0.16,
    }

    # Education distribution from census
    education_distribution: dict[str, float] = {
        "Less than high school": 0.11,
        "High school": 0.27,
        "Some college": 0.20,
        "Associate degree": 0.09,
        "Bachelor's degree": 0.21,
        "Graduate degree": 0.12,
    }

    # Occupation distribution from census
    occupation_distribution: dict[str, float] = {
        "Professional": 0.40,
        "Service": 0.18,
        "Sales/Administrative": 0.20,
        "Technical/Construction": 0.10,
        "Manufacturing/Transportation": 0.12,
    }

    # Region type distribution (can be customized)
    region_distribution: dict[str, float] = {
        "Urban": 0.40,
        "Suburban": 0.45,
        "Rural": 0.15,
    }

    # Data source metadata
    source: str = "US Census Bureau ACS 5-Year"
    source_year: int = 2022
    region_code: Optional[str] = None
    confidence_score: float = 0.9


class CensusBasedPersonaGenerator:
    """
    Generate personas using real census data distributions.

    This generator uses official census data to create demographically
    accurate personas that reflect real-world population distributions.
    """

    def __init__(
        self,
        census_distribution: Optional[CensusBasedDistribution] = None,
        seed: Optional[int] = None,
    ):
        """
        Initialize with census-based distribution.

        Args:
            census_distribution: Pre-loaded census distribution data
            seed: Random seed for reproducibility
        """
        self.distribution = census_distribution or CensusBasedDistribution()
        if seed is not None:
            random.seed(seed)

    @classmethod
    def from_regional_profile(cls, regional_profile_data: dict) -> "CensusBasedPersonaGenerator":
        """
        Create generator from a stored regional profile.

        Args:
            regional_profile_data: Regional profile demographics dict
        """
        dist = CensusBasedDistribution()

        demographics = regional_profile_data.get("demographics", {})

        if "age_distribution" in demographics:
            dist.age_distribution = demographics["age_distribution"]
        if "gender_distribution" in demographics:
            dist.gender_distribution = demographics["gender_distribution"]
        if "income_distribution" in demographics:
            dist.income_distribution = demographics["income_distribution"]
        if "education_distribution" in demographics:
            dist.education_distribution = demographics["education_distribution"]
        if "occupation_distribution" in demographics:
            dist.occupation_distribution = demographics["occupation_distribution"]

        dist.region_code = regional_profile_data.get("region_code")
        dist.confidence_score = regional_profile_data.get("confidence_score", 0.9)

        return cls(census_distribution=dist)

    def _sample_from_distribution(self, distribution: dict[str, float]) -> str:
        """Sample a value based on weighted distribution."""
        items = list(distribution.keys())
        weights = list(distribution.values())

        # Normalize weights if they don't sum to 1
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return random.choices(items, weights=weights)[0]

    def _age_bracket_to_age(self, bracket: str) -> int:
        """Convert age bracket to specific age within range."""
        bracket_ranges = {
            "18-24": (18, 24),
            "25-34": (25, 34),
            "35-44": (35, 44),
            "45-54": (45, 54),
            "55-64": (55, 64),
            "65+": (65, 85),
        }

        if bracket in bracket_ranges:
            low, high = bracket_ranges[bracket]
            return random.randint(low, high)

        # Try to parse custom brackets
        if "-" in bracket:
            parts = bracket.split("-")
            try:
                return random.randint(int(parts[0]), int(parts[1]))
            except ValueError:
                pass
        elif "+" in bracket:
            try:
                base = int(bracket.replace("+", ""))
                return random.randint(base, base + 20)
            except ValueError:
                pass

        return random.randint(30, 50)  # Default fallback

    def generate_demographics(self) -> dict[str, Any]:
        """Generate demographically accurate attributes."""
        age_bracket = self._sample_from_distribution(self.distribution.age_distribution)
        age = self._age_bracket_to_age(age_bracket)

        return {
            "age": age,
            "age_bracket": age_bracket,
            "gender": self._sample_from_distribution(self.distribution.gender_distribution),
            "income_bracket": self._sample_from_distribution(self.distribution.income_distribution),
            "education": self._sample_from_distribution(self.distribution.education_distribution),
            "occupation": self._sample_from_distribution(self.distribution.occupation_distribution),
            "location_type": self._sample_from_distribution(self.distribution.region_distribution),
            "data_source": self.distribution.source,
            "source_year": self.distribution.source_year,
        }

    def generate_psychographics(self, demographics: dict[str, Any]) -> dict[str, Any]:
        """
        Generate psychographic profile based on demographics.
        Uses research-backed correlations between demographics and psychographics.
        """
        age = demographics.get("age", 35)
        education = demographics.get("education", "")
        income = demographics.get("income_bracket", "")

        # Values orientation correlates with age and education
        if age < 30:
            values_weights = [0.2, 0.3, 0.5]
        elif age > 55:
            values_weights = [0.5, 0.3, 0.2]
        else:
            values_weights = [0.33, 0.34, 0.33]

        # Adjust for education
        if "Graduate" in education or "Bachelor" in education:
            values_weights = [
                values_weights[0] * 0.8,
                values_weights[1],
                values_weights[2] * 1.2
            ]

        values_orientation = random.choices(
            ["traditional", "moderate", "progressive"],
            weights=values_weights
        )[0]

        # Technology adoption correlates with age
        if age < 30:
            tech_weights = [0.15, 0.35, 0.30, 0.15, 0.05]
        elif age < 45:
            tech_weights = [0.05, 0.20, 0.40, 0.25, 0.10]
        elif age < 60:
            tech_weights = [0.03, 0.12, 0.35, 0.30, 0.20]
        else:
            tech_weights = [0.02, 0.08, 0.25, 0.35, 0.30]

        technology_adoption = random.choices(
            ["innovator", "early_adopter", "early_majority", "late_majority", "laggard"],
            weights=tech_weights
        )[0]

        # Risk tolerance correlates with age and income
        base_risk = 5
        if age < 35:
            base_risk += 2
        elif age > 55:
            base_risk -= 2

        if "150,000" in income or "100,000" in income:
            base_risk += 1
        elif "Under" in income or "25,000" in income:
            base_risk -= 1

        risk_tolerance = max(1, min(10, base_risk + random.randint(-2, 2)))

        # Decision style
        if "Graduate" in education or "Bachelor" in education:
            decision_weights = [0.4, 0.25, 0.15, 0.20]
        else:
            decision_weights = [0.25, 0.30, 0.25, 0.20]

        decision_style = random.choices(
            ["analytical", "intuitive", "dependent", "spontaneous"],
            weights=decision_weights
        )[0]

        # Brand loyalty correlates with age
        if age > 50:
            loyalty_weights = [0.5, 0.35, 0.15]
        elif age < 30:
            loyalty_weights = [0.2, 0.35, 0.45]
        else:
            loyalty_weights = [0.3, 0.4, 0.3]

        brand_loyalty = random.choices(
            ["high", "moderate", "low"],
            weights=loyalty_weights
        )[0]

        return {
            "values_orientation": values_orientation,
            "risk_tolerance": risk_tolerance,
            "technology_adoption": technology_adoption,
            "decision_style": decision_style,
            "brand_loyalty": brand_loyalty,
        }

    def generate_behavioral_context(
        self,
        demographics: dict[str, Any],
        psychographics: dict[str, Any],
    ) -> str:
        """Generate behavioral context statement."""
        age = demographics["age"]
        occupation = demographics.get("occupation", "")
        income = demographics.get("income_bracket", "")
        education = demographics.get("education", "")
        values = psychographics["values_orientation"]
        risk = psychographics["risk_tolerance"]
        tech = psychographics["technology_adoption"]

        contexts = []

        # Income-based context
        if "Under" in income or "25,000 - $50,000" in income:
            contexts.append("budget-conscious and carefully considers purchases")
        elif "150,000" in income:
            contexts.append("has disposable income for quality products and experiences")

        # Risk-based context
        if risk <= 3:
            contexts.append("prefers established brands and avoids unfamiliar products")
        elif risk >= 8:
            contexts.append("enjoys trying new products and experiences")

        # Technology context
        if tech in ["innovator", "early_adopter"]:
            contexts.append("actively seeks out new technology and digital solutions")
        elif tech == "laggard":
            contexts.append("prefers traditional methods over new technology")

        # Values-based context
        if values == "traditional":
            contexts.append("values tradition, family, and established practices")
        elif values == "progressive":
            contexts.append("open to new ideas and social change")

        # Education context
        if "Graduate" in education:
            contexts.append("values research and data-driven decisions")

        # Occupation-based context
        if "Professional" in occupation:
            contexts.append("career-oriented with professional aspirations")
        elif "Service" in occupation:
            contexts.append("values customer interaction and service quality")

        # Age-based context
        if age < 25:
            contexts.append("digitally native and influenced by social media")
        elif age > 60:
            contexts.append("values quality and reliability over novelty")

        return "; ".join(contexts[:4]) if contexts else "typical consumer behavior"

    def compile_persona_prompt(
        self,
        demographics: dict[str, Any],
        psychographics: dict[str, Any],
        behavioral_context: str,
    ) -> str:
        """Compile the full persona prompt for LLM with data provenance."""
        data_note = f"Based on {self.distribution.source} ({self.distribution.source_year})"
        if self.distribution.region_code:
            data_note += f" - Region: {self.distribution.region_code}"

        return f"""You are simulating a person with these characteristics:

DEMOGRAPHICS (Census-based):
- Age: {demographics['age']} years old ({demographics.get('age_bracket', 'N/A')})
- Gender: {demographics['gender']}
- Location: {demographics['location_type']} area
- Education: {demographics['education']}
- Income: {demographics['income_bracket']}
- Occupation: {demographics['occupation']}

PSYCHOGRAPHICS (Research-backed):
- Values: {psychographics['values_orientation']}
- Risk tolerance: {psychographics['risk_tolerance']}/10
- Technology adoption: {psychographics['technology_adoption']}
- Decision style: {psychographics['decision_style']}
- Brand loyalty: {psychographics['brand_loyalty']}

BEHAVIORAL CONTEXT:
This person {behavioral_context}.

DATA PROVENANCE:
{data_note}
Confidence Score: {self.distribution.confidence_score:.0%}

INSTRUCTIONS:
Respond as this person would. Consider your demographics, values, and circumstances when making decisions. Your responses should reflect the statistical likelihood of someone with these characteristics. Be authentic and consistent with your persona's profile."""

    def generate_persona(self, index: int) -> Persona:
        """Generate a complete census-based persona."""
        demographics = self.generate_demographics()
        psychographics = self.generate_psychographics(demographics)
        behavioral_context = self.generate_behavioral_context(demographics, psychographics)
        full_prompt = self.compile_persona_prompt(demographics, psychographics, behavioral_context)

        return Persona(
            index=index,
            demographics=demographics,
            psychographics=psychographics,
            behavioral_context=behavioral_context,
            full_prompt=full_prompt,
        )

    def generate_population(
        self,
        count: int,
        custom_distribution: Optional[dict] = None,
    ) -> list[Persona]:
        """
        Generate a population of census-based personas.

        Args:
            count: Number of personas to generate
            custom_distribution: Optional custom distribution overrides
        """
        if custom_distribution:
            # Apply custom distribution overrides
            if "age_distribution" in custom_distribution:
                self.distribution.age_distribution = custom_distribution["age_distribution"]
            if "gender_distribution" in custom_distribution:
                self.distribution.gender_distribution = custom_distribution["gender_distribution"]
            if "income_distribution" in custom_distribution:
                self.distribution.income_distribution = custom_distribution["income_distribution"]
            if "education_distribution" in custom_distribution:
                self.distribution.education_distribution = custom_distribution["education_distribution"]
            if "occupation_distribution" in custom_distribution:
                self.distribution.occupation_distribution = custom_distribution["occupation_distribution"]
            if "region_distribution" in custom_distribution:
                self.distribution.region_distribution = custom_distribution["region_distribution"]

        return [self.generate_persona(i) for i in range(count)]


def get_persona_generator(
    use_census_data: bool = True,
    regional_profile: Optional[dict] = None,
    seed: Optional[int] = None,
) -> PersonaGenerator | CensusBasedPersonaGenerator:
    """
    Factory function to get appropriate persona generator.

    Args:
        use_census_data: Whether to use census-based generation
        regional_profile: Optional pre-loaded regional profile data
        seed: Random seed for reproducibility

    Returns:
        Either a CensusBasedPersonaGenerator or standard PersonaGenerator
    """
    if use_census_data:
        if regional_profile:
            return CensusBasedPersonaGenerator.from_regional_profile(regional_profile)
        return CensusBasedPersonaGenerator(seed=seed)
    return PersonaGenerator(seed=seed)
