import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

/**
 * @deprecated This route is DEPRECATED. Use backend PIL jobs instead.
 *
 * Goal Analysis API Route - Blueprint v2
 *
 * DEPRECATION NOTICE (2026-01-17):
 * This frontend-only route bypasses the backend PIL job system and does NOT
 * persist results to the database. All goal analysis should now go through:
 *   - POST /api/v1/pil-jobs/ with job_type="goal_analysis"
 *
 * The GoalAssistantPanel.tsx already uses PIL jobs via usePILJob hooks.
 * This route is kept temporarily for backward compatibility but will be removed.
 *
 * Reference: blueprint_v2.md §2.1.1, §7.1
 */

// OpenRouter API configuration
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';
const MODEL = 'openai/gpt-4o-mini';

// Request interface
interface GoalAnalysisRequest {
  goal_text: string;
  skip_clarification?: boolean;
}

// Clarifying question structure (per blueprint_v2.md §2.1.1)
interface ClarifyingQuestion {
  id: string;
  question: string;
  why_we_ask: string;
  answer_type: 'single_select' | 'multi_select' | 'short_text';
  options?: { value: string; label: string }[];
  required: boolean;
}

// Goal analysis result structure
interface GoalAnalysisResult {
  goal_summary: string;
  domain_guess: 'marketing' | 'political' | 'finance' | 'social' | 'technology' | 'custom';
  output_type: 'distribution' | 'point' | 'ranked' | 'paths';
  horizon_guess: string;
  scope_guess: string;
  primary_drivers: string[];
  clarifying_questions: ClarifyingQuestion[];
  risk_notes: string[];
  processing_time_ms: number;
}

