import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

// OpenRouter API configuration
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

// Use GPT-4o-mini for fast, cheap generation
const MODEL = 'openai/gpt-4o-mini';

interface GenerateRequest {
  project_id: string;
  prompt: string;
  max_scenarios?: number;
}

interface GeneratedScenario {
  scenario_id: string;
  label: string;
  description: string;
  variable_deltas: Record<string, number>;
  total_magnitude: number;
  confidence: number;
  event_script_preview?: {
    intensity_profile: string;
    scope: string;
    estimated_duration_ticks: number;
  };
}

interface GenerateResponse {
  compilation_id: string;
  original_prompt: string;
  candidate_scenarios: GeneratedScenario[];
  compiled_at: string;
  compilation_time_ms: number;
  warnings: string[];
}

const SYSTEM_PROMPT = `You are an expert scenario analyst for predictive simulations. Given a "what-if" question, generate plausible alternative scenarios that could occur.

For each scenario, provide:
1. A clear, concise label (2-5 words)
2. A description explaining the scenario (1-2 sentences)
3. Key variables that would change and by how much (as decimal multipliers, e.g., 0.2 for 20% increase, -0.3 for 30% decrease)
4. A confidence score (0.0-1.0) indicating how likely/plausible this scenario is
5. The total magnitude of change (sum of absolute variable deltas)

Think about:
- Direct effects of the what-if condition
- Secondary/indirect effects
- Different severity levels (mild, moderate, severe)
- Different timeframes (short-term, long-term)

Respond ONLY with valid JSON in this exact format:
{
  "scenarios": [
    {
      "label": "Scenario Name",
      "description": "What happens in this scenario",
      "variable_deltas": {
        "variable_name": 0.2,
        "another_variable": -0.1
      },
      "confidence": 0.75,
      "intensity": "moderate",
      "scope": "regional",
      "duration_ticks": 100
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
    const body: GenerateRequest = await request.json();
    const { prompt, max_scenarios = 5 } = body;

    if (!prompt || prompt.trim().length === 0) {
      return NextResponse.json(
        { error: 'Prompt is required' },
        { status: 400 }
      );
    }

    // Check for API key
    if (!OPENROUTER_API_KEY) {
      // Fallback to mock generation if no API key
      return generateMockScenarios(prompt, max_scenarios, startTime);
    }

    // Call OpenRouter API
    const response = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'HTTP-Referer': process.env.NEXTAUTH_URL || 'https://agentverse.io',
        'X-Title': 'AgentVerse Event Lab',
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: `Generate ${max_scenarios} alternative scenarios for this what-if question:\n\n"${prompt}"\n\nProvide diverse scenarios with varying severity and timeframes.` }
        ],
        temperature: 0.7,
        max_tokens: 2000,
        response_format: { type: 'json_object' },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      // Fallback to mock if OpenRouter fails
      return generateMockScenarios(prompt, max_scenarios, startTime, `OpenRouter error: ${response.status}`);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;

    if (!content) {
      return generateMockScenarios(prompt, max_scenarios, startTime, 'No content in response');
    }

    // Parse the JSON response
    let parsedScenarios;
    try {
      parsedScenarios = JSON.parse(content);
    } catch {
      return generateMockScenarios(prompt, max_scenarios, startTime, 'Failed to parse AI response');
    }

    // Transform to our format
    const scenarios: GeneratedScenario[] = (parsedScenarios.scenarios || []).map(
      (s: { label: string; description: string; variable_deltas: Record<string, number>; confidence: number; intensity?: string; scope?: string; duration_ticks?: number }, index: number) => ({
        scenario_id: `gen-${Date.now()}-${index}`,
        label: s.label || `Scenario ${index + 1}`,
        description: s.description || 'Generated scenario',
        variable_deltas: s.variable_deltas || {},
        total_magnitude: Object.values(s.variable_deltas || {}).reduce((sum, v) => sum + Math.abs(v as number), 0),
        confidence: s.confidence || 0.5,
        event_script_preview: s.intensity ? {
          intensity_profile: s.intensity,
          scope: s.scope || 'local',
          estimated_duration_ticks: s.duration_ticks || 50,
        } : undefined,
      })
    );

    const result: GenerateResponse = {
      compilation_id: `comp-${Date.now()}`,
      original_prompt: prompt,
      candidate_scenarios: scenarios.slice(0, max_scenarios),
      compiled_at: new Date().toISOString(),
      compilation_time_ms: Date.now() - startTime,
      warnings: [],
    };

    return NextResponse.json(result);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: `Failed to generate scenarios: ${errorMessage}` },
      { status: 500 }
    );
  }
}

// Fallback mock generation when OpenRouter is unavailable
function generateMockScenarios(
  prompt: string,
  maxScenarios: number,
  startTime: number,
  warning?: string
): NextResponse {
  // Extract key terms from the prompt for more relevant mock scenarios
  const promptLower = prompt.toLowerCase();

  // Determine scenario themes based on prompt content
  const themes: Array<{
    label: string;
    description: string;
    variables: Record<string, number>;
    confidence: number;
    intensity: string;
  }> = [];

  if (promptLower.includes('price') || promptLower.includes('cost') || promptLower.includes('tariff')) {
    themes.push(
      { label: 'Moderate Price Increase', description: 'Prices rise by 15-20%, causing moderate consumer behavior shifts', variables: { consumer_spending: -0.15, inflation: 0.12, demand: -0.1 }, confidence: 0.82, intensity: 'moderate' },
      { label: 'Severe Price Shock', description: 'Dramatic 40%+ price spike triggers market disruption', variables: { consumer_spending: -0.35, inflation: 0.28, demand: -0.25, market_volatility: 0.4 }, confidence: 0.65, intensity: 'severe' },
      { label: 'Gradual Adjustment', description: 'Slow price changes allow market adaptation over time', variables: { consumer_spending: -0.08, inflation: 0.06, adaptation_rate: 0.2 }, confidence: 0.88, intensity: 'mild' }
    );
  }

  if (promptLower.includes('competitor') || promptLower.includes('market') || promptLower.includes('enter')) {
    themes.push(
      { label: 'Market Share Loss', description: 'New competition captures 10-15% market share', variables: { market_share: -0.12, revenue: -0.1, competition_intensity: 0.3 }, confidence: 0.78, intensity: 'moderate' },
      { label: 'Price War Scenario', description: 'Aggressive pricing battle reduces margins across the industry', variables: { profit_margin: -0.25, price_level: -0.2, customer_acquisition: 0.15 }, confidence: 0.72, intensity: 'severe' },
      { label: 'Innovation Response', description: 'Competition drives innovation and product improvement', variables: { rd_investment: 0.2, product_quality: 0.15, customer_satisfaction: 0.1 }, confidence: 0.68, intensity: 'moderate' }
    );
  }

  if (promptLower.includes('election') || promptLower.includes('government') || promptLower.includes('policy')) {
    themes.push(
      { label: 'Policy Shift Impact', description: 'New policies create regulatory changes affecting operations', variables: { compliance_cost: 0.2, regulatory_burden: 0.15, market_access: -0.1 }, confidence: 0.75, intensity: 'moderate' },
      { label: 'Favorable Outcome', description: 'Policy changes create beneficial business environment', variables: { tax_burden: -0.15, business_confidence: 0.2, investment: 0.18 }, confidence: 0.62, intensity: 'moderate' },
      { label: 'Uncertainty Period', description: 'Political uncertainty causes market hesitation', variables: { market_volatility: 0.25, investment: -0.15, consumer_confidence: -0.12 }, confidence: 0.85, intensity: 'mild' }
    );
  }

  if (promptLower.includes('interest') || promptLower.includes('rate') || promptLower.includes('fed')) {
    themes.push(
      { label: 'Borrowing Cost Increase', description: 'Higher rates reduce borrowing and slow expansion', variables: { borrowing: -0.2, expansion_rate: -0.15, housing_market: -0.18 }, confidence: 0.8, intensity: 'moderate' },
      { label: 'Savings Boost', description: 'Higher rates encourage saving over spending', variables: { savings_rate: 0.25, consumer_spending: -0.12, bank_deposits: 0.2 }, confidence: 0.78, intensity: 'moderate' }
    );
  }

  // Default scenarios if no specific themes matched
  if (themes.length === 0) {
    themes.push(
      { label: 'Optimistic Scenario', description: 'Favorable conditions lead to positive outcomes', variables: { growth: 0.15, confidence: 0.12, performance: 0.18 }, confidence: 0.7, intensity: 'moderate' },
      { label: 'Pessimistic Scenario', description: 'Challenging conditions create headwinds', variables: { growth: -0.12, confidence: -0.15, performance: -0.1 }, confidence: 0.72, intensity: 'moderate' },
      { label: 'Status Quo', description: 'Minimal change from current trajectory', variables: { growth: 0.02, confidence: 0.01, performance: 0.03 }, confidence: 0.85, intensity: 'mild' },
      { label: 'High Volatility', description: 'Uncertain conditions create market swings', variables: { volatility: 0.35, uncertainty: 0.3, risk_premium: 0.2 }, confidence: 0.65, intensity: 'severe' },
      { label: 'Structural Shift', description: 'Fundamental changes reshape the landscape', variables: { market_structure: 0.4, adaptation_need: 0.35, opportunity: 0.25 }, confidence: 0.55, intensity: 'severe' }
    );
  }

  // Select scenarios up to maxScenarios
  const selectedThemes = themes.slice(0, maxScenarios);

  const scenarios: GeneratedScenario[] = selectedThemes.map((theme, index) => ({
    scenario_id: `mock-${Date.now()}-${index}`,
    label: theme.label,
    description: theme.description,
    variable_deltas: theme.variables,
    total_magnitude: Object.values(theme.variables).reduce((sum, v) => sum + Math.abs(v), 0),
    confidence: theme.confidence,
    event_script_preview: {
      intensity_profile: theme.intensity,
      scope: 'market-wide',
      estimated_duration_ticks: theme.intensity === 'severe' ? 200 : theme.intensity === 'moderate' ? 100 : 50,
    },
  }));

  const warnings = warning ? [warning, 'Using intelligent mock generation'] : ['Using intelligent mock generation - connect OpenRouter API for AI-powered scenarios'];

  const result: GenerateResponse = {
    compilation_id: `mock-comp-${Date.now()}`,
    original_prompt: prompt,
    candidate_scenarios: scenarios,
    compiled_at: new Date().toISOString(),
    compilation_time_ms: Date.now() - startTime,
    warnings,
  };

  return NextResponse.json(result);
}
