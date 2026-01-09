"""
Generate 100 Realistic AI Personas
Creates diverse, human-like personas for testing and simulation.
"""

import asyncio
import random
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import uuid4
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.persona import PersonaTemplate, PersonaRecord
from app.models.user import User


# ============ DATA POOLS ============

# Demographics
FIRST_NAMES_MALE = [
    "James", "Michael", "Robert", "David", "William", "John", "Richard", "Thomas",
    "Christopher", "Daniel", "Anthony", "Steven", "Kevin", "Brian", "Ronald",
    "Wei", "Jun", "Ming", "Chen", "Kenji", "Hiroshi", "Takeshi", "Mohammed",
    "Ahmed", "Ali", "Carlos", "Juan", "Miguel", "Pedro", "Jose",
    "Marcus", "Jamal", "Terrence", "Deshawn", "Andre",
    "Raj", "Vikram", "Arjun", "Sanjay", "Amit"
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
    "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Margaret", "Betty", "Dorothy",
    "Mei", "Ling", "Xin", "Yuki", "Sakura", "Aiko", "Fatima", "Aisha", "Noor",
    "Maria", "Sofia", "Isabella", "Valentina", "Gabriela",
    "Keisha", "Aaliyah", "Jasmine", "Imani", "Destiny",
    "Priya", "Anita", "Sunita", "Kavita", "Deepa"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Wang", "Li", "Zhang", "Chen", "Liu", "Tanaka", "Yamamoto", "Suzuki",
    "Al-Rashid", "Al-Hassan", "Khan", "Singh", "Patel", "Kumar", "Sharma",
    "Kim", "Park", "Lee", "Nguyen", "Tran", "Mueller", "Schmidt", "Weber"
]

