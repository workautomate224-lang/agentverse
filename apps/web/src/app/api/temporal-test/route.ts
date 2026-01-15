/**
 * Temporal Knowledge Isolation Test API
 *
 * This endpoint demonstrates temporal isolation by injecting
 * a backtest policy into LLM system prompts.
 *
 * Reference: temporal.md (Single Source of Truth)
 *
 * Smart Auto-Trigger:
 * - auto_classify: Enable LLM-based pre-classification (default: true)
 * - web_search: Manual override (null = auto, true/false = force)
 * - thinking_mode: Manual override (null = auto, true/false = force)
 */

import { NextResponse } from 'next/server';

const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

/**
 * Smart Classifier - Quick heuristic check for prompts
 * Returns classification decision for web_search and thinking_mode
 */
interface ClassificationResult {
  web_search: boolean;
  thinking_mode: boolean;
  confidence: number;
  reasoning: string;
}

function quickClassify(prompt: string): ClassificationResult {
  const promptLower = prompt.toLowerCase();

  // Strong web search indicators
  const webSearchKeywords = [
    'today', 'latest', 'current', 'now', 'recent',
    'stock price', 'weather', 'news', 'happening',
    '2025', '2026', 'right now', 'this week', 'this month',
    'breaking', 'update', 'score', 'result', 'live'
  ];

  // Strong thinking mode indicators
  const thinkingKeywords = [
    'analyze', 'analyse', 'compare', 'evaluate', 'pros and cons',
    'step by step', 'explain why', 'reasoning', 'trade-off',
    'design', 'architect', 'plan', 'strategy', 'decision',
    'advantages and disadvantages', 'in-depth', 'comprehensive analysis',
    'impact', 'implications', 'consider'
  ];

  // Count matches
  const webSearchScore = webSearchKeywords.filter(kw => promptLower.includes(kw)).length;
  const thinkingScore = thinkingKeywords.filter(kw => promptLower.includes(kw)).length;

  // Determine classification
  const needsWebSearch = webSearchScore >= 1;
  const needsThinking = thinkingScore >= 1;

  const confidence = Math.min(0.9, 0.5 + (webSearchScore + thinkingScore) * 0.1);

  return {
    web_search: needsWebSearch,
    thinking_mode: needsThinking,
    confidence,
    reasoning: `Detected ${webSearchScore} web search keywords, ${thinkingScore} thinking keywords`
  };
}

/**
 * LLM-based classification for more accurate decisions
 * Falls back to heuristic if API call fails or times out
 */
