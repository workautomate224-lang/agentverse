'use client';

import { useState } from 'react';
import {
  Clock,
  Send,
  Shield,
  ShieldOff,
  Calendar,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Zap,
} from 'lucide-react';

interface TestResult {
  answer: string;
  policy_injected: boolean;
  cutoff_date: string | null;
  isolation_level: number | null;
  model: string;
  policy_text: string | null;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

interface QuickTest {
  label: string;
  question: string;
  date: string;
  description: string;
}

const QUICK_TESTS: QuickTest[] = [
  {
    label: '2024 US Election',
    question: 'Who won the 2024 US Presidential Election?',
    date: '2024-11-06T00:00:00Z',
    description: 'Election Day - results should not be known',
  },
  {
    label: 'Claude 3.5 Sonnet',
    question: 'What is Claude 3.5 Sonnet and when was it released?',
    date: '2024-01-01T00:00:00Z',
    description: 'Before release (June 2024) - should not know',
  },
  {
    label: 'GPT-4o Launch',
    question: 'Tell me about OpenAI GPT-4o model.',
    date: '2024-04-01T00:00:00Z',
    description: 'Before release (May 2024) - should not know',
  },
  {
    label: 'COVID-19 Pandemic',
    question: 'Is there a pandemic happening right now?',
    date: '2019-12-01T00:00:00Z',
    description: 'Before COVID - should not know about pandemic',
  },
];

const ISOLATION_LEVELS = [
  { value: 1, label: 'Level 1 - Basic', description: 'Trust but verify' },
  { value: 2, label: 'Level 2 - Strict', description: 'Enforce cutoff (Recommended)' },
  { value: 3, label: 'Level 3 - Audit-First', description: 'Maximum restriction' },
];

export default function TemporalTestPage() {
  const [question, setQuestion] = useState('');
  const [asOfDate, setAsOfDate] = useState('2024-11-06T00:00:00');
  const [isolationLevel, setIsolationLevel] = useState(2);
  const [enableIsolation, setEnableIsolation] = useState(true);
  const [loading, setLoading] = useState(false);
  const [withIsolationResult, setWithIsolationResult] = useState<TestResult | null>(null);
  const [withoutIsolationResult, setWithoutIsolationResult] = useState<TestResult | null>(null);
  const [showPolicy, setShowPolicy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState(false);

  const runTest = async (withIsolation: boolean) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/temporal-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          as_of_datetime: asOfDate,
          isolation_level: isolationLevel,
          enable_isolation: withIsolation,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to run test');
      }

      if (withIsolation) {
        setWithIsolationResult(data);
      } else {
        setWithoutIsolationResult(data);
      }

      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const runComparisonTest = async () => {
    setLoading(true);
    setError(null);
    setWithIsolationResult(null);
    setWithoutIsolationResult(null);

    try {
      // Run both tests in parallel
      const [withResult, withoutResult] = await Promise.all([
        fetch('/api/temporal-test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question,
            as_of_datetime: asOfDate,
            isolation_level: isolationLevel,
            enable_isolation: true,
          }),
        }).then(r => r.json()),
        fetch('/api/temporal-test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question,
            as_of_datetime: asOfDate,
            isolation_level: isolationLevel,
            enable_isolation: false,
          }),
        }).then(r => r.json()),
      ]);

      setWithIsolationResult(withResult);
      setWithoutIsolationResult(withoutResult);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickTest = (test: QuickTest) => {
    setQuestion(test.question);
    setAsOfDate(test.date.replace('Z', ''));
  };

  const handleSubmit = async () => {
    if (!question.trim()) return;

    if (compareMode) {
      await runComparisonTest();
    } else {
      await runTest(enableIsolation);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="min-h-screen bg-black p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="border border-cyan-500/30 bg-black/50 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="w-8 h-8 text-cyan-400" />
            <h1 className="text-2xl font-mono text-cyan-400">
              TEMPORAL KNOWLEDGE ISOLATION TEST
            </h1>
          </div>
          <p className="text-gray-400 font-mono text-sm">
            Test that the LLM respects temporal boundaries. When isolation is enabled,
            the model should NOT reveal knowledge from after the cutoff date.
          </p>
        </div>

        {/* Quick Tests */}
        <div className="border border-white/10 bg-black/30 p-4">
          <h2 className="text-sm font-mono text-white/70 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            QUICK TEST SCENARIOS
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {QUICK_TESTS.map((test) => (
              <button
                key={test.label}
                onClick={() => handleQuickTest(test)}
                className="border border-white/20 hover:border-cyan-500/50 bg-black/50
                         hover:bg-cyan-500/10 p-3 text-left transition-all"
              >
                <div className="font-mono text-cyan-400 text-sm mb-1">{test.label}</div>
                <div className="text-xs text-gray-500">{test.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Configuration Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Input Configuration */}
          <div className="border border-white/10 bg-black/30 p-4 space-y-4">
            <h2 className="text-sm font-mono text-white/70 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-purple-400" />
              TEST CONFIGURATION
            </h2>

            {/* As-of Date */}
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-2">
                AS-OF DATETIME (CUTOFF)
              </label>
              <input
                type="datetime-local"
                value={asOfDate}
                onChange={(e) => setAsOfDate(e.target.value)}
                className="w-full bg-black border border-white/20 text-white font-mono
                         p-2 focus:border-cyan-500 focus:outline-none"
              />
              <div className="text-xs text-gray-500 mt-1">
                Model will simulate knowledge as of: {formatDate(asOfDate)}
              </div>
            </div>

            {/* Isolation Level */}
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-2">
                ISOLATION LEVEL
              </label>
              <select
                value={isolationLevel}
                onChange={(e) => setIsolationLevel(Number(e.target.value))}
                className="w-full bg-black border border-white/20 text-white font-mono
                         p-2 focus:border-cyan-500 focus:outline-none"
              >
                {ISOLATION_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label} - {level.description}
                  </option>
                ))}
              </select>
            </div>

            {/* Isolation Toggle */}
            <div className="flex items-center justify-between p-3 border border-white/10 bg-black/50">
              <div className="flex items-center gap-2">
                {enableIsolation ? (
                  <Shield className="w-5 h-5 text-green-400" />
                ) : (
                  <ShieldOff className="w-5 h-5 text-red-400" />
                )}
                <span className="font-mono text-sm text-white">
                  Temporal Isolation
                </span>
              </div>
              <button
                onClick={() => setEnableIsolation(!enableIsolation)}
                className={`w-12 h-6 rounded-full transition-colors ${
                  enableIsolation ? 'bg-green-500' : 'bg-red-500/50'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full transition-transform ${
                    enableIsolation ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>

            {/* Compare Mode Toggle */}
            <div className="flex items-center justify-between p-3 border border-white/10 bg-black/50">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                <span className="font-mono text-sm text-white">
                  Side-by-Side Comparison
                </span>
              </div>
              <button
                onClick={() => setCompareMode(!compareMode)}
                className={`w-12 h-6 rounded-full transition-colors ${
                  compareMode ? 'bg-yellow-500' : 'bg-gray-600'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full transition-transform ${
                    compareMode ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Right: Question Input */}
          <div className="border border-white/10 bg-black/30 p-4 space-y-4">
            <h2 className="text-sm font-mono text-white/70 flex items-center gap-2">
              <Send className="w-4 h-4 text-cyan-400" />
              QUESTION
            </h2>

            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Enter a question to test temporal isolation..."
              className="w-full h-32 bg-black border border-white/20 text-white font-mono
                       p-3 focus:border-cyan-500 focus:outline-none resize-none"
            />

            <button
              onClick={handleSubmit}
              disabled={loading || !question.trim()}
              className="w-full bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500
                       text-cyan-400 font-mono py-3 flex items-center justify-center gap-2
                       disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  PROCESSING...
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  {compareMode ? 'RUN COMPARISON TEST' : 'RUN TEST'}
                </>
              )}
            </button>

            {error && (
              <div className="p-3 border border-red-500/50 bg-red-500/10 text-red-400 font-mono text-sm">
                ERROR: {error}
              </div>
            )}
          </div>
        </div>

        {/* Results Panel */}
        {(withIsolationResult || withoutIsolationResult) && (
          <div className="space-y-4">
            {compareMode ? (
              /* Side-by-side comparison */
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* With Isolation */}
                <div className="border border-green-500/30 bg-black/30 p-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Shield className="w-5 h-5 text-green-400" />
                    <span className="font-mono text-green-400">WITH ISOLATION</span>
                    <span className="ml-auto px-2 py-1 bg-green-500/20 border border-green-500
                                   text-green-400 text-xs font-mono">
                      PROTECTED
                    </span>
                  </div>
                  {withIsolationResult ? (
                    <div className="text-white font-mono text-sm whitespace-pre-wrap bg-black/50 p-3 border border-white/10">
                      {withIsolationResult.answer}
                    </div>
                  ) : (
                    <div className="text-gray-500 font-mono text-sm">Loading...</div>
                  )}
                </div>

                {/* Without Isolation */}
                <div className="border border-red-500/30 bg-black/30 p-4">
                  <div className="flex items-center gap-2 mb-4">
                    <ShieldOff className="w-5 h-5 text-red-400" />
                    <span className="font-mono text-red-400">WITHOUT ISOLATION</span>
                    <span className="ml-auto px-2 py-1 bg-red-500/20 border border-red-500
                                   text-red-400 text-xs font-mono">
                      UNPROTECTED
                    </span>
                  </div>
                  {withoutIsolationResult ? (
                    <div className="text-white font-mono text-sm whitespace-pre-wrap bg-black/50 p-3 border border-white/10">
                      {withoutIsolationResult.answer}
                    </div>
                  ) : (
                    <div className="text-gray-500 font-mono text-sm">Loading...</div>
                  )}
                </div>
              </div>
            ) : (
              /* Single result */
              <div className={`border ${enableIsolation ? 'border-green-500/30' : 'border-white/10'} bg-black/30 p-4`}>
                <div className="flex items-center gap-2 mb-4">
                  {enableIsolation ? (
                    <>
                      <Shield className="w-5 h-5 text-green-400" />
                      <span className="font-mono text-green-400">RESPONSE (ISOLATION ACTIVE)</span>
                      <span className="ml-auto px-2 py-1 bg-green-500/20 border border-green-500
                                     text-green-400 text-xs font-mono">
                        CUTOFF: {formatDate(withIsolationResult?.cutoff_date || asOfDate)}
                      </span>
                    </>
                  ) : (
                    <>
                      <ShieldOff className="w-5 h-5 text-red-400" />
                      <span className="font-mono text-red-400">RESPONSE (NO ISOLATION)</span>
                      <span className="ml-auto px-2 py-1 bg-red-500/20 border border-red-500
                                     text-red-400 text-xs font-mono">
                        UNPROTECTED
                      </span>
                    </>
                  )}
                </div>
                <div className="text-white font-mono text-sm whitespace-pre-wrap bg-black/50 p-4 border border-white/10">
                  {enableIsolation ? withIsolationResult?.answer : withoutIsolationResult?.answer}
                </div>
              </div>
            )}

            {/* Policy Display (Collapsible) */}
            {withIsolationResult?.policy_text && (
              <div className="border border-white/10 bg-black/30">
                <button
                  onClick={() => setShowPolicy(!showPolicy)}
                  className="w-full p-3 flex items-center justify-between text-left
                           hover:bg-white/5 transition-colors"
                >
                  <span className="font-mono text-sm text-gray-400">
                    VIEW INJECTED POLICY TEXT
                  </span>
                  {showPolicy ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  )}
                </button>
                {showPolicy && (
                  <div className="p-4 border-t border-white/10">
                    <pre className="text-xs text-green-400/80 font-mono whitespace-pre-wrap overflow-auto max-h-96">
                      {withIsolationResult.policy_text}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Test Result Analysis */}
            {compareMode && withIsolationResult && withoutIsolationResult && (
              <div className="border border-purple-500/30 bg-black/30 p-4">
                <h3 className="font-mono text-purple-400 mb-3 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  TEST ANALYSIS
                </h3>
                <div className="space-y-2 font-mono text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">Question:</span>
                    <span className="text-white">{question}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">Cutoff Date:</span>
                    <span className="text-cyan-400">{formatDate(asOfDate)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">Responses Differ:</span>
                    {withIsolationResult.answer !== withoutIsolationResult.answer ? (
                      <span className="text-green-400 flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" /> YES - Isolation working
                      </span>
                    ) : (
                      <span className="text-yellow-400 flex items-center gap-1">
                        <AlertTriangle className="w-4 h-4" /> NO - Responses identical
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Info Panel */}
        <div className="border border-white/10 bg-black/30 p-4">
          <h3 className="font-mono text-white/70 text-sm mb-2">HOW IT WORKS</h3>
          <ul className="text-xs font-mono text-gray-500 space-y-1">
            <li>1. Select a cutoff date (as-of datetime) for the temporal simulation</li>
            <li>2. Enter a question that tests knowledge from after the cutoff date</li>
            <li>3. With isolation enabled, the LLM receives a system prompt enforcing the cutoff</li>
            <li>4. The model should refuse to reveal information from after the cutoff date</li>
            <li>5. Use comparison mode to see the difference with/without isolation</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
