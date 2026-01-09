"""
AI Content Generator Service
Generates context, descriptions, and questions based on titles and product types.
"""

import os
import json
import random
from typing import Optional, Dict, List, Any
from pydantic import BaseModel


class GeneratedContent(BaseModel):
    """Generated content response."""
    context: Optional[str] = None
    description: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None


class ContentTemplate(BaseModel):
    """Predefined content template."""
    id: str
    name: str
    category: str
    description: str
    context: str
    questions: List[Dict[str, Any]]


# Predefined templates for common scenarios
SCENARIO_TEMPLATES: List[ContentTemplate] = [
    ContentTemplate(
        id="product_launch",
        name="Product Launch Survey",
        category="marketing",
        description="Evaluate consumer response to a new product launch",
        context="""You are evaluating a new product that is about to be launched in the market.
Consider factors like pricing, features, brand reputation, and your personal needs when forming your opinions.
The product aims to solve common pain points in its category and offers innovative features.""",
        questions=[
            {"type": "scale", "text": "How likely are you to purchase this product? (1-10)"},
            {"type": "multiple_choice", "text": "What factor is most important to you?", "options": ["Price", "Quality", "Brand", "Features", "Reviews"]},
            {"type": "open_ended", "text": "What concerns do you have about this product?"},
        ]
    ),
    ContentTemplate(
        id="brand_perception",
        name="Brand Perception Study",
        category="marketing",
        description="Understand how consumers perceive your brand",
        context="""You are being asked about your perception of a specific brand in the market.
Consider your past experiences, what you've heard from others, advertising you've seen,
and your overall impression of the brand's reputation and values.""",
        questions=[
            {"type": "scale", "text": "How favorable is your overall impression of this brand? (1-10)"},
            {"type": "multiple_choice", "text": "What word best describes this brand?", "options": ["Innovative", "Reliable", "Affordable", "Premium", "Trendy"]},
            {"type": "open_ended", "text": "What comes to mind when you think of this brand?"},
        ]
    ),
    ContentTemplate(
        id="election_poll",
        name="Election Poll",
        category="political",
        description="Gauge voter preferences and key issues",
        context="""You are a registered voter being asked about an upcoming election.
Consider the candidates, their platforms, your personal values, and the issues that matter most to you.
Think about both local and national implications of your vote.""",
        questions=[
            {"type": "multiple_choice", "text": "Which candidate do you plan to vote for?", "options": ["Candidate A", "Candidate B", "Undecided", "Will not vote"]},
            {"type": "multiple_choice", "text": "What is the most important issue to you?", "options": ["Economy", "Healthcare", "Education", "Environment", "Security"]},
            {"type": "scale", "text": "How confident are you in your voting decision? (1-10)"},
        ]
    ),
    ContentTemplate(
        id="customer_satisfaction",
        name="Customer Satisfaction Survey",
        category="research",
        description="Measure customer satisfaction with your service",
        context="""You are a customer who has recently used a product or service.
Reflect on your entire experience from discovery to purchase to usage.
Consider factors like ease of use, customer support, value for money, and overall satisfaction.""",
        questions=[
            {"type": "scale", "text": "How satisfied are you with the overall experience? (1-10)"},
            {"type": "scale", "text": "How likely are you to recommend us to others? (1-10)"},
            {"type": "multiple_choice", "text": "What aspect needs the most improvement?", "options": ["Product Quality", "Customer Service", "Pricing", "Delivery", "Website/App"]},
            {"type": "open_ended", "text": "What could we do better?"},
        ]
    ),
    ContentTemplate(
        id="market_research",
        name="Market Research Study",
        category="research",
        description="Understand market trends and consumer behavior",
        context="""You are a consumer in a specific market segment.
Consider your buying habits, preferences, and how you typically make purchasing decisions.
Think about what influences your choices and what you value most in products/services.""",
        questions=[
            {"type": "multiple_choice", "text": "How often do you purchase products in this category?", "options": ["Weekly", "Monthly", "Quarterly", "Yearly", "Rarely"]},
            {"type": "multiple_choice", "text": "Where do you typically make these purchases?", "options": ["Online", "In-store", "Both equally", "Through subscription"]},
            {"type": "scale", "text": "How price-sensitive are you in this category? (1-10)"},
            {"type": "open_ended", "text": "What would make you switch to a different brand?"},
        ]
    ),
    ContentTemplate(
        id="focus_group",
        name="Focus Group Discussion",
        category="qualitative",
        description="Deep-dive qualitative insights from group discussion",
        context="""You are participating in a focus group discussion about a specific topic.
Share your honest opinions, experiences, and thoughts openly.
Feel free to agree or disagree with ideas presented and explain your reasoning.""",
        questions=[
            {"type": "open_ended", "text": "What are your initial thoughts on this concept?"},
            {"type": "open_ended", "text": "How does this compare to what you currently use?"},
            {"type": "scale", "text": "How innovative do you find this idea? (1-10)"},
            {"type": "open_ended", "text": "What would make this more appealing to you?"},
        ]
    ),
    ContentTemplate(
        id="ux_testing",
        name="User Experience Testing",
        category="product",
        description="Evaluate the usability and experience of a product",
        context="""You are testing a digital product (website, app, or software).
Focus on how easy it is to use, how intuitive the interface is, and whether it meets your needs.
Consider both first impressions and deeper functionality as you explore.""",
        questions=[
            {"type": "scale", "text": "How easy was it to complete your intended task? (1-10)"},
            {"type": "scale", "text": "How visually appealing is the interface? (1-10)"},
            {"type": "multiple_choice", "text": "What was the biggest usability issue?", "options": ["Navigation", "Loading speed", "Layout", "Text clarity", "None"]},
            {"type": "open_ended", "text": "What feature would you add or change?"},
        ]
    ),
    ContentTemplate(
        id="pricing_study",
        name="Pricing Study",
        category="marketing",
        description="Determine optimal pricing and price sensitivity",
        context="""You are evaluating a product's pricing in relation to its value.
Consider what you would realistically pay based on your budget, alternatives available,
and the perceived value of the features and benefits offered.""",
        questions=[
            {"type": "scale", "text": "At the current price, how good of a value is this? (1-10)"},
            {"type": "multiple_choice", "text": "At what price would you definitely buy?", "options": ["$19", "$29", "$39", "$49", "$59+"]},
            {"type": "multiple_choice", "text": "At what price would you consider this too expensive?", "options": ["$29", "$39", "$49", "$59", "$79+"]},
            {"type": "open_ended", "text": "What would justify a higher price for this product?"},
        ]
    ),
]