// System prompt for goal analysis (per blueprint_v2.md §7.1)
const GOAL_ANALYSIS_PROMPT = `You are a Project Formulation Expert for a predictive AI simulation platform. Your role is to analyze user goals and generate structured clarifying questions that will help create an optimal blueprint.

CRITICAL RULES:
1. Ask ONLY questions that would change the blueprint structure
2. Keep to 3-8 questions maximum unless explicitly asked for more
3. Prefer structured answers (single-select, multi-select) over free text
4. Each question MUST include "why_we_ask" - a brief explanation of why this matters

For each goal analysis, you must output:
1. goal_summary: A clear, concise summary of what the user wants to predict (1-2 sentences)
2. domain_guess: The primary domain (marketing, political, finance, social, technology, custom)
3. output_type: What kind of prediction output (distribution, point, ranked, paths)
4. horizon_guess: Time horizon for the prediction (e.g., "30 days", "6 months", "1 year")
5. scope_guess: Geographic or entity scope (e.g., "Malaysia", "US Market", "Global")
6. primary_drivers: List of 2-5 key factors that will drive this prediction
7. clarifying_questions: Array of structured questions (see format below)
8. risk_notes: Any concerns or caveats about this prediction goal

Respond ONLY with valid JSON in this exact format:
{
  "goal_summary": "string",
  "domain_guess": "marketing|political|finance|social|technology|custom",
  "output_type": "distribution|point|ranked|paths",
  "horizon_guess": "string",
  "scope_guess": "string",
  "primary_drivers": ["string"],
  "clarifying_questions": [
    {
      "id": "q1",
      "question": "What is your primary prediction target?",
      "why_we_ask": "This determines the core simulation model to use",
      "answer_type": "single_select",
      "options": [
        {"value": "outcome", "label": "Final outcome/winner"},
        {"value": "distribution", "label": "Probability distribution"},
        {"value": "trend", "label": "Trend direction"}
      ],
      "required": true
    }
  ],
  "risk_notes": ["string"]
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
    const body: GoalAnalysisRequest = await request.json();
    const { goal_text, skip_clarification = false } = body;

    if (!goal_text || goal_text.trim().length < 10) {
      return NextResponse.json(
        { error: 'Goal text must be at least 10 characters' },
        { status: 400 }
      );
    }

    // If skip_clarification, return minimal analysis without questions
    if (skip_clarification) {
      return NextResponse.json(generateMinimalAnalysis(goal_text, startTime));
    }

    // Check for API key
    if (!OPENROUTER_API_KEY) {
      // Fallback to mock generation if no API key
      return NextResponse.json(generateMockAnalysis(goal_text, startTime));
    }

    // Call OpenRouter API
    const response = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'HTTP-Referer': process.env.NEXTAUTH_URL || 'https://agentverse.io',
        'X-Title': 'AgentVerse Goal Analysis',
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: 'system', content: GOAL_ANALYSIS_PROMPT },
          {
            role: 'user',
            content: `Analyze this prediction goal and generate clarifying questions:\n\n"${goal_text}"\n\nProvide a thorough analysis with 3-6 clarifying questions that would help create an optimal simulation blueprint.`
          }
        ],
        temperature: 0.7,
        max_tokens: 2000,
        response_format: { type: 'json_object' },
      }),
    });

    if (!response.ok) {
      // Fallback to mock if OpenRouter fails
      return NextResponse.json(generateMockAnalysis(goal_text, startTime));
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;

    if (!content) {
      return NextResponse.json(generateMockAnalysis(goal_text, startTime));
    }

    // Parse the JSON response
    let parsed;
    try {
      parsed = JSON.parse(content);
    } catch {
      return NextResponse.json(generateMockAnalysis(goal_text, startTime));
    }

    // Build result with proper types
    const result: GoalAnalysisResult = {
      goal_summary: parsed.goal_summary || extractGoalSummary(goal_text),
      domain_guess: parsed.domain_guess || detectDomain(goal_text),
      output_type: parsed.output_type || 'distribution',
      horizon_guess: parsed.horizon_guess || '6 months',
      scope_guess: parsed.scope_guess || 'Regional',
      primary_drivers: parsed.primary_drivers || [],
      clarifying_questions: (parsed.clarifying_questions || []).map(
        (q: ClarifyingQuestion, i: number) => ({
          id: q.id || `q${i + 1}`,
          question: q.question,
          why_we_ask: q.why_we_ask || 'This helps configure the simulation',
          answer_type: q.answer_type || 'single_select',
          options: q.options,
          required: q.required ?? true,
        })
      ),
      risk_notes: parsed.risk_notes || [],
      processing_time_ms: Date.now() - startTime,
    };

    return NextResponse.json(result);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: `Failed to analyze goal: ${errorMessage}` },
      { status: 500 }
    );
  }
}

// Extract a goal summary from the text
function extractGoalSummary(goal: string): string {
  // Take first sentence or first 100 chars
  const firstSentence = goal.split(/[.!?]/)[0];
  if (firstSentence.length <= 100) {
    return firstSentence.trim() + '.';
  }
  return goal.slice(0, 97).trim() + '...';
}

// Detect domain from goal text
function detectDomain(goal: string): GoalAnalysisResult['domain_guess'] {
  const lower = goal.toLowerCase();

  if (/election|vote|politic|government|policy|candidate/.test(lower)) {
    return 'political';
  }
  if (/market|brand|ad|campaign|customer|consumer|product/.test(lower)) {
    return 'marketing';
  }
  if (/price|stock|invest|financ|econom|inflation|interest/.test(lower)) {
    return 'finance';
  }
  if (/social|community|trend|opinion|sentiment|movement/.test(lower)) {
    return 'social';
  }
  if (/tech|software|ai|digital|platform|app/.test(lower)) {
    return 'technology';
  }
  return 'custom';
}

// Generate minimal analysis when skipping clarification
function generateMinimalAnalysis(goal: string, startTime: number): GoalAnalysisResult {
  return {
    goal_summary: extractGoalSummary(goal),
    domain_guess: detectDomain(goal),
    output_type: 'distribution',
    horizon_guess: '6 months',
    scope_guess: 'Regional',
    primary_drivers: ['User behavior', 'Market conditions', 'External events'],
    clarifying_questions: [], // No questions when skipping
    risk_notes: ['Blueprint generated without clarification - may require manual refinement'],
    processing_time_ms: Date.now() - startTime,
  };
}

// Generate mock analysis when OpenRouter is unavailable
function generateMockAnalysis(goal: string, startTime: number): GoalAnalysisResult {
  const domain = detectDomain(goal);
  const lower = goal.toLowerCase();

  // Generate domain-specific clarifying questions
  const questions: ClarifyingQuestion[] = [];

  // Universal questions
  questions.push({
    id: 'q1',
    question: 'What is your primary prediction target?',
    why_we_ask: 'This determines the core simulation model and output format',
    answer_type: 'single_select',
    options: [
      { value: 'outcome', label: 'Final outcome or winner' },
      { value: 'distribution', label: 'Probability distribution' },
      { value: 'timeline', label: 'Timeline of events' },
      { value: 'trend', label: 'Trend direction and magnitude' },
    ],
    required: true,
  });

  questions.push({
    id: 'q2',
    question: 'What is your prediction time horizon?',
    why_we_ask: 'Different time horizons require different modeling approaches',
    answer_type: 'single_select',
    options: [
      { value: '1_week', label: '1 week' },
      { value: '1_month', label: '1 month' },
      { value: '3_months', label: '3 months' },
      { value: '6_months', label: '6 months' },
      { value: '1_year', label: '1 year or more' },
    ],
    required: true,
  });

  // Domain-specific questions
  if (domain === 'political') {
    questions.push({
      id: 'q3',
      question: 'What type of political event are you predicting?',
      why_we_ask: 'Political predictions require specific voter behavior models',
      answer_type: 'single_select',
      options: [
        { value: 'election', label: 'Election outcome' },
        { value: 'policy', label: 'Policy adoption/impact' },
        { value: 'approval', label: 'Approval ratings' },
        { value: 'other', label: 'Other political event' },
      ],
      required: true,
    });
  } else if (domain === 'marketing') {
    questions.push({
      id: 'q3',
      question: 'What marketing outcome are you measuring?',
      why_we_ask: 'Different marketing metrics require different persona configurations',
      answer_type: 'single_select',
      options: [
        { value: 'brand', label: 'Brand perception/sentiment' },
        { value: 'purchase', label: 'Purchase intent/behavior' },
        { value: 'engagement', label: 'Engagement metrics' },
        { value: 'market_share', label: 'Market share change' },
      ],
      required: true,
    });
  } else if (domain === 'finance') {
    questions.push({
      id: 'q3',
      question: 'What type of financial prediction?',
      why_we_ask: 'Financial predictions need specific economic indicator configurations',
      answer_type: 'single_select',
      options: [
        { value: 'price', label: 'Price movement' },
        { value: 'sentiment', label: 'Investor sentiment' },
        { value: 'adoption', label: 'Product/service adoption' },
        { value: 'macro', label: 'Macroeconomic impact' },
      ],
      required: true,
    });
  } else {
    questions.push({
      id: 'q3',
      question: 'What is the primary driver of change?',
      why_we_ask: 'Understanding the main driver helps configure the simulation engine',
      answer_type: 'single_select',
      options: [
        { value: 'behavior', label: 'Human behavior change' },
        { value: 'technology', label: 'Technology adoption' },
        { value: 'external', label: 'External events' },
        { value: 'policy', label: 'Policy/regulation change' },
      ],
      required: true,
    });
  }

  // Data availability question
  questions.push({
    id: 'q4',
    question: 'What data do you have available?',
    why_we_ask: 'Data availability determines which simulation methods are viable',
    answer_type: 'multi_select',
    options: [
      { value: 'historical', label: 'Historical data' },
      { value: 'surveys', label: 'Survey data' },
      { value: 'social', label: 'Social media data' },
      { value: 'internal', label: 'Internal company data' },
      { value: 'none', label: 'No existing data' },
    ],
    required: false,
  });

  // Accuracy vs speed question
  questions.push({
    id: 'q5',
    question: 'What is your priority?',
    why_we_ask: 'This helps balance simulation depth with execution speed',
    answer_type: 'single_select',
    options: [
      { value: 'accuracy', label: 'Maximum accuracy (slower)' },
      { value: 'balanced', label: 'Balanced approach' },
      { value: 'speed', label: 'Quick insights (faster)' },
    ],
    required: true,
  });

  // Determine primary drivers based on goal
  const drivers: string[] = [];
  if (/election|vote/.test(lower)) {
    drivers.push('Voter demographics', 'Political sentiment', 'Campaign events');
  } else if (/market|brand|product/.test(lower)) {
    drivers.push('Consumer behavior', 'Market trends', 'Competitor actions');
  } else if (/price|inflation/.test(lower)) {
    drivers.push('Economic indicators', 'Policy changes', 'Market sentiment');
  } else {
    drivers.push('User behavior', 'External events', 'System dynamics');
  }

  return {
    goal_summary: extractGoalSummary(goal),
    domain_guess: domain,
    output_type: 'distribution',
    horizon_guess: '6 months',
    scope_guess: 'Regional',
    primary_drivers: drivers,
    clarifying_questions: questions,
    risk_notes: ['Using mock analysis - connect OpenRouter API for AI-powered analysis'],
    processing_time_ms: Date.now() - startTime,
  };
}
