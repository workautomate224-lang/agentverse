import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

// OpenRouter API configuration
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

// Use GPT-4o-mini for fast, cheap generation
const MODEL = 'openai/gpt-4o-mini';

interface GeneratePlanRequest {
  prompt: string;
  target_metric?: string;
  horizon_ticks?: number;
  context?: {
    project_id?: string;
    node_id?: string;
    current_state?: Record<string, unknown>;
  };
}

interface InterventionStep {
  tick: number;
  action: string;
  parameters: Record<string, unknown>;
  expected_impact: string;
}

interface GeneratePlanResponse {
  name: string;
  description: string;
  target_metric: string;
  target_value: number;
  horizon_ticks: number;
  steps: InterventionStep[];
  reasoning: string;
  confidence: number;
  warnings: string[];
}

const SYSTEM_PROMPT = `You are an expert intervention planner for predictive simulations. Your role is to help users achieve their target outcomes through strategic interventions.

Given a user's goal or question about "how to achieve X", generate a detailed intervention plan with specific, actionable steps.

For each intervention plan, provide:
1. A clear, concise name (2-5 words)
2. A description explaining the overall strategy (1-2 sentences)
3. The target metric to optimize (e.g., "market_share", "revenue", "customer_satisfaction")
4. The target value to achieve (as a decimal for percentages, e.g., 0.25 for 25%)
5. The time horizon in simulation ticks (typically 50-500)
6. A list of intervention steps, each with:
   - tick: When to apply the intervention (0 = immediately, higher = later)
   - action: The type of intervention (e.g., "adjust_price", "launch_campaign", "expand_capacity")
   - parameters: Key-value pairs for the intervention (e.g., {"price_change": -0.1, "target_segment": "premium"})
   - expected_impact: Description of what this step should achieve
7. Your reasoning for why this plan should work
8. A confidence score (0.0-1.0) indicating how likely this plan is to succeed

Think about:
- Timing and sequencing of interventions
- Dependencies between steps
- Resource constraints
- Potential risks and mitigation
- Both short-term and long-term effects

Respond ONLY with valid JSON in this exact format:
{
  "name": "Plan Name",
  "description": "Overall strategy description",
  "target_metric": "metric_name",
  "target_value": 0.25,
  "horizon_ticks": 200,
  "steps": [
    {
      "tick": 0,
      "action": "action_type",
      "parameters": {"key": "value"},
      "expected_impact": "What this achieves"
    }
  ],
  "reasoning": "Why this plan should work",
  "confidence": 0.75
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
    const body: GeneratePlanRequest = await request.json();
    const { prompt, target_metric, horizon_ticks = 200, context } = body;

    if (!prompt || prompt.trim().length === 0) {
      return NextResponse.json(
        { error: 'Prompt is required' },
        { status: 400 }
      );
    }

    // Check for API key
    if (!OPENROUTER_API_KEY) {
      // Fallback to mock generation if no API key
      return generateMockPlan(prompt, target_metric, horizon_ticks, startTime);
    }

    // Build the user message with context
    let userMessage = `Generate an intervention plan for the following goal:\n\n"${prompt}"`;

    if (target_metric) {
      userMessage += `\n\nThe primary metric to optimize is: ${target_metric}`;
    }

    if (horizon_ticks) {
      userMessage += `\nTime horizon: ${horizon_ticks} ticks`;
    }

    if (context?.current_state) {
      userMessage += `\n\nCurrent state:\n${JSON.stringify(context.current_state, null, 2)}`;
    }

    // Call OpenRouter API
    const response = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'HTTP-Referer': process.env.NEXTAUTH_URL || 'https://agentverse.io',
        'X-Title': 'AgentVerse Target Planner',
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: userMessage }
        ],
        temperature: 0.7,
        max_tokens: 2500,
        response_format: { type: 'json_object' },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      // Fallback to mock if OpenRouter fails
      return generateMockPlan(prompt, target_metric, horizon_ticks, startTime, `OpenRouter error: ${response.status}`);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;

    if (!content) {
      return generateMockPlan(prompt, target_metric, horizon_ticks, startTime, 'No content in response');
    }

    // Parse the JSON response
    let parsedPlan;
    try {
      parsedPlan = JSON.parse(content);
    } catch {
      return generateMockPlan(prompt, target_metric, horizon_ticks, startTime, 'Failed to parse AI response');
    }

    // Validate and normalize the response
    const result: GeneratePlanResponse = {
      name: parsedPlan.name || 'AI Generated Plan',
      description: parsedPlan.description || 'AI-generated intervention plan',
      target_metric: parsedPlan.target_metric || target_metric || 'performance',
      target_value: typeof parsedPlan.target_value === 'number' ? parsedPlan.target_value : 0.2,
      horizon_ticks: typeof parsedPlan.horizon_ticks === 'number' ? parsedPlan.horizon_ticks : horizon_ticks,
      steps: Array.isArray(parsedPlan.steps) ? parsedPlan.steps.map((s: Partial<InterventionStep>, i: number) => ({
        tick: typeof s.tick === 'number' ? s.tick : i * 20,
        action: s.action || 'intervention',
        parameters: s.parameters || {},
        expected_impact: s.expected_impact || 'Expected positive impact',
      })) : [],
      reasoning: parsedPlan.reasoning || 'AI-generated plan based on the provided goal.',
      confidence: typeof parsedPlan.confidence === 'number' ? parsedPlan.confidence : 0.7,
      warnings: [],
    };

    return NextResponse.json(result);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: `Failed to generate plan: ${errorMessage}` },
      { status: 500 }
    );
  }
}

// Fallback mock generation when OpenRouter is unavailable
function generateMockPlan(
  prompt: string,
  targetMetric?: string,
  horizonTicks: number = 200,
  startTime: number = Date.now(),
  warning?: string
): NextResponse {
  const promptLower = prompt.toLowerCase();

  // Determine plan theme based on prompt content
  let plan: Omit<GeneratePlanResponse, 'warnings'>;

  if (promptLower.includes('market share') || promptLower.includes('grow') || promptLower.includes('expand')) {
    plan = {
      name: 'Market Expansion Strategy',
      description: 'Phased approach to increase market share through competitive pricing and targeted marketing.',
      target_metric: targetMetric || 'market_share',
      target_value: 0.25,
      horizon_ticks: horizonTicks,
      steps: [
        { tick: 0, action: 'analyze_competitors', parameters: { depth: 'comprehensive' }, expected_impact: 'Identify competitive gaps and opportunities' },
        { tick: 20, action: 'adjust_pricing', parameters: { price_change: -0.05, segment: 'entry_level' }, expected_impact: 'Attract price-sensitive customers' },
        { tick: 50, action: 'launch_campaign', parameters: { budget: 50000, channels: ['digital', 'social'] }, expected_impact: 'Increase brand awareness by 15%' },
        { tick: 100, action: 'expand_distribution', parameters: { new_channels: 3 }, expected_impact: 'Reach 20% more potential customers' },
        { tick: 150, action: 'loyalty_program', parameters: { reward_rate: 0.05 }, expected_impact: 'Improve customer retention by 10%' },
      ],
      reasoning: 'A phased expansion strategy allows for market testing and adjustment while building sustainable growth.',
      confidence: 0.75,
    };
  } else if (promptLower.includes('revenue') || promptLower.includes('profit') || promptLower.includes('sales')) {
    plan = {
      name: 'Revenue Optimization Plan',
      description: 'Multi-pronged approach to increase revenue through pricing optimization and upselling.',
      target_metric: targetMetric || 'revenue',
      target_value: 0.3,
      horizon_ticks: horizonTicks,
      steps: [
        { tick: 0, action: 'segment_analysis', parameters: { criteria: ['value', 'frequency'] }, expected_impact: 'Identify high-value customer segments' },
        { tick: 30, action: 'premium_tier_launch', parameters: { price_premium: 0.2, features: 'enhanced' }, expected_impact: 'Capture additional value from power users' },
        { tick: 60, action: 'cross_sell_campaign', parameters: { target_segments: ['high_value'] }, expected_impact: 'Increase average order value by 15%' },
        { tick: 100, action: 'retention_incentives', parameters: { discount_rate: 0.1, min_tenure: 6 }, expected_impact: 'Reduce churn by 8%' },
        { tick: 150, action: 'price_optimization', parameters: { method: 'dynamic', ceiling: 0.15 }, expected_impact: 'Optimize margin without volume loss' },
      ],
      reasoning: 'Combining value extraction from existing customers with new premium offerings creates sustainable revenue growth.',
      confidence: 0.72,
    };
  } else if (promptLower.includes('satisfaction') || promptLower.includes('nps') || promptLower.includes('customer')) {
    plan = {
      name: 'Customer Experience Enhancement',
      description: 'Systematic improvements to customer touchpoints to boost satisfaction and loyalty.',
      target_metric: targetMetric || 'customer_satisfaction',
      target_value: 0.85,
      horizon_ticks: horizonTicks,
      steps: [
        { tick: 0, action: 'feedback_collection', parameters: { channels: ['survey', 'support', 'social'] }, expected_impact: 'Identify top pain points' },
        { tick: 25, action: 'support_enhancement', parameters: { response_time_target: '2h', channels: 'omni' }, expected_impact: 'Reduce resolution time by 40%' },
        { tick: 60, action: 'product_improvements', parameters: { priority: 'top_3_issues' }, expected_impact: 'Address major friction points' },
        { tick: 100, action: 'proactive_outreach', parameters: { trigger: 'at_risk', offer: 'concierge' }, expected_impact: 'Recover 30% of at-risk customers' },
        { tick: 140, action: 'community_building', parameters: { platform: 'dedicated', rewards: true }, expected_impact: 'Create brand advocates' },
      ],
      reasoning: 'Addressing customer pain points systematically while building emotional connection creates lasting satisfaction.',
      confidence: 0.78,
    };
  } else {
    // Default generic plan
    plan = {
      name: 'Strategic Improvement Plan',
      description: 'Balanced approach to achieving the target through incremental improvements.',
      target_metric: targetMetric || 'performance',
      target_value: 0.2,
      horizon_ticks: horizonTicks,
      steps: [
        { tick: 0, action: 'baseline_assessment', parameters: { metrics: 'all' }, expected_impact: 'Establish current performance baseline' },
        { tick: 30, action: 'quick_wins', parameters: { effort: 'low', impact: 'medium' }, expected_impact: 'Achieve early momentum with 5% improvement' },
        { tick: 70, action: 'process_optimization', parameters: { focus: 'bottlenecks' }, expected_impact: 'Remove key constraints' },
        { tick: 120, action: 'capability_building', parameters: { areas: ['skills', 'tools'] }, expected_impact: 'Enable sustained improvement' },
        { tick: 170, action: 'continuous_improvement', parameters: { methodology: 'iterative' }, expected_impact: 'Lock in gains and identify new opportunities' },
      ],
      reasoning: 'A balanced approach combining quick wins with structural improvements creates sustainable progress.',
      confidence: 0.68,
    };
  }

  const warnings = warning
    ? [warning, 'Using mock plan generation - connect OpenRouter API for AI-powered plans']
    : ['Using mock plan generation - connect OpenRouter API for AI-powered plans'];

  const result: GeneratePlanResponse = {
    ...plan,
    warnings,
  };

  return NextResponse.json(result);
}
