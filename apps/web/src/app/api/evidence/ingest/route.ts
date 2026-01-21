import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import crypto from 'crypto';

/**
 * Evidence URL Ingestion API
 * Reference: DEMO2_MVP_EXECUTION.md Task 4
 *
 * Responsibilities:
 * - Fetch + snapshot URLs (user-provided)
 * - Record provenance + hash
 * - Extract minimal signals for persona generation
 * - Apply temporal compliance status per source
 */

// Evidence status based on temporal compliance
export type EvidenceStatus = 'PASS' | 'WARN' | 'FAIL';

export interface EvidenceUrl {
  id: string;
  url: string;
  title: string;
  content_hash: string;
  content_length: number;
  fetched_at: string;
  status: EvidenceStatus;
  status_reason: string;
  extracted_signals: ExtractedSignals;
  provenance: EvidenceProvenance;
}

interface ExtractedSignals {
  keywords: string[];
  topics: string[];
  entities: string[];
  sentiment?: 'positive' | 'negative' | 'neutral';
  content_type: string;
}

interface EvidenceProvenance {
  source_url: string;
  fetch_timestamp: string;
  content_hash: string;
  snapshot_version: string;
  temporal_check: TemporalCheck;
}

interface TemporalCheck {
  as_of_datetime?: string;
  source_date_detected?: string;
  compliance_status: EvidenceStatus;
  compliance_reason: string;
}

interface IngestRequest {
  urls: string[];
  project_id: string;
  as_of_datetime?: string;
}

interface IngestResponse {
  success: boolean;
  evidence_items: EvidenceUrl[];
  summary: {
    total: number;
    passed: number;
    warned: number;
    failed: number;
  };
}

// Simple text extraction and signal detection
function extractSignals(text: string, url: string): ExtractedSignals {
  // Extract keywords (simple word frequency)
  const words = text.toLowerCase().match(/\b[a-z]{4,}\b/g) || [];
  const wordFreq: Record<string, number> = {};
  words.forEach(w => { wordFreq[w] = (wordFreq[w] || 0) + 1; });
  const sortedWords = Object.entries(wordFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([word]) => word);

  // Detect content type from URL
  let contentType = 'article';
  if (url.includes('news')) contentType = 'news';
  else if (url.includes('research') || url.includes('study')) contentType = 'research';
  else if (url.includes('gov')) contentType = 'government';
  else if (url.includes('survey') || url.includes('poll')) contentType = 'survey';

  // Simple sentiment detection
  const positiveWords = ['good', 'great', 'positive', 'success', 'growth', 'improve'];
  const negativeWords = ['bad', 'negative', 'decline', 'fail', 'problem', 'crisis'];
  const positiveCount = positiveWords.filter(w => text.toLowerCase().includes(w)).length;
  const negativeCount = negativeWords.filter(w => text.toLowerCase().includes(w)).length;
  const sentiment = positiveCount > negativeCount ? 'positive' :
                   negativeCount > positiveCount ? 'negative' : 'neutral';

  // Extract potential topic categories
  const topics: string[] = [];
  const topicPatterns: Record<string, string[]> = {
    'politics': ['election', 'vote', 'government', 'policy', 'political', 'party'],
    'economy': ['economy', 'market', 'financial', 'business', 'trade', 'gdp'],
    'technology': ['tech', 'digital', 'software', 'ai', 'data', 'internet'],
    'health': ['health', 'medical', 'hospital', 'disease', 'treatment', 'vaccine'],
    'environment': ['climate', 'environment', 'carbon', 'pollution', 'sustainable'],
    'social': ['social', 'community', 'demographic', 'population', 'culture']
  };

  Object.entries(topicPatterns).forEach(([topic, patterns]) => {
    if (patterns.some(p => text.toLowerCase().includes(p))) {
      topics.push(topic);
    }
  });

  // Extract entities (capitalized words that might be names/orgs)
  const entityPattern = /\b[A-Z][a-z]+ [A-Z][a-z]+\b/g;
  const entities = [...new Set(text.match(entityPattern) || [])].slice(0, 5);

  return {
    keywords: sortedWords,
    topics: topics.length > 0 ? topics : ['general'],
    entities,
    sentiment,
    content_type: contentType
  };
}

