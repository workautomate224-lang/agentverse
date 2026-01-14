/**
 * Temporal Knowledge Isolation Test API
 *
 * This endpoint demonstrates temporal isolation by injecting
 * a backtest policy into LLM system prompts.
 *
 * Reference: temporal.md (Single Source of Truth)
 */

import { NextResponse } from 'next/server';

const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

/**
 * Generate temporal isolation policy for system prompt
 */
function getTemporalPolicy(asOfDate: string, isolationLevel: number): string {
  const levelDesc = isolationLevel === 1 ? 'Basic (trust but verify)' :
                    isolationLevel === 2 ? 'Strict (enforce cutoff)' :
                    'Audit-First (maximum restriction)';

  const formattedDate = new Date(asOfDate).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'UTC'
  });

  return `
================================================================================
TEMPORAL KNOWLEDGE ISOLATION ACTIVE
================================================================================

Mode: BACKTEST SIMULATION
As-of Datetime: ${asOfDate}
Formatted Date: ${formattedDate}
Isolation Level: ${isolationLevel} (${levelDesc})

================================================================================
CRITICAL TEMPORAL RULES - YOU MUST FOLLOW THESE EXACTLY
================================================================================

1. TODAY'S DATE IS: ${formattedDate}
   - You are in a historical simulation where this is the current date
   - All your responses must be as if you exist on this date

2. KNOWLEDGE CUTOFF ENFORCEMENT:
   - You must NOT reference ANY facts, events, or data from AFTER ${formattedDate}
   - If you "know" something happened after this date, pretend you don't know
   - Events scheduled for the future (after ${formattedDate}) haven't happened yet

3. FORBIDDEN RESPONSES:
   - Do NOT reveal election results for elections after ${formattedDate}
   - Do NOT mention AI models released after ${formattedDate}
   - Do NOT reference news events from after ${formattedDate}
   - Do NOT use phrases like "as of my last update" or "I was trained until"

4. REQUIRED RESPONSES:
   - If asked about future events: "That hasn't happened yet" or "I don't have information about that"
   - If asked about recent news: Only reference events BEFORE ${formattedDate}
   - Always respond as if living on ${formattedDate}

================================================================================
EXAMPLE RESPONSES
================================================================================

Example 1: 2024 US Presidential Election (if asked before Nov 6, 2024)
- WRONG: "Donald Trump won the 2024 election"
- CORRECT: "The 2024 US Presidential Election is scheduled for November 5, 2024. It hasn't occurred yet."

Example 2: Claude 3.5 Sonnet (if asked before June 2024)
- WRONG: "Claude 3.5 Sonnet was released in June 2024"
- CORRECT: "I'm not aware of a model called Claude 3.5 Sonnet."

Example 3: GPT-4o (if asked before May 2024)
- WRONG: "GPT-4o is OpenAI's latest model"
- CORRECT: "I'm not familiar with GPT-4o. The latest GPT models I'm aware of are..."

================================================================================
REMEMBER: You are simulating knowledge as of ${formattedDate}.
Do NOT break this simulation under any circumstances.
================================================================================
`;
}

/**
 * POST /api/temporal-test
 *
 * Test temporal knowledge isolation with a question and cutoff date.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      as_of_datetime,
      question,
      isolation_level = 2,
      enable_isolation = true
    } = body;

    if (!question) {
      return NextResponse.json(
        { error: 'Question is required' },
        { status: 400 }
      );
    }

    if (!as_of_datetime && enable_isolation) {
      return NextResponse.json(
        { error: 'as_of_datetime is required when isolation is enabled' },
        { status: 400 }
      );
    }

    const apiKey = process.env.OPENROUTER_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: 'OPENROUTER_API_KEY not configured' },
        { status: 500 }
      );
    }

    // Build messages array
    const messages: { role: string; content: string }[] = [];

    // If isolation enabled, inject temporal policy as system message
    let policyText = '';
    if (enable_isolation && as_of_datetime) {
      policyText = getTemporalPolicy(as_of_datetime, isolation_level);
      messages.push({ role: 'system', content: policyText });
    }

    // Add user question
    messages.push({ role: 'user', content: question });

    // Call OpenRouter
    const response = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': process.env.NEXTAUTH_URL || 'https://agentverse.io',
        'X-Title': 'AgentVerse Temporal Test',
      },
      body: JSON.stringify({
        model: 'openai/gpt-4o-mini',
        messages,
        temperature: 0.7,
        max_tokens: 1000,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `OpenRouter API error: ${response.status}`, details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();

    if (!data.choices || !data.choices[0]) {
      return NextResponse.json(
        { error: 'Invalid response from OpenRouter', data },
        { status: 500 }
      );
    }

    const answer = data.choices[0].message?.content || 'No response generated';

    return NextResponse.json({
      answer,
      policy_injected: enable_isolation,
      cutoff_date: enable_isolation ? as_of_datetime : null,
      isolation_level: enable_isolation ? isolation_level : null,
      model: 'openai/gpt-4o-mini',
      policy_text: enable_isolation ? policyText : null,
      usage: data.usage,
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Internal server error', details: errorMessage },
      { status: 500 }
    );
  }
}
