import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

// OpenRouter API configuration
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

// Use GPT-4o-mini for fast, cheap generation
const MODEL = 'openai/gpt-4o-mini';

interface GeneratePersonasRequest {
  template_id?: string;
  region: string;
  country?: string;
  sub_region?: string;
  topic?: string;
  industry?: string;
  keywords?: string[];
  count?: number;
  include_psychographics?: boolean;
  include_behavioral?: boolean;
  include_cultural?: boolean;
  include_topic_knowledge?: boolean;
}

interface GeneratedPersona {
  id: string;
  name: string;
  age: number;
  gender: string;
  occupation: string;
  income_bracket: string;
  education_level: string;
  location: string;
  personality_traits: string[];
  values: string[];
  interests: string[];
  pain_points: string[];
  goals: string[];
  communication_style: string;
  decision_making_style: string;
  brand_preferences?: string[];
  media_consumption?: string[];
  cultural_context?: string;
  topic_knowledge?: string;
  behavioral_patterns?: string[];
}

interface GeneratePersonasResponse {
  count: number;
  template_id: string | null;
  sample_personas: GeneratedPersona[];
  generation_config: Record<string, unknown>;
}

const SYSTEM_PROMPT = `You are an expert market researcher and persona creator. You create realistic, diverse consumer personas based on demographic and psychographic parameters.

When generating personas, ensure:
1. Diversity in age, gender, occupation, and perspectives
2. Realistic and consistent personality traits
3. Authentic pain points and goals relevant to their demographic
4. Culturally appropriate values and interests for the specified region
5. Varied communication and decision-making styles

Respond ONLY with valid JSON in this exact format:
{
  "personas": [
    {
      "name": "Full Name",
      "age": 35,
      "gender": "Female/Male/Non-binary",
      "occupation": "Job Title",
      "income_bracket": "Low/Middle/Upper-Middle/High",
      "education_level": "High School/Bachelor's/Master's/PhD",
      "location": "City, Region",
      "personality_traits": ["trait1", "trait2", "trait3"],
      "values": ["value1", "value2", "value3"],
      "interests": ["interest1", "interest2", "interest3"],
      "pain_points": ["pain_point1", "pain_point2"],
      "goals": ["goal1", "goal2"],
      "communication_style": "Direct/Indirect/Formal/Casual",
      "decision_making_style": "Analytical/Intuitive/Collaborative/Decisive",
      "brand_preferences": ["brand1", "brand2"],
      "media_consumption": ["platform1", "platform2"],
      "cultural_context": "Brief cultural background relevant to region",
      "behavioral_patterns": ["pattern1", "pattern2"]
    }
  ]
}`;

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    // Check authentication
    const session = await getServerSession(authOptions);
    if (!session?.user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Parse request body
    const body: GeneratePersonasRequest = await request.json();
    const {
      region = 'United States',
      country,
      sub_region,
      topic = '',
      industry = '',
      keywords = [],
      count = 10,
      include_psychographics = true,
      include_behavioral = true,
      include_cultural = true,
      include_topic_knowledge = false,
    } = body;

    // Build the user prompt
    const locationContext = [country, sub_region, region].filter(Boolean).join(', ') || region;
    const topicContext = topic ? `\nTopic/Context: ${topic}` : '';
    const industryContext = industry ? `\nIndustry Focus: ${industry}` : '';
    const keywordsContext = keywords.length > 0 ? `\nKeywords to incorporate: ${keywords.join(', ')}` : '';

    const additionalRequirements: string[] = [];
    if (include_psychographics) additionalRequirements.push('detailed psychographic profiles');
    if (include_behavioral) additionalRequirements.push('behavioral patterns and habits');
    if (include_cultural) additionalRequirements.push('cultural context and values');
    if (include_topic_knowledge) additionalRequirements.push('topic-specific knowledge and opinions');

    const userPrompt = `Generate ${count} diverse and realistic consumer personas for the following context:

Region/Location: ${locationContext}${topicContext}${industryContext}${keywordsContext}

Requirements:
- Create ${count} unique personas with diverse demographics
- Ensure realistic age distribution (18-75)
- Include mix of genders and backgrounds
- Make personas culturally authentic for ${locationContext}
${additionalRequirements.length > 0 ? `- Include: ${additionalRequirements.join(', ')}` : ''}

Generate detailed, realistic personas that would be useful for market research and consumer simulation.`;

    // Check for API key
    if (!OPENROUTER_API_KEY) {
      // Fallback to mock generation if no API key
      return generateMockPersonas(body, count, startTime);
    }

    // Call OpenRouter API
    const response = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'HTTP-Referer': process.env.NEXTAUTH_URL || 'https://agentverse.io',
        'X-Title': 'AgentVerse Persona Generator',
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: userPrompt }
        ],
        temperature: 0.8, // Higher temperature for more diverse personas
        max_tokens: 4000,
        response_format: { type: 'json_object' },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      // Fallback to mock if OpenRouter fails
      return generateMockPersonas(body, count, startTime, `OpenRouter error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;

    if (!content) {
      return generateMockPersonas(body, count, startTime, 'No content in response');
    }

    // Parse the JSON response
    let parsedPersonas;
    try {
      parsedPersonas = JSON.parse(content);
    } catch {
      return generateMockPersonas(body, count, startTime, 'Failed to parse AI response');
    }

    // Transform to our format
    const personas: GeneratedPersona[] = (parsedPersonas.personas || []).map(
      (p: GeneratedPersona, index: number) => ({
        id: `gen-persona-${Date.now()}-${index}`,
        name: p.name || `Persona ${index + 1}`,
        age: p.age || 30 + Math.floor(Math.random() * 30),
        gender: p.gender || 'Not specified',
        occupation: p.occupation || 'Professional',
        income_bracket: p.income_bracket || 'Middle',
        education_level: p.education_level || "Bachelor's",
        location: p.location || locationContext,
        personality_traits: p.personality_traits || [],
        values: p.values || [],
        interests: p.interests || [],
        pain_points: p.pain_points || [],
        goals: p.goals || [],
        communication_style: p.communication_style || 'Direct',
        decision_making_style: p.decision_making_style || 'Analytical',
        brand_preferences: p.brand_preferences,
        media_consumption: p.media_consumption,
        cultural_context: p.cultural_context,
        topic_knowledge: p.topic_knowledge,
        behavioral_patterns: p.behavioral_patterns,
      })
    );

    const result: GeneratePersonasResponse = {
      count: personas.length,
      template_id: body.template_id || null,
      sample_personas: personas.slice(0, count),
      generation_config: {
        region,
        country,
        sub_region,
        topic,
        industry,
        keywords,
        include_psychographics,
        include_behavioral,
        include_cultural,
        include_topic_knowledge,
        model: MODEL,
        generation_time_ms: Date.now() - startTime,
      },
    };

    return NextResponse.json(result);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: `Failed to generate personas: ${errorMessage}` },
      { status: 500 }
    );
  }
}

// Fallback mock generation when OpenRouter is unavailable
function generateMockPersonas(
  config: GeneratePersonasRequest,
  count: number,
  startTime: number,
  warning?: string
): NextResponse {
  const region = config.region || 'United States';

  // Generate diverse mock personas
  const names = [
    'Sarah Chen', 'Michael Johnson', 'Priya Sharma', 'David Kim', 'Maria Garcia',
    'James Wilson', 'Aisha Mohammed', 'Robert Taylor', 'Lisa Anderson', 'Wei Zhang',
    'Jennifer Brown', 'Carlos Rodriguez', 'Emma Thompson', 'Raj Patel', 'Sofia Martinez',
    'Daniel Lee', 'Fatima Al-Hassan', 'Chris Davis', 'Yuki Tanaka', 'Anna Kowalski'
  ];

  const occupations = [
    'Software Engineer', 'Marketing Manager', 'Teacher', 'Healthcare Professional',
    'Small Business Owner', 'Financial Analyst', 'Creative Director', 'Sales Executive',
    'Research Scientist', 'Operations Manager', 'Consultant', 'Entrepreneur',
    'Product Manager', 'HR Specialist', 'Architect', 'Journalist'
  ];

  const personalityTraits = [
    ['Analytical', 'Detail-oriented', 'Methodical'],
    ['Creative', 'Open-minded', 'Innovative'],
    ['Ambitious', 'Driven', 'Goal-oriented'],
    ['Empathetic', 'Caring', 'Supportive'],
    ['Practical', 'Realistic', 'Grounded'],
    ['Adventurous', 'Risk-taking', 'Curious'],
    ['Organized', 'Efficient', 'Systematic'],
    ['Social', 'Outgoing', 'Collaborative']
  ];

  const values = [
    ['Family', 'Security', 'Tradition'],
    ['Innovation', 'Progress', 'Achievement'],
    ['Community', 'Social Justice', 'Equality'],
    ['Freedom', 'Independence', 'Self-expression'],
    ['Sustainability', 'Environment', 'Health'],
    ['Success', 'Recognition', 'Wealth'],
    ['Knowledge', 'Learning', 'Growth'],
    ['Balance', 'Harmony', 'Wellbeing']
  ];

  const personas: GeneratedPersona[] = [];

  for (let i = 0; i < count; i++) {
    const nameIndex = i % names.length;
    const age = 22 + Math.floor(Math.random() * 45);
    const genders = ['Female', 'Male', 'Non-binary'];
    const gender = genders[Math.floor(Math.random() * genders.length)];
    const occupation = occupations[Math.floor(Math.random() * occupations.length)];
    const incomes = ['Low', 'Middle', 'Upper-Middle', 'High'];
    const income = incomes[Math.floor(Math.random() * incomes.length)];
    const educations = ['High School', "Bachelor's", "Master's", 'PhD'];
    const education = educations[Math.floor(Math.random() * educations.length)];
    const traits = personalityTraits[Math.floor(Math.random() * personalityTraits.length)];
    const personaValues = values[Math.floor(Math.random() * values.length)];
    const commStyles = ['Direct', 'Indirect', 'Formal', 'Casual'];
    const commStyle = commStyles[Math.floor(Math.random() * commStyles.length)];
    const decisionStyles = ['Analytical', 'Intuitive', 'Collaborative', 'Decisive'];
    const decisionStyle = decisionStyles[Math.floor(Math.random() * decisionStyles.length)];

    personas.push({
      id: `mock-persona-${Date.now()}-${i}`,
      name: names[nameIndex],
      age,
      gender,
      occupation,
      income_bracket: income,
      education_level: education,
      location: region,
      personality_traits: traits,
      values: personaValues,
      interests: ['Technology', 'Travel', 'Reading'].slice(0, 2 + Math.floor(Math.random() * 2)),
      pain_points: ['Time management', 'Work-life balance', 'Financial planning'].slice(0, 2),
      goals: ['Career growth', 'Financial security', 'Personal development'].slice(0, 2),
      communication_style: commStyle,
      decision_making_style: decisionStyle,
      brand_preferences: ['Quality brands', 'Value brands', 'Eco-friendly brands'].slice(0, 2),
      media_consumption: ['Social media', 'News websites', 'Streaming services'].slice(0, 2),
      cultural_context: `Typical ${region} consumer with diverse cultural influences`,
      behavioral_patterns: ['Early adopter', 'Price conscious', 'Brand loyal'].slice(0, 2),
    });
  }

  const warnings = warning
    ? [warning, 'Using mock generation - connect OpenRouter API for AI-powered personas']
    : ['Using mock generation - connect OpenRouter API for AI-powered personas'];

  const result: GeneratePersonasResponse = {
    count: personas.length,
    template_id: config.template_id || null,
    sample_personas: personas,
    generation_config: {
      ...config,
      mock: true,
      warnings,
      generation_time_ms: Date.now() - startTime,
    },
  };

  return NextResponse.json(result);
}