class AIContentGenerator:
    """Service for generating AI content for scenarios and products."""

    def __init__(self):
        """Initialize the content generator."""
        self.templates = SCENARIO_TEMPLATES

    def get_templates(self, category: Optional[str] = None) -> List[ContentTemplate]:
        """Get available templates, optionally filtered by category."""
        if category:
            return [t for t in self.templates if t.category == category]
        return self.templates

    def get_template_by_id(self, template_id: str) -> Optional[ContentTemplate]:
        """Get a specific template by ID."""
        for template in self.templates:
            if template.id == template_id:
                return template
        return None

    async def generate_context(
        self,
        title: str,
        product_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        target_market: Optional[Dict[str, Any]] = None,
    ) -> GeneratedContent:
        """
        Generate context and related content based on title and parameters.
        Uses intelligent pattern matching and templates to generate relevant content.
        """
        title_lower = title.lower()

        # Determine the best approach based on keywords
        context_parts = []
        questions = []
        description = ""

        # Analyze title for key themes
        themes = self._analyze_themes(title_lower)

        # Generate description
        description = self._generate_description(title, themes, product_type, sub_type)

        # Generate context
        context = self._generate_context_text(title, themes, product_type, sub_type, target_market)

        # Generate relevant questions
        questions = self._generate_questions(title, themes, product_type, sub_type)

        # Generate recommendations
        recommendations = self._generate_recommendations(themes, product_type)

        return GeneratedContent(
            context=context,
            description=description,
            questions=questions,
            recommendations=recommendations,
        )

    def _analyze_themes(self, title: str) -> Dict[str, bool]:
        """Analyze title for key themes."""
        themes = {
            "election": any(w in title for w in ["election", "vote", "poll", "candidate", "political", "president"]),
            "product": any(w in title for w in ["product", "launch", "release", "new", "feature"]),
            "brand": any(w in title for w in ["brand", "perception", "awareness", "reputation", "image"]),
            "market": any(w in title for w in ["market", "research", "analysis", "trend", "consumer"]),
            "satisfaction": any(w in title for w in ["satisfaction", "feedback", "experience", "service", "customer"]),
            "pricing": any(w in title for w in ["price", "pricing", "cost", "value", "affordable"]),
            "ux": any(w in title for w in ["ux", "user", "interface", "usability", "experience", "app", "website"]),
            "campaign": any(w in title for w in ["campaign", "ad", "marketing", "advertising", "promotion"]),
            "focus_group": any(w in title for w in ["focus", "group", "discussion", "qualitative", "insight"]),
        }
        return themes

    def _generate_description(
        self,
        title: str,
        themes: Dict[str, bool],
        product_type: Optional[str],
        sub_type: Optional[str],
    ) -> str:
        """Generate a description based on title and themes."""
        descriptions = {
            "election": f"A comprehensive study to understand voter preferences, key issues, and electoral sentiment regarding {title}.",
            "product": f"An in-depth analysis to evaluate consumer response, market potential, and success factors for {title}.",
            "brand": f"A strategic study to measure and understand brand perception, awareness, and positioning for {title}.",
            "market": f"Market research initiative to identify trends, opportunities, and consumer behavior patterns related to {title}.",
            "satisfaction": f"Customer experience evaluation to measure satisfaction levels and identify improvement opportunities for {title}.",
            "pricing": f"Price sensitivity analysis to determine optimal pricing strategy and value perception for {title}.",
            "ux": f"User experience research to evaluate usability, design effectiveness, and user satisfaction for {title}.",
            "campaign": f"Campaign effectiveness study to measure reach, engagement, and impact of {title}.",
            "focus_group": f"Qualitative research to gather in-depth insights and perspectives on {title}.",
        }

        for theme, is_present in themes.items():
            if is_present:
                return descriptions.get(theme, f"Research study to gather insights and data on {title}.")

        # Default description based on product type
        type_descriptions = {
            "predict": f"Predictive analysis to forecast outcomes and trends for {title}.",
            "insight": f"Deep-dive research to uncover motivations and behaviors related to {title}.",
            "simulate": f"Interactive simulation to model scenarios and gather responses for {title}.",
        }

        return type_descriptions.get(product_type or "", f"Comprehensive study to understand perspectives on {title}.")

    def _generate_context_text(
        self,
        title: str,
        themes: Dict[str, bool],
        product_type: Optional[str],
        sub_type: Optional[str],
        target_market: Optional[Dict[str, Any]],
    ) -> str:
        """Generate context text for the scenario."""
        context_templates = {
            "election": f"""You are a registered voter being asked about {title}.

Consider the following when forming your opinions:
- The candidates and their platforms
- Key issues that affect you and your community
- Your personal values and priorities
- What you've heard from news, social media, and people around you
- Your past voting experiences and party affiliations (if any)

Please answer honestly based on your background and beliefs. There are no right or wrong answers.""",

            "product": f"""You are a potential consumer evaluating {title}.

Consider the following factors:
- How this product/service might fit into your daily life
- Its features, benefits, and potential drawbacks
- The price point and value proposition
- Alternative options available in the market
- Reviews and opinions you may have encountered
- Your personal needs and preferences

Please provide your genuine reactions and opinions.""",

            "brand": f"""You are being asked about your perceptions of {title}.

Think about:
- Your past experiences with this brand (if any)
- What you've seen in advertising and media
- What others have said about this brand
- How this brand compares to competitors
- The values and image the brand represents
- Your emotional connection or feelings toward the brand

Share your honest impressions and associations.""",

            "market": f"""You are participating in market research about {title}.

Consider your experiences as a consumer:
- Your purchasing habits and preferences
- How you typically make buying decisions
- What influences your choices (price, quality, convenience, etc.)
- Where you shop and how you discover new products
- Your satisfaction with current options in the market

Your insights will help shape better products and services.""",

            "satisfaction": f"""You are providing feedback about your experience with {title}.

Reflect on your entire customer journey:
- How you discovered and chose this product/service
- The purchase and onboarding experience
- Day-to-day usage and any issues encountered
- Interactions with customer support (if any)
- Overall value received compared to expectations

Please be candid about both positives and areas for improvement.""",

            "pricing": f"""You are evaluating the pricing of {title}.

Consider these aspects:
- Your personal budget and spending priorities
- The value you perceive in this product/service
- Prices of similar offerings in the market
- What features or benefits justify different price points
- Your willingness to pay for premium options

Share your honest assessment of fair value.""",

            "ux": f"""You are testing the user experience of {title}.

Focus on:
- How intuitive and easy to use the interface is
- Whether you can accomplish your goals efficiently
- Visual design and aesthetic appeal
- Any frustrations or confusion you encounter
- Features you find helpful or missing
- Overall satisfaction with the experience

Provide detailed feedback about your journey.""",

            "campaign": f"""You are being asked about {title} marketing campaign.

Think about:
- Where and how you encountered this campaign
- Your initial reaction and impression
- How memorable and distinctive it was
- Whether it influenced your perception or behavior
- The message and emotional impact
- How it compares to other marketing you've seen

Share your genuine reactions and thoughts.""",

            "focus_group": f"""You are participating in a focus group discussion about {title}.

Guidelines for participation:
- Share your honest opinions and experiences
- Feel free to agree or disagree with others
- Explain the reasoning behind your views
- Ask questions if anything is unclear
- Build on ideas that resonate with you

Your unique perspective is valuable to this discussion.""",
        }

        # Find the most relevant context
        for theme, is_present in themes.items():
            if is_present:
                context = context_templates.get(theme)
                if context:
                    # Add target market context if available
                    if target_market:
                        regions = target_market.get("regions", [])
                        countries = target_market.get("countries", [])
                        if regions or countries:
                            locations = ", ".join(regions + countries)
                            context += f"\n\nNote: This study focuses on perspectives from {locations}."
                    return context

        # Default context
        return f"""You are participating in a research study about {title}.

Please provide your honest opinions and perspectives based on:
- Your personal experiences and background
- Your knowledge and beliefs on this topic
- Your genuine reactions and feelings

There are no right or wrong answers. Your authentic response is what matters most."""

    def _generate_questions(
        self,
        title: str,
        themes: Dict[str, bool],
        product_type: Optional[str],
        sub_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Generate relevant questions based on themes."""
        questions = []

        # Theme-based questions
        if themes.get("election"):
            questions = [
                {"type": "multiple_choice", "text": "Which candidate do you currently support?", "options": ["Candidate A", "Candidate B", "Third Party", "Undecided", "Will not vote"]},
                {"type": "multiple_choice", "text": "What is the most important issue in this election?", "options": ["Economy", "Healthcare", "Immigration", "Climate", "Education", "National Security"]},
                {"type": "scale", "text": "How likely are you to vote in this election? (1-10)"},
                {"type": "open_ended", "text": "What would change your vote?"},
            ]
        elif themes.get("product"):
            questions = [
                {"type": "scale", "text": "How interested are you in this product? (1-10)"},
                {"type": "scale", "text": "How likely are you to purchase this product? (1-10)"},
                {"type": "multiple_choice", "text": "What feature is most important to you?", "options": ["Price", "Quality", "Design", "Features", "Brand"]},
                {"type": "open_ended", "text": "What would make this product more appealing to you?"},
            ]
        elif themes.get("brand"):
            questions = [
                {"type": "scale", "text": "How favorable is your impression of this brand? (1-10)"},
                {"type": "scale", "text": "How likely are you to recommend this brand? (1-10)"},
                {"type": "multiple_choice", "text": "What word best describes this brand?", "options": ["Innovative", "Reliable", "Affordable", "Premium", "Trustworthy"]},
                {"type": "open_ended", "text": "What comes to mind when you think of this brand?"},
            ]
        elif themes.get("satisfaction"):
            questions = [
                {"type": "scale", "text": "How satisfied are you overall? (1-10)"},
                {"type": "scale", "text": "How likely are you to recommend us? (1-10)"},
                {"type": "multiple_choice", "text": "What aspect needs the most improvement?", "options": ["Product Quality", "Customer Service", "Pricing", "Delivery", "Website/App"]},
                {"type": "open_ended", "text": "What could we do better?"},
            ]
        elif themes.get("pricing"):
            questions = [
                {"type": "scale", "text": "How good of a value is this at the current price? (1-10)"},
                {"type": "multiple_choice", "text": "Compared to alternatives, this is priced:", "options": ["Too Low", "About Right", "Slightly High", "Too High"]},
                {"type": "multiple_choice", "text": "What price would you definitely buy at?", "options": ["Current -30%", "Current -20%", "Current -10%", "Current Price", "Current +10%"]},
                {"type": "open_ended", "text": "What would justify a premium price?"},
            ]
        else:
            # Default questions based on product type
            if product_type == "predict":
                questions = [
                    {"type": "scale", "text": "How confident are you in your prediction? (1-10)"},
                    {"type": "multiple_choice", "text": "What is your prediction?", "options": ["Option A", "Option B", "Option C", "Undecided"]},
                    {"type": "open_ended", "text": "What factors influenced your prediction?"},
                ]
            elif product_type == "insight":
                questions = [
                    {"type": "open_ended", "text": "What are your initial thoughts on this topic?"},
                    {"type": "scale", "text": "How strongly do you feel about this? (1-10)"},
                    {"type": "open_ended", "text": "What experiences have shaped your views?"},
                ]
            else:
                questions = [
                    {"type": "scale", "text": "How would you rate your overall experience? (1-10)"},
                    {"type": "multiple_choice", "text": "Which aspect is most important to you?", "options": ["Quality", "Price", "Service", "Convenience", "Other"]},
                    {"type": "open_ended", "text": "Please share any additional thoughts."},
                ]

        return questions

    def _generate_recommendations(
        self,
        themes: Dict[str, bool],
        product_type: Optional[str],
    ) -> List[str]:
        """Generate recommendations for the study."""
        recommendations = [
            "Consider increasing sample size for higher statistical confidence",
            "Segment results by demographic groups for deeper insights",
            "Compare results against industry benchmarks",
            "Follow up with qualitative interviews for key findings",
        ]

        if themes.get("election"):
            recommendations.append("Account for likely voter models in analysis")
        if themes.get("product"):
            recommendations.append("Test multiple price points to find optimal pricing")
        if themes.get("brand"):
            recommendations.append("Include competitor brands for comparative analysis")

        return recommendations[:4]  # Return top 4 recommendations


# Singleton instance
_generator_instance: Optional[AIContentGenerator] = None


def get_ai_content_generator() -> AIContentGenerator:
    """Get the singleton AI content generator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = AIContentGenerator()
    return _generator_instance
