import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

/**
 * Blueprint Draft API Route - Blueprint v2
 *
 * This endpoint generates a blueprint draft from goal analysis + clarification answers
 * WITHOUT requiring a project_id. Used in Step 1 of the v2 wizard.
 *
 * Reference: blueprint_v2.md §2.1.1, §4, §7.2
 */

// OpenRouter API configuration
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';
const MODEL = 'openai/gpt-4o-mini';

// Request interface
interface BlueprintDraftRequest {
  goal_text: string;
  goal_summary: string;
  domain_guess: string;
  clarification_answers: Record<string, string | string[]>;
  cutoff_date?: string;
  chosen_core?: 'collective' | 'target' | 'hybrid';
}

// Input slot definition (per blueprint_v2.md §4.3)
interface InputSlot {
  slot_id: string;
  name: string;
  description: string;
  required_level: 'required' | 'recommended' | 'optional';
  data_type: string;
  example_sources: string[];
}

// Section task definition (per blueprint_v2.md §4.4)
interface SectionTask {
  task_id: string;
  title: string;
  why_it_matters: string;
  linked_slots: string[];
  completion_criteria: string;
}

// Blueprint draft structure (per blueprint_v2.md §4)
interface BlueprintDraft {
  // Project Profile (§4.1)
  project_profile: {
    goal_text: string;
    goal_summary: string;
    domain_guess: string;
    output_type: string;
    horizon: string;
    scope: string;
    success_metrics: string[];
  };
  // Strategy (§4.2)
  strategy: {
    chosen_core: 'collective' | 'target' | 'hybrid';
    primary_drivers: string[];
    required_modules: string[];
  };
  // Input Slots Contract (§4.3)
  input_slots: InputSlot[];
  // Section Task Map (§4.4)
  section_tasks: Record<string, SectionTask[]>;
  // Metadata
  clarification_answers: Record<string, string | string[]>;
  generated_at: string;
  processing_time_ms: number;
  warnings: string[];
}

// System prompt for blueprint generation (per blueprint_v2.md §7.2)
const BLUEPRINT_DRAFT_PROMPT = `You are a Blueprint Architect for a predictive AI simulation platform. Your role is to create a detailed blueprint that will guide the user through setting up their simulation project.

Given a goal, domain, and clarification answers, generate a comprehensive blueprint with:

1. Project Profile - Clear summary of what we're predicting
2. Strategy - Which simulation approach to use
3. Input Slots - What data is needed (required/recommended/optional)
4. Section Tasks - Specific tasks for each section of the platform

SECTIONS TO COVER (generate 1-3 tasks per section):
- overview: Project overview and health
- inputs: Data and personas
- rules: Rules and assumptions
- runs: Run center for simulations
- universe: Universe/scenario mapping
- events: Event lab for what-if scenarios
- society: Society simulation settings
- target: Target planner
- reliability: Reliability and validation
- telemetry: Telemetry and replay
- reports: Report generation

INPUT SLOT REQUIRED LEVELS:
- required: Must have before running simulations
- recommended: Significantly improves accuracy
- optional: Nice to have, enhances specific features

Respond ONLY with valid JSON in this format:
{
  "project_profile": {
    "goal_summary": "string",
    "output_type": "distribution|point|ranked|paths",
    "horizon": "string",
    "scope": "string",
    "success_metrics": ["string"]
  },
  "strategy": {
    "chosen_core": "collective|target|hybrid",
    "primary_drivers": ["string"],
    "required_modules": ["string"]
  },
  "input_slots": [
    {
      "slot_id": "personas_base",
      "name": "Base Personas",
      "description": "Core persona profiles for simulation",
      "required_level": "required",
      "data_type": "persona_list",
      "example_sources": ["Survey data", "Census data"]
    }
  ],
  "section_tasks": {
    "overview": [
      {
        "task_id": "overview_1",
        "title": "Review project scope",
        "why_it_matters": "Ensures alignment with prediction goals",
        "linked_slots": [],
        "completion_criteria": "Blueprint summary reviewed"
      }
    ]
  }
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
    const body: BlueprintDraftRequest = await request.json();
    const {
      goal_text,
      goal_summary,
      domain_guess,
      clarification_answers,
      cutoff_date,
      chosen_core,
    } = body;

    if (!goal_text || goal_text.trim().length < 10) {
      return NextResponse.json(
        { error: 'Goal text must be at least 10 characters' },
        { status: 400 }
      );
    }

    // Check for API key
    if (!OPENROUTER_API_KEY) {
      // Fallback to mock generation if no API key
      return NextResponse.json(
        generateMockBlueprint(body, startTime)
      );
    }

    // Format clarification answers for the prompt
    const answersText = Object.entries(clarification_answers)
      .map(([key, value]) => `- ${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
      .join('\n');

    // Call OpenRouter API
    const response = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'HTTP-Referer': process.env.NEXTAUTH_URL || 'https://agentverse.io',
        'X-Title': 'AgentVerse Blueprint Draft',
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: 'system', content: BLUEPRINT_DRAFT_PROMPT },
          {
            role: 'user',
            content: `Generate a blueprint draft for this prediction project:

GOAL: "${goal_text}"

SUMMARY: ${goal_summary}

DOMAIN: ${domain_guess}

CLARIFICATION ANSWERS:
${answersText || 'No clarification answers provided'}

${cutoff_date ? `CUTOFF DATE: ${cutoff_date}` : ''}
${chosen_core ? `CHOSEN CORE: ${chosen_core}` : ''}

Create a comprehensive blueprint with appropriate input slots and section tasks.`
          }
        ],
        temperature: 0.7,
        max_tokens: 3000,
        response_format: { type: 'json_object' },
      }),
    });

    if (!response.ok) {
      return NextResponse.json(
        generateMockBlueprint(body, startTime)
      );
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;

    if (!content) {
      return NextResponse.json(
        generateMockBlueprint(body, startTime)
      );
    }

    // Parse the JSON response
    let parsed;
    try {
      parsed = JSON.parse(content);
    } catch {
      return NextResponse.json(
        generateMockBlueprint(body, startTime)
      );
    }

    // Build the blueprint draft
    const blueprint: BlueprintDraft = {
      project_profile: {
        goal_text,
        goal_summary: parsed.project_profile?.goal_summary || goal_summary,
        domain_guess,
        output_type: parsed.project_profile?.output_type || 'distribution',
        horizon: parsed.project_profile?.horizon || '6 months',
        scope: parsed.project_profile?.scope || 'Regional',
        success_metrics: parsed.project_profile?.success_metrics || [],
      },
      strategy: {
        chosen_core: chosen_core || parsed.strategy?.chosen_core || 'collective',
        primary_drivers: parsed.strategy?.primary_drivers || [],
        required_modules: parsed.strategy?.required_modules || [],
      },
      input_slots: parsed.input_slots || generateDefaultSlots(domain_guess),
      section_tasks: parsed.section_tasks || generateDefaultTasks(),
      clarification_answers,
      generated_at: new Date().toISOString(),
      processing_time_ms: Date.now() - startTime,
      warnings: [],
    };

    return NextResponse.json(blueprint);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: `Failed to generate blueprint draft: ${errorMessage}` },
      { status: 500 }
    );
  }
}