COUNTRIES = [
    {"name": "United States", "region": "North America", "cities": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin", "Seattle", "Denver", "Boston", "Atlanta", "Miami"]},
    {"name": "United Kingdom", "region": "Europe", "cities": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool", "Edinburgh", "Bristol"]},
    {"name": "Germany", "region": "Europe", "cities": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart"]},
    {"name": "France", "region": "Europe", "cities": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Bordeaux"]},
    {"name": "Japan", "region": "Asia Pacific", "cities": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Kyoto", "Fukuoka"]},
    {"name": "Australia", "region": "Asia Pacific", "cities": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"]},
    {"name": "Canada", "region": "North America", "cities": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Edmonton"]},
    {"name": "Singapore", "region": "Asia Pacific", "cities": ["Singapore"]},
    {"name": "India", "region": "Asia Pacific", "cities": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune"]},
    {"name": "Brazil", "region": "Latin America", "cities": ["Sao Paulo", "Rio de Janeiro", "Brasilia", "Salvador", "Fortaleza"]},
    {"name": "Mexico", "region": "Latin America", "cities": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana"]},
    {"name": "South Korea", "region": "Asia Pacific", "cities": ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon"]},
]

EDUCATION_LEVELS = ["High School", "Some College", "Associate's Degree", "Bachelor's Degree", "Master's Degree", "Doctorate", "Professional Degree"]
EDUCATION_FIELDS = ["Business", "Engineering", "Computer Science", "Arts & Humanities", "Social Sciences", "Medicine", "Law", "Education", "Science", "Communications"]

OCCUPATIONS = [
    {"title": "Software Engineer", "industry": "Technology", "level": "Mid-Level"},
    {"title": "Marketing Manager", "industry": "Marketing", "level": "Senior"},
    {"title": "Financial Analyst", "industry": "Finance", "level": "Mid-Level"},
    {"title": "Sales Representative", "industry": "Sales", "level": "Entry-Level"},
    {"title": "Product Manager", "industry": "Technology", "level": "Senior"},
    {"title": "Data Scientist", "industry": "Technology", "level": "Mid-Level"},
    {"title": "HR Specialist", "industry": "Human Resources", "level": "Mid-Level"},
    {"title": "Operations Manager", "industry": "Operations", "level": "Senior"},
    {"title": "Graphic Designer", "industry": "Creative", "level": "Mid-Level"},
    {"title": "Accountant", "industry": "Finance", "level": "Mid-Level"},
    {"title": "Teacher", "industry": "Education", "level": "Mid-Level"},
    {"title": "Nurse", "industry": "Healthcare", "level": "Mid-Level"},
    {"title": "Project Manager", "industry": "Management", "level": "Senior"},
    {"title": "Consultant", "industry": "Consulting", "level": "Senior"},
    {"title": "Entrepreneur", "industry": "Various", "level": "Executive"},
    {"title": "Retail Store Manager", "industry": "Retail", "level": "Mid-Level"},
    {"title": "Real Estate Agent", "industry": "Real Estate", "level": "Mid-Level"},
    {"title": "Chef", "industry": "Hospitality", "level": "Senior"},
    {"title": "Lawyer", "industry": "Legal", "level": "Senior"},
    {"title": "Doctor", "industry": "Healthcare", "level": "Senior"},
    {"title": "Electrician", "industry": "Trades", "level": "Mid-Level"},
    {"title": "Construction Manager", "industry": "Construction", "level": "Senior"},
    {"title": "Customer Service Rep", "industry": "Service", "level": "Entry-Level"},
    {"title": "Bank Manager", "industry": "Finance", "level": "Senior"},
    {"title": "Pharmacist", "industry": "Healthcare", "level": "Senior"},
    {"title": "Freelance Writer", "industry": "Media", "level": "Mid-Level"},
    {"title": "UX Designer", "industry": "Technology", "level": "Mid-Level"},
    {"title": "Insurance Agent", "industry": "Insurance", "level": "Mid-Level"},
    {"title": "Logistics Coordinator", "industry": "Logistics", "level": "Mid-Level"},
    {"title": "Research Scientist", "industry": "Science", "level": "Senior"},
]

PERSONALITY_TYPES = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
                     "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"]

HOBBIES = [
    "Reading", "Travel", "Photography", "Cooking", "Gardening", "Gaming",
    "Hiking", "Running", "Swimming", "Yoga", "Cycling", "Tennis", "Golf",
    "Music", "Movies", "Theatre", "Art", "Writing", "Podcasts", "Crafts",
    "Fishing", "Camping", "DIY Projects", "Volunteering", "Wine Tasting",
    "Dancing", "Martial Arts", "Meditation", "Collecting", "Birdwatching"
]

SOCIAL_MEDIA = ["Facebook", "Instagram", "Twitter", "LinkedIn", "TikTok", "YouTube", "Reddit", "Pinterest", "Snapchat"]

STREAMING_SERVICES = ["Netflix", "Amazon Prime", "Disney+", "HBO Max", "Hulu", "Apple TV+", "Spotify", "YouTube Premium"]

VALUES = ["Family", "Career Success", "Health & Wellness", "Financial Security", "Community",
          "Adventure", "Creativity", "Learning", "Independence", "Social Justice", "Spirituality",
          "Work-Life Balance", "Environmental Sustainability", "Personal Growth", "Tradition"]


def generate_persona(index: int) -> dict:
    """Generate a single realistic persona."""

    # Basic demographics
    gender = random.choice(["Male", "Female"])
    if gender == "Male":
        first_name = random.choice(FIRST_NAMES_MALE)
    else:
        first_name = random.choice(FIRST_NAMES_FEMALE)

    last_name = random.choice(LAST_NAMES)
    age = random.randint(18, 75)

    # Location
    country_data = random.choice(COUNTRIES)
    city = random.choice(country_data["cities"])

    # Age bracket
    if age < 25:
        age_bracket = "18-24"
        generation = "Gen Z"
    elif age < 35:
        age_bracket = "25-34"
        generation = "Millennial"
    elif age < 45:
        age_bracket = "35-44"
        generation = "Millennial" if age < 40 else "Gen X"
    elif age < 55:
        age_bracket = "45-54"
        generation = "Gen X"
    elif age < 65:
        age_bracket = "55-64"
        generation = "Gen X" if age < 60 else "Baby Boomer"
    else:
        age_bracket = "65+"
        generation = "Baby Boomer"

    # Income (correlate with age and occupation)
    base_income = random.randint(30000, 200000)
    if age > 40:
        base_income = int(base_income * 1.3)

    if base_income < 40000:
        income_bracket = "$30,000 - $50,000"
        wealth_class = "Working Class"
    elif base_income < 75000:
        income_bracket = "$50,000 - $75,000"
        wealth_class = "Middle Class"
    elif base_income < 125000:
        income_bracket = "$75,000 - $125,000"
        wealth_class = "Upper Middle Class"
    else:
        income_bracket = "$125,000+"
        wealth_class = "Upper Class"

    # Marital status (correlate with age)
    if age < 25:
        marital_status = random.choices(["Single", "In a Relationship", "Married"], weights=[60, 30, 10])[0]
    elif age < 35:
        marital_status = random.choices(["Single", "In a Relationship", "Married", "Divorced"], weights=[30, 20, 40, 10])[0]
    else:
        marital_status = random.choices(["Single", "Married", "Divorced", "Widowed"], weights=[15, 55, 20, 10])[0]

    # Children
    if marital_status in ["Married", "Divorced", "Widowed"] and age > 28:
        children = random.randint(0, 3)
    else:
        children = 0 if random.random() > 0.2 else random.randint(1, 2)

    # Occupation
    occupation_data = random.choice(OCCUPATIONS)

    # Education
    education_level = random.choice(EDUCATION_LEVELS)
    education_field = random.choice(EDUCATION_FIELDS)

    # Personality
    personality_type = random.choice(PERSONALITY_TYPES)

    # Big Five personality traits (0-1 scale)
    big_five = {
        "openness": round(random.uniform(0.2, 1.0), 2),
        "conscientiousness": round(random.uniform(0.2, 1.0), 2),
        "extraversion": round(random.uniform(0.2, 1.0), 2),
        "agreeableness": round(random.uniform(0.2, 1.0), 2),
        "neuroticism": round(random.uniform(0.1, 0.8), 2),
    }

    # Values
    personal_values = random.sample(VALUES, k=random.randint(3, 5))

    # Hobbies
    personal_hobbies = random.sample(HOBBIES, k=random.randint(3, 6))

    # Social media
    social_platforms = random.sample(SOCIAL_MEDIA, k=random.randint(2, 5))

    # Streaming
    streaming = random.sample(STREAMING_SERVICES, k=random.randint(1, 4))

    # Build the persona record
    demographics = {
        "name": f"{first_name} {last_name}",
        "age": age,
        "age_bracket": age_bracket,
        "gender": gender,
        "country": country_data["name"],
        "region": country_data["region"],
        "city": city,
        "urban_rural": random.choices(["Urban", "Suburban", "Rural"], weights=[45, 40, 15])[0],
        "marital_status": marital_status,
        "household_size": 1 + children + (1 if marital_status == "Married" else 0),
        "children": children,
        "income_personal": income_bracket,
        "wealth_bracket": wealth_class,
        "language_primary": "English",
        "generation": generation,
        "ethnicity": random.choice(["Caucasian", "African American", "Hispanic", "Asian", "Mixed", "Other"]),
    }

    professional = {
        "employment_status": random.choices(["Full-time", "Part-time", "Self-employed", "Retired", "Unemployed"],
                                           weights=[60, 15, 10, 10, 5])[0],
        "occupation": occupation_data["title"],
        "industry": occupation_data["industry"],
        "seniority_level": occupation_data["level"],
        "years_experience": max(0, age - 22 - random.randint(0, 10)),
        "education_level": education_level,
        "education_field": education_field,
        "work_style": random.choice(["Collaborative", "Independent", "Mixed"]),
        "remote_work_preference": random.choice(["Remote", "Hybrid", "In-office"]),
        "job_satisfaction": random.randint(4, 10),
    }

    psychographics = {
        "values_primary": personal_values,
        "personality_type": personality_type,
        "big_five": big_five,
        "risk_tolerance": random.randint(3, 9),
        "change_readiness": random.randint(4, 9),
        "innovation_adoption": random.choice(["Innovator", "Early Adopter", "Early Majority", "Late Majority", "Laggard"]),
        "decision_style": random.choice(["Analytical", "Intuitive", "Balanced", "Impulsive"]),
        "brand_loyalty_tendency": random.choice(["High", "Moderate", "Low"]),
        "price_sensitivity": random.randint(3, 9),
        "quality_consciousness": random.randint(5, 10),
        "environmental_consciousness": random.randint(3, 10),
        "health_consciousness": random.randint(4, 10),
        "life_satisfaction": random.randint(5, 10),
        "optimism": random.randint(4, 10),
        "political_orientation": random.choice(["Conservative", "Center-Right", "Moderate", "Center-Left", "Progressive"]),
    }

    behavioral = {
        "media_consumption": {
            "social_media_hours_daily": round(random.uniform(0.5, 4.0), 1),
            "platforms": social_platforms,
            "news_consumption": random.choice(["Heavy", "Moderate", "Light", "Minimal"]),
            "streaming_services": streaming,
            "podcast_listener": random.choice([True, False]),
        },
        "shopping_behavior": {
            "online_vs_offline": round(random.uniform(0.3, 0.9), 2),
            "research_before_purchase": random.choice([True, False, True]),  # Biased toward yes
            "review_dependency": random.randint(3, 10),
            "impulse_purchase_frequency": random.choice(["Rarely", "Occasionally", "Frequently"]),
        },
        "technology_usage": {
            "primary_device": random.choice(["iPhone", "Android", "Computer"]),
            "tech_savviness": random.randint(4, 10),
            "smart_home_adoption": random.choice([True, False]),
        },
        "financial_behavior": {
            "savings_rate": round(random.uniform(0.05, 0.35), 2),
            "investment_active": random.choice([True, False]),
            "financial_planning": random.choice(["None", "Basic", "Moderate", "Structured", "Comprehensive"]),
        },
    }

    interests = {
        "hobbies": personal_hobbies,
        "travel_frequency": random.choice(["Rarely", "1-2 trips/year", "3-5 trips/year", "6+ trips/year"]),
        "travel_style": random.choice(["Budget", "Mid-range", "Luxury", "Adventure"]),
        "dining_frequency": random.choice(["Rarely", "1-2x/month", "Weekly", "2-3x/week", "Daily"]),
        "fitness_level": random.choice(["Sedentary", "Lightly Active", "Moderately Active", "Very Active"]),
        "pet_ownership": random.choice([None, "Dog", "Cat", "Both", "Other"]),
    }

    return {
        "demographics": demographics,
        "professional": professional,
        "psychographics": psychographics,
        "behavioral": behavioral,
        "interests": interests,
        "source_type": "ai_generated",
        "confidence_score": round(random.uniform(0.8, 0.95), 2),
    }


async def create_personas():
    """Create 100 realistic AI personas in the database."""

    print("Starting persona generation...")

    async with AsyncSessionLocal() as session:
        # Get the test user
        result = await session.execute(
            select(User).where(User.email == "test@agentverse.io")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("Error: Test user not found. Please ensure the test user exists.")
            return

        print(f"Using user: {user.email}")

        # Create a template for these personas
        template = PersonaTemplate(
            id=uuid4(),
            user_id=user.id,
            name="Global Diverse Population",
            description="100 realistic AI personas representing diverse demographics from around the world. Includes varied ages, locations, occupations, and psychographic profiles for comprehensive testing.",
            region="global",
            source_type="ai_generated",
            demographic_config={"age": True, "gender": True, "location": True, "income": True},
            psychographic_config={"values": True, "personality": True, "lifestyle": True},
            behavioral_config={"media": True, "shopping": True, "technology": True},
            professional_config={"occupation": True, "education": True, "industry": True},
            cultural_config={"region": True},
            distributions={
                "age": {"18-24": 0.15, "25-34": 0.25, "35-44": 0.25, "45-54": 0.20, "55+": 0.15},
                "gender": {"Male": 0.49, "Female": 0.51},
            },
            data_completeness=0.95,
            confidence_score=0.90,
            is_active=True,
            is_public=True,
        )

        session.add(template)
        await session.flush()

        print(f"Created template: {template.name} (ID: {template.id})")

        # Generate 100 personas
        personas_created = 0

        for i in range(100):
            persona_data = generate_persona(i)

            # Create full prompt
            demo = persona_data["demographics"]
            prof = persona_data["professional"]
            psych = persona_data["psychographics"]

            full_prompt = f"""You are {demo['name']}, a {demo['age']}-year-old {demo['gender'].lower()} from {demo['city']}, {demo['country']}.

Background:
- Generation: {demo['generation']}
- Marital Status: {demo['marital_status']}
- Household Size: {demo['household_size']} {"(with " + str(demo['children']) + " children)" if demo['children'] > 0 else ""}
- Income Bracket: {demo['income_personal']}
- Social Class: {demo['wealth_bracket']}

Professional:
- Occupation: {prof['occupation']} in {prof['industry']}
- Experience: {prof['years_experience']} years
- Education: {prof['education_level']} in {prof['education_field']}
- Work Style: {prof['work_style']}, prefers {prof['remote_work_preference']} work

Personality & Values:
- Personality Type: {psych['personality_type']}
- Core Values: {', '.join(psych['values_primary'])}
- Decision Style: {psych['decision_style']}
- Innovation Adoption: {psych['innovation_adoption']}
- Risk Tolerance: {psych['risk_tolerance']}/10
- Political Leaning: {psych['political_orientation']}

Interests & Lifestyle:
- Hobbies: {', '.join(persona_data['interests']['hobbies'])}
- Travel: {persona_data['interests']['travel_frequency']} ({persona_data['interests']['travel_style']})
- Fitness: {persona_data['interests']['fitness_level']}

Respond authentically as this person, considering your background, values, and life experiences."""

            persona_record = PersonaRecord(
                id=uuid4(),
                template_id=template.id,
                demographics=persona_data["demographics"],
                professional=persona_data["professional"],
                psychographics=persona_data["psychographics"],
                behavioral=persona_data["behavioral"],
                interests=persona_data["interests"],
                source_type=persona_data["source_type"],
                confidence_score=persona_data["confidence_score"],
                full_prompt=full_prompt,
            )

            session.add(persona_record)
            personas_created += 1

            if personas_created % 10 == 0:
                print(f"  Created {personas_created} personas...")

        await session.commit()

        print(f"\nSuccessfully created {personas_created} personas!")
        print(f"Template ID: {template.id}")
        print(f"\nView personas at: /dashboard/personas")


if __name__ == "__main__":
    asyncio.run(create_personas())