// Check temporal compliance of the source
function checkTemporalCompliance(
  url: string,
  content: string,
  asOfDateTime?: string
): TemporalCheck {
  const now = new Date();
  const asOf = asOfDateTime ? new Date(asOfDateTime) : null;

  // Try to detect date from content
  const datePatterns = [
    /(\d{4}-\d{2}-\d{2})/,
    /(\w+ \d{1,2}, \d{4})/,
    /(\d{1,2} \w+ \d{4})/
  ];

  let detectedDate: string | undefined;
  for (const pattern of datePatterns) {
    const match = content.match(pattern);
    if (match) {
      try {
        const parsed = new Date(match[1]);
        if (!isNaN(parsed.getTime())) {
          detectedDate = parsed.toISOString();
          break;
        }
      } catch {
        // Continue to next pattern
      }
    }
  }

  // Determine compliance status
  let status: EvidenceStatus = 'PASS';
  let reason = 'Source appears current and valid';

  // Check if source is too old (more than 1 year)
  if (detectedDate) {
    const sourceDate = new Date(detectedDate);
    const oneYearAgo = new Date(now);
    oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);

    if (sourceDate < oneYearAgo) {
      status = 'WARN';
      reason = 'Source date is more than 1 year old';
    }

    // Check against as_of_datetime if provided
    if (asOf && sourceDate > asOf) {
      status = 'FAIL';
      reason = `Source date (${sourceDate.toISOString().split('T')[0]}) is after cutoff (${asOf.toISOString().split('T')[0]})`;
    }
  } else {
    // No date detected
    status = 'WARN';
    reason = 'Could not detect publication date from source';
  }

  // Check URL patterns for known unreliable sources
  const unreliablePatterns = ['facebook.com/post', 'twitter.com/status', 'reddit.com/r/'];
  if (unreliablePatterns.some(p => url.includes(p))) {
    status = 'WARN';
    reason = 'Social media source - verify independently';
  }

  return {
    as_of_datetime: asOfDateTime,
    source_date_detected: detectedDate,
    compliance_status: status,
    compliance_reason: reason
  };
}

// Fetch URL content with timeout and error handling
async function fetchUrlContent(url: string): Promise<{ content: string; title: string } | null> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'AgentVerse Evidence Collector/1.0'
      }
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return null;
    }

    const html = await response.text();

    // Extract title
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
    const title = titleMatch ? titleMatch[1].trim() : new URL(url).hostname;

    // Strip HTML tags for content analysis
    const content = html
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 50000); // Limit content size

    return { content, title };
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest) {
  try {
    // Check authentication
    const session = await getServerSession(authOptions);
    if (!session?.user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body: IngestRequest = await request.json();
    const { urls, project_id, as_of_datetime } = body;

    if (!urls || urls.length === 0) {
      return NextResponse.json(
        { error: 'No URLs provided' },
        { status: 400 }
      );
    }

    if (!project_id) {
      return NextResponse.json(
        { error: 'Project ID required' },
        { status: 400 }
      );
    }

    const evidenceItems: EvidenceUrl[] = [];
    let passed = 0, warned = 0, failed = 0;

    // Process each URL
    for (const url of urls) {
      try {
        // Validate URL format
        new URL(url);
      } catch {
        // Invalid URL - mark as failed
        evidenceItems.push({
          id: `ev-${crypto.randomUUID()}`,
          url,
          title: 'Invalid URL',
          content_hash: '',
          content_length: 0,
          fetched_at: new Date().toISOString(),
          status: 'FAIL',
          status_reason: 'Invalid URL format',
          extracted_signals: {
            keywords: [],
            topics: [],
            entities: [],
            content_type: 'unknown'
          },
          provenance: {
            source_url: url,
            fetch_timestamp: new Date().toISOString(),
            content_hash: '',
            snapshot_version: '1.0.0',
            temporal_check: {
              as_of_datetime,
              compliance_status: 'FAIL',
              compliance_reason: 'Invalid URL format'
            }
          }
        });
        failed++;
        continue;
      }

      // Fetch URL content
      const fetchResult = await fetchUrlContent(url);

      if (!fetchResult) {
        evidenceItems.push({
          id: `ev-${crypto.randomUUID()}`,
          url,
          title: 'Fetch Failed',
          content_hash: '',
          content_length: 0,
          fetched_at: new Date().toISOString(),
          status: 'FAIL',
          status_reason: 'Failed to fetch URL content',
          extracted_signals: {
            keywords: [],
            topics: [],
            entities: [],
            content_type: 'unknown'
          },
          provenance: {
            source_url: url,
            fetch_timestamp: new Date().toISOString(),
            content_hash: '',
            snapshot_version: '1.0.0',
            temporal_check: {
              as_of_datetime,
              compliance_status: 'FAIL',
              compliance_reason: 'Failed to fetch URL'
            }
          }
        });
        failed++;
        continue;
      }

      const { content, title } = fetchResult;

      // Generate content hash
      const contentHash = crypto
        .createHash('sha256')
        .update(content)
        .digest('hex');

      // Extract signals
      const signals = extractSignals(content, url);

      // Check temporal compliance
      const temporalCheck = checkTemporalCompliance(url, content, as_of_datetime);

      const evidence: EvidenceUrl = {
        id: `ev-${crypto.randomUUID()}`,
        url,
        title,
        content_hash: contentHash,
        content_length: content.length,
        fetched_at: new Date().toISOString(),
        status: temporalCheck.compliance_status,
        status_reason: temporalCheck.compliance_reason,
        extracted_signals: signals,
        provenance: {
          source_url: url,
          fetch_timestamp: new Date().toISOString(),
          content_hash: contentHash,
          snapshot_version: '1.0.0',
          temporal_check: temporalCheck
        }
      };

      evidenceItems.push(evidence);

      switch (temporalCheck.compliance_status) {
        case 'PASS': passed++; break;
        case 'WARN': warned++; break;
        case 'FAIL': failed++; break;
      }
    }

    const response: IngestResponse = {
      success: true,
      evidence_items: evidenceItems,
      summary: {
        total: evidenceItems.length,
        passed,
        warned,
        failed
      }
    };

    return NextResponse.json(response);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: `Evidence ingestion failed: ${errorMessage}` },
      { status: 500 }
    );
  }
}