// Generate default input slots based on domain
function generateDefaultSlots(domain: string): InputSlot[] {
  const baseSlots: InputSlot[] = [
    {
      slot_id: 'personas_base',
      name: 'Base Personas',
      description: 'Core persona profiles that represent your target population',
      required_level: 'required',
      data_type: 'persona_list',
      example_sources: ['Survey data', 'Census demographics', 'Customer database'],
    },
    {
      slot_id: 'historical_data',
      name: 'Historical Data',
      description: 'Past data for calibration and validation',
      required_level: 'recommended',
      data_type: 'time_series',
      example_sources: ['Internal records', 'Public datasets', 'Third-party data'],
    },
    {
      slot_id: 'constraints',
      name: 'Business Constraints',
      description: 'Rules and limits that affect predictions',
      required_level: 'optional',
      data_type: 'rule_set',
      example_sources: ['Policy documents', 'Regulatory requirements'],
    },
  ];

  // Add domain-specific slots
  if (domain === 'political') {
    baseSlots.push({
      slot_id: 'voter_demographics',
      name: 'Voter Demographics',
      description: 'Voter registration and demographic data',
      required_level: 'required',
      data_type: 'demographic_data',
      example_sources: ['Election commission data', 'Census data'],
    });
    baseSlots.push({
      slot_id: 'polling_data',
      name: 'Polling Data',
      description: 'Historical and current polling results',
      required_level: 'recommended',
      data_type: 'poll_results',
      example_sources: ['Polling organizations', 'Media polls'],
    });
  } else if (domain === 'marketing') {
    baseSlots.push({
      slot_id: 'market_segments',
      name: 'Market Segments',
      description: 'Customer segmentation data',
      required_level: 'required',
      data_type: 'segment_data',
      example_sources: ['CRM data', 'Market research'],
    });
    baseSlots.push({
      slot_id: 'competitor_data',
      name: 'Competitor Intelligence',
      description: 'Competitor positioning and market share',
      required_level: 'recommended',
      data_type: 'competitor_info',
      example_sources: ['Market reports', 'Public filings'],
    });
  } else if (domain === 'finance') {
    baseSlots.push({
      slot_id: 'economic_indicators',
      name: 'Economic Indicators',
      description: 'Macroeconomic data relevant to predictions',
      required_level: 'required',
      data_type: 'economic_data',
      example_sources: ['FRED', 'World Bank', 'IMF'],
    });
    baseSlots.push({
      slot_id: 'market_data',
      name: 'Market Data',
      description: 'Price and volume data',
      required_level: 'recommended',
      data_type: 'market_data',
      example_sources: ['Financial data providers', 'Exchange data'],
    });
  }

  return baseSlots;
}

