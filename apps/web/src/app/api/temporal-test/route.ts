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
 *
 * NOTE: Isolation mode uses CONCISE responses to save tokens and speed up replies.
 * When knowledge is blocked, there's no need for lengthy explanations.
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
    return `TEMPORAL ISOLATION: ${formattedDate}

RULES:
- Pre-cutoff knowledge: Answer concisely with key facts
- Post-cutoff knowledge: Simply state "This hasn't occurred yet as of ${formattedDate}"
- Keep responses brief and direct`;
  }

  // LEVEL 2 - STRICT (Hard Enforcement) - DEFAULT/RECOMMENDED
  if (isolationLevel === 2) {
    return `TEMPORAL ISOLATION - STRICT MODE
Cutoff: ${formattedDate}

RULES:
- BEFORE cutoff: Answer with key facts (concise)
- AFTER cutoff: Say "This information is not available as of ${formattedDate}" (one sentence)
- ON cutoff date: Describe current state briefly

Keep responses SHORT and DIRECT. No lengthy explanations needed.`;
  }

  // LEVEL 3 - AUDIT-FIRST (Maximum Restriction)
  return `TEMPORAL ISOLATION - AUDIT MODE
Cutoff: ${formattedDate}

RULES:
- Only answer if CERTAIN info predates cutoff
- Format: "[Date of info] Brief answer"
- Post-cutoff: "Not available as of ${formattedDate}"
- Uncertain: "Cannot confirm timing"

Keep responses CONCISE.`;
}

/**
 * Base system prompt for comprehensive, professional responses
 * This ensures all responses match official ChatGPT quality standards
 */
const PROFESSIONAL_RESPONSE_PROMPT = `You are a highly knowledgeable AI assistant providing comprehensive, professional-grade responses.

RESPONSE QUALITY STANDARDS:
1. Be thorough and detailed - provide complete, well-researched answers
2. Use clear structure with paragraphs, bullet points, or numbered lists when appropriate
3. Include relevant context, background information, and nuances
4. Cite specific facts, dates, statistics, and sources when available
5. Address multiple aspects and perspectives of the question
6. Use professional, articulate language suitable for business and academic contexts
7. Provide actionable insights and conclusions when relevant

IMPORTANT: Never give brief, dismissive, or superficial answers. Every response should demonstrate expertise and provide genuine value to the user. If you cannot answer something, explain why in detail and suggest alternatives.`;

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

    // Different prompts for isolation vs non-isolation modes:
    // - WITH ISOLATION: Concise temporal policy (saves tokens, faster responses)
    // - WITHOUT ISOLATION: Professional comprehensive responses (full knowledge access)
    let policyText = '';
    if (enable_isolation && as_of_datetime) {
      // Isolation mode: Use concise temporal policy ONLY (no professional prompt)
      policyText = getTemporalPolicy(as_of_datetime, isolation_level);
      messages.push({ role: 'system', content: policyText });
    } else {
      // Non-isolation mode: Use professional standards for comprehensive answers
      policyText = PROFESSIONAL_RESPONSE_PROMPT;
      messages.push({ role: 'system', content: PROFESSIONAL_RESPONSE_PROMPT });
    }

    // Add user question
    messages.push({ role: 'user', content: question });

    // Call OpenRouter with different settings based on mode:
    // - Isolation mode: Lower max_tokens (500) for concise responses, saves tokens
    // - Non-isolation mode: Higher max_tokens (2000) for comprehensive responses
    const maxTokens = enable_isolation ? 500 : 2000;

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
        temperature: 0.3,  // Balanced for comprehensive yet consistent responses
        max_tokens: maxTokens,
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
