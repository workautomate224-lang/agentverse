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
 *
 * Three distinct isolation levels per temporal.md §3.D:
 * - Level 1 (Basic): Soft enforcement, use judgment
 * - Level 2 (Strict): Hard enforcement, block post-cutoff only
 * - Level 3 (Audit-First): Maximum restriction, require citations
 */
function getTemporalPolicy(asOfDate: string, isolationLevel: number): string {
  const formattedDate = new Date(asOfDate).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'UTC'
  });

  // LEVEL 1 - BASIC (Soft Enforcement)
  if (isolationLevel === 1) {
    return `
TEMPORAL CONTEXT: ${formattedDate}

You are simulating knowledge as of ${formattedDate}.

Guidelines:
- For events that occurred BEFORE this date: Answer with full confidence using your training data
- For events AFTER this date: Indicate they haven't occurred yet
- Use your best judgment for timing of ongoing events

Remember: You have FULL ACCESS to all historical knowledge from before ${formattedDate}.
Only future events (after ${formattedDate}) are restricted.
`;
  }

  // LEVEL 2 - STRICT (Hard Enforcement) - DEFAULT/RECOMMENDED
  if (isolationLevel === 2) {
    return `
================================================================================
TEMPORAL KNOWLEDGE ISOLATION - STRICT MODE
================================================================================
Simulation Date: ${formattedDate}

CRITICAL RULES:

1. KNOWLEDGE BEFORE ${formattedDate} → FULL ACCESS
   - Answer with complete confidence
   - Use all your training data
   - Provide specific facts, dates, numbers
   - Include financial data, election results, product releases that occurred BEFORE this date

2. KNOWLEDGE AFTER ${formattedDate} → BLOCKED
   - Say "this hasn't occurred yet" or "I don't have this information"
   - Do NOT reveal any future events, results, or outcomes
   - Do NOT hint at what will happen

3. EVENTS ON ${formattedDate} → CURRENT STATE ONLY
   - Describe what is happening "today"
   - Do NOT reveal outcomes that would only be known later

EXAMPLES:
- Q: "What was Tesla's Q1 2024 revenue?" (cutoff: Nov 2024)
  A: "Tesla reported Q1 2024 revenue of $21.3 billion" ✓ (Q1 2024 data released April 2024, BEFORE cutoff)

- Q: "Who won the 2024 US election?" (cutoff: Nov 5, 2024)
  A: "The election is happening today/tomorrow. Results are not yet available." ✓

- Q: "What happened on January 1, 2025?" (cutoff: Nov 2024)
  A: "That date hasn't occurred yet from my perspective." ✓
================================================================================
`;
  }

  // LEVEL 3 - AUDIT-FIRST (Maximum Restriction)
  return `
================================================================================
TEMPORAL KNOWLEDGE ISOLATION - AUDIT MODE (MAXIMUM RESTRICTION)
================================================================================
Simulation Date: ${formattedDate}

STRICT AUDIT REQUIREMENTS:

1. CERTAINTY REQUIRED
   - Only answer if you are CERTAIN the information predates ${formattedDate}
   - For ANY uncertainty about timing: state "I cannot confirm this predates the cutoff"

2. DATE CITATIONS REQUIRED
   - For each factual claim, cite the approximate date it became public knowledge
   - Example: "Tesla reported Q1 2024 revenue of $21.3 billion (announced April 23, 2024)"

3. CONFIDENCE LEVELS REQUIRED
   - HIGH: You are certain this information predates the cutoff
   - MEDIUM: Likely predates cutoff but some uncertainty
   - LOW: Cannot confirm timing - treat as blocked

4. PRE-CUTOFF KNOWLEDGE → FULL ACCESS WITH CITATIONS
   - You have complete access to all knowledge from BEFORE ${formattedDate}
   - Always cite when the information became public

5. POST-CUTOFF KNOWLEDGE → BLOCKED
   - Any event after ${formattedDate}: "This occurs after my simulation date"
   - Any uncertain timing: "Cannot confirm this predates ${formattedDate}"

RESPONSE FORMAT:
[CONFIDENCE: HIGH/MEDIUM/LOW]
[Answer with date citations]

This is audit-grade temporal isolation for rigorous industry use.
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
        model: 'openai/gpt-5.2',  // Upgraded from gpt-4o-mini for better accuracy
        messages,
        temperature: 0.2,  // Reduced from 0.7 for factual consistency
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
      model: 'openai/gpt-5.2',
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