// Generate default section tasks
function generateDefaultTasks(): Record<string, SectionTask[]> {
  return {
    overview: [
      {
        task_id: 'overview_review',
        title: 'Review blueprint summary',
        why_it_matters: 'Ensures the project scope matches your prediction goals',
        linked_slots: [],
        completion_criteria: 'Blueprint reviewed and confirmed',
      },
    ],
    inputs: [
      {
        task_id: 'inputs_personas',
        title: 'Configure base personas',
        why_it_matters: 'Personas are the foundation of all simulations',
        linked_slots: ['personas_base'],
        completion_criteria: 'At least 10 personas configured',
      },
      {
        task_id: 'inputs_data',
        title: 'Connect historical data',
        why_it_matters: 'Historical data improves prediction accuracy',
        linked_slots: ['historical_data'],
        completion_criteria: 'Data source connected and validated',
      },
    ],
    rules: [
      {
        task_id: 'rules_constraints',
        title: 'Define business constraints',
        why_it_matters: 'Constraints ensure realistic predictions',
        linked_slots: ['constraints'],
        completion_criteria: 'Core constraints documented',
      },
    ],
    runs: [
      {
        task_id: 'runs_baseline',
        title: 'Run baseline simulation',
        why_it_matters: 'Establishes a reference point for comparisons',
        linked_slots: ['personas_base', 'historical_data'],
        completion_criteria: 'Baseline run completed successfully',
      },
    ],
    universe: [
      {
        task_id: 'universe_scenarios',
        title: 'Define key scenarios',
        why_it_matters: 'Scenarios enable what-if analysis',
        linked_slots: [],
        completion_criteria: 'At least 3 scenarios defined',
      },
    ],
    events: [
      {
        task_id: 'events_triggers',
        title: 'Configure event triggers',
        why_it_matters: 'Events drive changes in simulations',
        linked_slots: [],
        completion_criteria: 'Event triggers configured',
      },
    ],
    society: [
      {
        task_id: 'society_dynamics',
        title: 'Set society dynamics parameters',
        why_it_matters: 'Controls how opinions and behaviors spread',
        linked_slots: ['personas_base'],
        completion_criteria: 'Dynamics parameters set',
      },
    ],
    target: [
      {
        task_id: 'target_define',
        title: 'Define prediction targets',
        why_it_matters: 'Clear targets improve prediction focus',
        linked_slots: [],
        completion_criteria: 'Targets defined and validated',
      },
    ],
    reliability: [
      {
        task_id: 'reliability_calibrate',
        title: 'Calibrate against historical data',
        why_it_matters: 'Calibration validates prediction accuracy',
        linked_slots: ['historical_data'],
        completion_criteria: 'Calibration score > 70%',
      },
    ],
    telemetry: [
      {
        task_id: 'telemetry_review',
        title: 'Review simulation telemetry',
        why_it_matters: 'Telemetry helps understand prediction dynamics',
        linked_slots: [],
        completion_criteria: 'Telemetry dashboard configured',
      },
    ],
    reports: [
      {
        task_id: 'reports_template',
        title: 'Configure report templates',
        why_it_matters: 'Consistent reports aid decision-making',
        linked_slots: [],
        completion_criteria: 'Report template selected',
      },
    ],
  };
}

// Generate mock blueprint when OpenRouter is unavailable
function generateMockBlueprint(
  request: BlueprintDraftRequest,
  startTime: number
): BlueprintDraft {
  const { goal_text, goal_summary, domain_guess, clarification_answers, chosen_core } = request;

  // Determine core type from answers or default
  let core: 'collective' | 'target' | 'hybrid' = chosen_core || 'collective';
  if (clarification_answers['q1'] === 'outcome') {
    core = 'target';
  } else if (clarification_answers['q1'] === 'distribution') {
    core = 'collective';
  }

  // Determine horizon from answers
  let horizon = '6 months';
  const horizonAnswer = clarification_answers['q2'];
  if (horizonAnswer === '1_week') horizon = '1 week';
  else if (horizonAnswer === '1_month') horizon = '1 month';
  else if (horizonAnswer === '3_months') horizon = '3 months';
  else if (horizonAnswer === '1_year') horizon = '1 year';

  return {
    project_profile: {
      goal_text,
      goal_summary,
      domain_guess,
      output_type: 'distribution',
      horizon,
      scope: 'Regional',
      success_metrics: [
        'Prediction accuracy > 70%',
        'Confidence interval coverage',
        'Calibration score',
      ],
    },
    strategy: {
      chosen_core: core,
      primary_drivers: ['User behavior', 'External events', 'Market conditions'],
      required_modules: [
        'Population synthesis',
        'Behavior modeling',
        domain_guess === 'political' ? 'Voter simulation' : 'Consumer simulation',
        'Scenario engine',
        'Calibration suite',
      ],
    },
    input_slots: generateDefaultSlots(domain_guess),
    section_tasks: generateDefaultTasks(),
    clarification_answers,
    generated_at: new Date().toISOString(),
    processing_time_ms: Date.now() - startTime,
    warnings: ['Using mock generation - connect OpenRouter API for AI-powered blueprints'],
  };
}