async function classifyWithLLM(
  prompt: string,
  apiKey: string
): Promise<ClassificationResult> {
  const classifierPrompt = `You are a prompt classifier. Analyze this prompt and determine capabilities needed.

PROMPT: ${prompt}

OUTPUT FORMAT (JSON only, no markdown):
{"web_search": true/false, "thinking_mode": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}

RULES:
- web_search=true if: current events, news, real-time data, stock prices, weather, "today", "latest", "2025", "2026"
- thinking_mode=true if: analysis, comparison, step-by-step reasoning, pros/cons, complex problems`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout

    const response = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://agentverse.io',
        'X-Title': 'AgentVerse SmartClassifier',
      },
      body: JSON.stringify({
        model: 'openai/gpt-4o-mini',
        messages: [{ role: 'user', content: classifierPrompt }],
        temperature: 0,
        max_tokens: 150,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content || '';

    // Parse JSON from response
    let jsonContent = content.trim();
    if (jsonContent.startsWith('```')) {
      jsonContent = jsonContent.split('```')[1];
      if (jsonContent.startsWith('json')) {
        jsonContent = jsonContent.slice(4);
      }
    }

    const result = JSON.parse(jsonContent);
    return {
      web_search: result.web_search === true,
      thinking_mode: result.thinking_mode === true,
      confidence: typeof result.confidence === 'number' ? result.confidence : 0.7,
      reasoning: result.reasoning || 'LLM classification',
    };
  } catch {
    // Fallback to heuristic on any error
    return quickClassify(prompt);
  }
}

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
 * Also supports advanced features:
 * - web_search: Enable web search for up-to-date information
 * - thinking_mode: Enable extended thinking/reasoning mode
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      as_of_datetime,
      question,
      isolation_level = 2,
      enable_isolation = true,
      // Smart Auto-Trigger (enabled by default for user-facing API)
      auto_classify = true,
      // Manual overrides: null = auto, true/false = force
      web_search = null as boolean | null,
      web_search_max_results = 5,
      thinking_mode = null as boolean | null,
      thinking_budget_tokens = null,
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

    // =========================================================================
    // Smart Auto-Classification
    // =========================================================================
    // If auto_classify is enabled and no manual override provided,
    // classify the prompt to determine if web_search or thinking_mode is needed.
    // This only applies when NOT in isolation mode (live mode).
    // =========================================================================
    let classification: ClassificationResult | null = null;
    let finalWebSearch = web_search ?? false;
    let finalThinkingMode = thinking_mode ?? false;

    if (!enable_isolation && auto_classify) {
      // Check if we need to auto-classify (only if no manual override)
      const needsClassification = web_search === null || thinking_mode === null;

      if (needsClassification) {
        // Use LLM classification for better accuracy
        classification = await classifyWithLLM(question, apiKey);

        // Apply classification results, respecting manual overrides
        // Priority: manual_override > auto_classification > default(false)
        if (web_search === null) {
          finalWebSearch = classification.web_search;
        } else {
          finalWebSearch = web_search;
        }

        if (thinking_mode === null) {
          finalThinkingMode = classification.thinking_mode;
        } else {
          finalThinkingMode = thinking_mode;
        }
      } else {
        // Manual overrides provided, use them directly
        finalWebSearch = web_search ?? false;
        finalThinkingMode = thinking_mode ?? false;
      }
    } else if (!enable_isolation) {
      // Auto-classify disabled, use manual values (default to false)
      finalWebSearch = web_search ?? false;
      finalThinkingMode = thinking_mode ?? false;
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
    const maxTokens = enable_isolation ? 500 : (finalThinkingMode ? 4000 : 2000);

    // Build request payload
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const requestPayload: Record<string, any> = {
      model: 'openai/gpt-5.2',  // Upgraded from gpt-4o-mini for better accuracy
      messages,
      temperature: 0.3,  // Balanced for comprehensive yet consistent responses
      max_tokens: maxTokens,
    };

    // Add web search plugin if enabled (only in non-isolated mode)
    // Reference: https://openrouter.ai/docs/guides/features/plugins/web-search
    if (finalWebSearch && !enable_isolation) {
      requestPayload.plugins = [
        {
          id: 'web',
          max_results: Math.min(Math.max(web_search_max_results, 1), 10)  // Clamp 1-10
        }
      ];
    }

    // Add thinking/reasoning mode if enabled (only in non-isolated mode)
    // Reference: https://openrouter.ai/docs/guides/routing/model-variants/thinking
    if (finalThinkingMode && !enable_isolation) {
      requestPayload.include_reasoning = true;
      if (thinking_budget_tokens) {
        requestPayload.reasoning = {
          max_tokens: thinking_budget_tokens
        };
      }
    }

    const response = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': process.env.NEXTAUTH_URL || 'https://agentverse.io',
        'X-Title': 'AgentVerse Temporal Test',
      },
      body: JSON.stringify(requestPayload),
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

    const message = data.choices[0].message;
    const answer = message?.content || 'No response generated';

    // Extract reasoning output if present (thinking mode)
    let reasoning = null;
    if (message?.reasoning) {
      reasoning = message.reasoning;
    } else if (message?.reasoning_content) {
      reasoning = message.reasoning_content;
    }

    // Extract web search results if present (from annotations)
    let webSearchResults = null;
    if (finalWebSearch && message?.annotations) {
      webSearchResults = message.annotations
        .filter((a: { type: string }) => a.type === 'url_citation')
        .map((a: { url?: string; title?: string }) => ({
          url: a.url,
          title: a.title
        }));
    }

    return NextResponse.json({
      answer,
      policy_injected: enable_isolation,
      cutoff_date: enable_isolation ? as_of_datetime : null,
      isolation_level: enable_isolation ? isolation_level : null,
      model: 'openai/gpt-5.2',
      policy_text: enable_isolation ? policyText : null,
      usage: data.usage,
      // Smart Auto-Trigger info
      auto_classify_enabled: auto_classify && !enable_isolation,
      classification: classification ? {
        web_search: classification.web_search,
        thinking_mode: classification.thinking_mode,
        confidence: classification.confidence,
        reasoning: classification.reasoning,
      } : null,
      // Manual overrides (null = auto-decided, true/false = manually set)
      manual_web_search: web_search,
      manual_thinking_mode: thinking_mode,
      // Final applied features
      web_search_enabled: finalWebSearch && !enable_isolation,
      thinking_mode_enabled: finalThinkingMode && !enable_isolation,
      reasoning: reasoning,
      web_search_results: webSearchResults,
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Internal server error', details: errorMessage },
      { status: 500 }
    );
  }
}
