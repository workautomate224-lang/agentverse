'use client';

/**
 * Product Results Visualization Page
 * Displays comprehensive results from a simulation run with interactive charts.
 */

import { useParams, useRouter } from 'next/navigation';
import { useRef } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  TrendingUp,
  Lightbulb,
  Users,
  BarChart3,
  PieChart,
  Target,
  CheckCircle,
  AlertTriangle,
  Loader2,
  ChevronRight,
  FileText,
  Sparkles,
  Terminal,
  Download,
  Scale,
  Eye,
  Activity,
  Gem,
  Briefcase,
  Vote,
  Building,
} from 'lucide-react';
import { useProduct, useProductResult } from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';
import {
  InteractivePieChart,
  InteractiveBarChart,
  HeatmapChart,
  ExportButton,
} from '@/components/charts';
import {
  exportToCSV,
  exportToJSON,
  exportToPDF,
  exportToPNG,
  transformResultsForExport,
} from '@/lib/exportService';

// ============= Types =============

interface PredictionData {
  primary_prediction?: {
    outcome: string;
    value: number;
    confidence_interval: [number, number];
    confidence_level: number;
  };
  response_distribution?: Record<string, number>;
}

interface InsightData {
  key_insights?: Array<{
    theme: string;
    frequency: number;
    percentage: number;
  }>;
  emotion_analysis?: Record<string, number>;
  avg_intensity?: number;
}

interface SimulationOutcome {
  session_dynamics?: {
    avg_enthusiasm: number;
    avg_likelihood: number;
    sentiment_distribution?: {
      positive: number;
      neutral: number;
      negative: number;
    };
  };
  key_quotes?: string[];
  common_concerns?: string[];
}

interface StatisticalAnalysis {
  sample_size: number;
  margin_of_error?: number;
  avg_confidence?: number;
}

interface SegmentAnalysis {
  by_age?: Record<string, { count: number; avg?: number; distribution?: Record<string, number> }>;
  by_income?: Record<string, { count: number; avg?: number; distribution?: Record<string, number> }>;
  by_gender?: Record<string, { count: number; avg?: number; distribution?: Record<string, number> }>;
}

// Advanced AI Model Analysis Types
interface OracleAnalysis {
  market_metrics?: {
    avg_purchase_intent?: number;
    brand_preference_distribution?: Record<string, number>;
    avg_price_sensitivity?: number;
    avg_brand_loyalty?: number;
    avg_value_perception?: number;
  };
  segment_insights?: Array<{
    segment: string;
    size: number;
    characteristics: string[];
  }>;
  competitive_position?: Record<string, number>;
  purchase_drivers?: string[];
}

interface PulseAnalysis {
  election_metrics?: {
    vote_distribution?: Record<string, number>;
    avg_turnout_likelihood?: number;
    avg_persuadability?: number;
    avg_enthusiasm?: number;
    candidate_favorability?: Record<string, number>;
  };
  swing_voter_analysis?: {
    percentage: number;
    key_issues: string[];
    persuasion_factors: string[];
  };
  issue_importance?: Record<string, number>;
  demographic_splits?: Record<string, Record<string, number>>;
}

interface PrismAnalysis {
  policy_metrics?: {
    avg_support_level?: number;
    avg_trust_level?: number;
    avg_compliance_likelihood?: number;
    avg_impact_perception?: number;
    awareness_rate?: number;
  };
  stakeholder_positions?: Record<string, {
    support: number;
    influence: number;
    concerns: string[];
  }>;
  implementation_barriers?: string[];
  success_factors?: string[];
}

// ============= Helper Components =============

function ProgressBar({ value, label }: { value: number; label: string }) {
  return (
    <div className="mb-3">
      <div className="flex justify-between mb-1">
        <span className="text-xs font-mono text-white/60">{label}</span>
        <span className="text-xs font-mono text-white font-bold">
          {(value * 100).toFixed(1)}%
        </span>
      </div>
      <div className="w-full bg-white/10 h-1">
        <div
          className="h-1 bg-white/80"
          style={{ width: `${Math.min(100, value * 100)}%` }}
        />
      </div>
    </div>
  );
}

// ============= Main Component =============

export default function ProductResultPage() {
  const params = useParams();
  const router = useRouter();
  const productId = params.id as string;
  const resultId = params.resultId as string;
  const chartContainerRef = useRef<HTMLDivElement>(null);

  const { data: product, isLoading: productLoading } = useProduct(productId);
  const { data: result, isLoading: resultLoading, error: resultError } = useProductResult(productId, resultId);

  if (productLoading || resultLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <Loader2 className="w-4 h-4 animate-spin text-white/40" />
      </div>
    );
  }

  if (resultError || !result) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-black">
        <AlertTriangle className="w-8 h-8 text-red-400 mb-4" />
        <h2 className="text-sm font-mono font-bold text-white mb-2">RESULT NOT FOUND</h2>
        <p className="text-xs font-mono text-white/40 mb-4">The result you&apos;re looking for doesn&apos;t exist.</p>
        <Link href={`/dashboard/products/${productId}`}>
          <Button variant="outline" className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK TO PRODUCT
          </Button>
        </Link>
      </div>
    );
  }

  const predictions = result.predictions as PredictionData | null;
  const insights = result.insights as InsightData | null;
  const simulationOutcomes = result.simulation_outcomes as SimulationOutcome | null;
  const statisticalAnalysis = result.statistical_analysis as StatisticalAnalysis | null;
  const segmentAnalysis = result.segment_analysis as SegmentAnalysis | null;

  // Advanced AI Model Analysis
  const oracleAnalysis = result.oracle_analysis as OracleAnalysis | null;
  const pulseAnalysis = result.pulse_analysis as PulseAnalysis | null;
  const prismAnalysis = result.prism_analysis as PrismAnalysis | null;

  const productType = product?.product_type || 'predict';
  const isAdvancedModel = ['oracle', 'pulse', 'prism'].includes(productType);

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 mb-6">
        <Link href="/dashboard/products" className="hover:text-white/60">
          Products
        </Link>
        <ChevronRight className="h-3 w-3" />
        <Link href={`/dashboard/products/${productId}`} className="hover:text-white/60">
          {product?.name || 'Product'}
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-white/60">Results</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-white/5 transition-colors"
          >
            <ArrowLeft className="h-4 w-4 text-white/40" />
          </button>
          <div>
            <h1 className="text-xl font-mono font-bold text-white">
              Simulation Results
            </h1>
            <p className="text-xs font-mono text-white/40 mt-1">
              {product?.name} • <span className="text-white/60">{result.result_type.replace('_', ' ').toUpperCase()}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/dashboard/products/compare">
            <Button variant="outline" size="sm">
              <Scale className="w-3 h-3 mr-2" />
              COMPARE
            </Button>
          </Link>
          <ExportButton
            onExport={async (format) => {
              const filename = `${product?.name?.replace(/\s+/g, '_') || 'result'}_${resultId}`;

              try {
                switch (format) {
                  case 'json':
                    const exportData = {
                      product: {
                        id: product?.id,
                        name: product?.name,
                        type: product?.product_type,
                      },
                      result: {
                        id: result.id,
                        type: result.result_type,
                        executive_summary: result.executive_summary,
                        key_takeaways: result.key_takeaways,
                        confidence_score: result.confidence_score,
                        predictions,
                        insights,
                        simulation_outcomes: simulationOutcomes,
                        statistical_analysis: statisticalAnalysis,
                        segment_analysis: segmentAnalysis,
                        recommendations: result.recommendations,
                      },
                      exported_at: new Date().toISOString(),
                    };
                    exportToJSON(exportData, filename);
                    break;

                  case 'csv':
                    const csvData = transformResultsForExport({
                      sentiment_distribution: simulationOutcomes?.session_dynamics?.sentiment_distribution,
                      ...(predictions?.response_distribution && {
                        response_distribution: predictions.response_distribution,
                      }),
                    }) as unknown as Record<string, unknown>[];
                    exportToCSV(csvData, filename);
                    break;

                  case 'pdf':
                    const sections = [
                      {
                        heading: 'Executive Summary',
                        content: result.executive_summary || 'No summary available',
                        type: 'text' as const,
                      },
                      ...(predictions?.response_distribution ? [{
                        heading: 'Response Distribution',
                        content: Object.entries(predictions.response_distribution).map(([key, val]) => ({
                          response: key,
                          percentage: `${((val as number) * 100).toFixed(1)}%`,
                        })),
                        type: 'table' as const,
                      }] : []),
                      ...(result.recommendations?.length ? [{
                        heading: 'Recommendations',
                        content: result.recommendations.join('\n\n'),
                        type: 'text' as const,
                      }] : []),
                    ];
                    await exportToPDF(`${product?.name || 'Results'} Report`, sections, filename);
                    break;

                  case 'png':
                    if (chartContainerRef.current) {
                      await exportToPNG(chartContainerRef.current, filename);
                    }
                    break;
                }

                toast({
                  title: 'Export Complete',
                  description: `Results exported as ${format.toUpperCase()} file.`,
                  variant: 'success',
                });
              } catch (error) {
                toast({
                  title: 'Export Failed',
                  description: 'An error occurred during export.',
                  variant: 'destructive',
                });
              }
            }}
            availableFormats={['pdf', 'png', 'csv', 'json']}
          />
        </div>
      </div>

      {/* Executive Summary */}
      <div className="bg-white/5 border border-white/10 p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="w-8 h-8 bg-white/5 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white/60" />
          </div>
          <div className="flex-1">
            <h2 className="text-sm font-mono font-bold text-white mb-2">EXECUTIVE SUMMARY</h2>
            <p className="text-xs font-mono text-white/60 leading-relaxed">
              {result.executive_summary || 'No executive summary available.'}
            </p>
          </div>
        </div>

        {/* Key Takeaways */}
        {result.key_takeaways && result.key_takeaways.length > 0 && (
          <div className="mt-6 pt-4 border-t border-white/10">
            <h3 className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-3">
              KEY TAKEAWAYS
            </h3>
            <ul className="space-y-2">
              {result.key_takeaways.map((takeaway: string, index: number) => (
                <li key={index} className="flex items-start gap-2 text-xs font-mono text-white/60">
                  <CheckCircle className="h-3 w-3 text-green-400 flex-shrink-0 mt-0.5" />
                  <span>{takeaway}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 mb-1">
            <Target className="w-3 h-3" />
            CONFIDENCE
          </div>
          <p className="text-xl font-mono font-bold text-white">
            {(result.confidence_score * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] font-mono text-white/30">Overall prediction confidence</p>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 mb-1">
            <Users className="w-3 h-3" />
            SAMPLE SIZE
          </div>
          <p className="text-xl font-mono font-bold text-white">
            {statisticalAnalysis?.sample_size || 0}
          </p>
          <p className="text-[10px] font-mono text-white/30">Agents simulated</p>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 mb-1">
            <BarChart3 className="w-3 h-3" />
            MARGIN
          </div>
          <p className="text-xl font-mono font-bold text-white">
            {statisticalAnalysis?.margin_of_error
              ? `±${(statisticalAnalysis.margin_of_error * 100).toFixed(1)}%`
              : 'N/A'}
          </p>
          <p className="text-[10px] font-mono text-white/30">At 95% confidence level</p>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 mb-1">
            <TrendingUp className="w-3 h-3" />
            TYPE
          </div>
          <p className="text-xl font-mono font-bold text-white">
            {result.result_type.replace('_', ' ')}
          </p>
          <p className="text-[10px] font-mono text-white/30">{productType.toUpperCase()}</p>
        </div>
      </div>

      {/* Predictions Section (for Predict type) */}
      {productType === 'predict' && predictions && (
        <div className="bg-white/5 border border-white/10 p-6 mb-6" ref={chartContainerRef}>
          <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            PREDICTION RESULTS
          </h2>

          {predictions.primary_prediction && (
            <div className="bg-white/5 border border-white/10 p-4 mb-6">
              <h3 className="text-[10px] font-mono text-white/40 uppercase mb-2">
                Primary Prediction
              </h3>
              <p className="text-lg font-mono font-bold text-white mb-1">
                {predictions.primary_prediction.outcome}
              </p>
              <p className="text-sm font-mono text-white/60">
                <span className="text-white font-bold">{(predictions.primary_prediction.value * 100).toFixed(1)}%</span>
                <span className="text-[10px] ml-2">
                  (CI: {(predictions.primary_prediction.confidence_interval[0] * 100).toFixed(1)}% -
                  {(predictions.primary_prediction.confidence_interval[1] * 100).toFixed(1)}%)
                </span>
              </p>
            </div>
          )}

          {predictions.response_distribution && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Pie Chart */}
              <div>
                <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">
                  Response Distribution (Pie)
                </h3>
                <div className="h-80">
                  <InteractivePieChart
                    data={Object.entries(predictions.response_distribution).map(([name, value]) => ({
                      name,
                      value: (value as number) * 100,
                    }))}
                    title="Response Distribution"
                    onSliceClick={(data) => {
                      toast({
                        title: data.name,
                        description: `${data.value.toFixed(1)}% of responses`,
                      });
                    }}
                  />
                </div>
              </div>

              {/* Bar Chart */}
              <div>
                <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">
                  Response Distribution (Bar)
                </h3>
                <div className="h-80">
                  <InteractiveBarChart
                    data={Object.entries(predictions.response_distribution)
                      .sort(([, a], [, b]) => (b as number) - (a as number))
                      .map(([name, value]) => ({
                        name,
                        value: (value as number) * 100,
                      }))}
                    title="Response Distribution"
                    showMeanLine
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Insights Section (for Insight type) */}
      {productType === 'insight' && insights && (
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
            <Lightbulb className="h-4 w-4" />
            KEY INSIGHTS
          </h2>

          {insights.key_insights && insights.key_insights.length > 0 && (
            <div className="space-y-3 mb-6">
              {insights.key_insights.map((insight, index) => (
                <div key={index} className="flex items-center gap-4 p-3 bg-white/5 border border-white/10">
                  <div className="w-1 h-8 bg-white/40" />
                  <div className="flex-1">
                    <p className="text-xs font-mono text-white">{insight.theme}</p>
                    <p className="text-[10px] font-mono text-white/40">
                      Mentioned by {(insight.percentage * 100).toFixed(1)}% of respondents
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {insights.emotion_analysis && (
            <div>
              <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">
                Emotion Analysis
              </h3>
              <div className="h-80 mb-6">
                <InteractiveBarChart
                  data={Object.entries(insights.emotion_analysis)
                    .sort(([, a], [, b]) => (b as number) - (a as number))
                    .slice(0, 8)
                    .map(([name, value]) => ({
                      name: name.charAt(0).toUpperCase() + name.slice(1),
                      value: (value as number) * 100,
                    }))}
                  title="Emotion Distribution"
                  horizontal
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Simulation Outcomes (for Simulate type) */}
      {productType === 'simulate' && simulationOutcomes && (
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
            <Users className="h-4 w-4" />
            SIMULATION OUTCOMES
          </h2>

          {simulationOutcomes.session_dynamics && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
              <div className="bg-white/5 border border-white/10 p-4 text-center">
                <p className="text-[10px] font-mono text-white/40 uppercase mb-1">
                  Average Enthusiasm
                </p>
                <p className="text-2xl font-mono font-bold text-white">
                  {simulationOutcomes.session_dynamics.avg_enthusiasm.toFixed(1)}/10
                </p>
              </div>
              <div className="bg-white/5 border border-white/10 p-4 text-center">
                <p className="text-[10px] font-mono text-white/40 uppercase mb-1">
                  Likelihood to Act
                </p>
                <p className="text-2xl font-mono font-bold text-white">
                  {simulationOutcomes.session_dynamics.avg_likelihood.toFixed(1)}/10
                </p>
              </div>
              {simulationOutcomes.session_dynamics.sentiment_distribution && (
                <div className="bg-white/5 border border-white/10 p-4">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-3">
                    Sentiment Distribution
                  </p>
                  <div className="h-48">
                    <InteractivePieChart
                      data={[
                        { name: 'Positive', value: simulationOutcomes.session_dynamics.sentiment_distribution.positive * 100 },
                        { name: 'Neutral', value: simulationOutcomes.session_dynamics.sentiment_distribution.neutral * 100 },
                        { name: 'Negative', value: simulationOutcomes.session_dynamics.sentiment_distribution.negative * 100 },
                      ]}
                      title="Sentiment"
                      colors={['#22c55e', '#a3a3a3', '#ef4444']}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {simulationOutcomes.key_quotes && simulationOutcomes.key_quotes.length > 0 && (
            <div className="mb-6">
              <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">
                Key Quotes
              </h3>
              <div className="space-y-2">
                {simulationOutcomes.key_quotes.slice(0, 5).map((quote, index) => (
                  <div key={index} className="bg-white/5 border-l-2 border-white/40 p-3">
                    <p className="text-xs font-mono text-white/60 italic">&quot;{quote}&quot;</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {simulationOutcomes.common_concerns && simulationOutcomes.common_concerns.length > 0 && (
            <div>
              <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">
                Common Concerns
              </h3>
              <div className="flex flex-wrap gap-2">
                {simulationOutcomes.common_concerns.map((concern, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-red-500/20 text-red-400 text-[10px] font-mono"
                  >
                    {concern}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ORACLE Analysis (Market Intelligence) */}
      {productType === 'oracle' && oracleAnalysis && (
        <div className="bg-gradient-to-br from-purple-500/10 to-blue-500/5 border border-purple-500/20 p-6 mb-6" ref={chartContainerRef}>
          <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
            <Eye className="h-4 w-4 text-purple-400" />
            <span className="text-purple-400">ORACLE</span> MARKET INTELLIGENCE
          </h2>

          {/* Market Metrics */}
          {oracleAnalysis.market_metrics && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
              {oracleAnalysis.market_metrics.avg_purchase_intent !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Purchase Intent</p>
                  <p className="text-2xl font-mono font-bold text-purple-400">
                    {(oracleAnalysis.market_metrics.avg_purchase_intent * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {oracleAnalysis.market_metrics.avg_price_sensitivity !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Price Sensitivity</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {oracleAnalysis.market_metrics.avg_price_sensitivity.toFixed(1)}/10
                  </p>
                </div>
              )}
              {oracleAnalysis.market_metrics.avg_brand_loyalty !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Brand Loyalty</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {oracleAnalysis.market_metrics.avg_brand_loyalty.toFixed(1)}/10
                  </p>
                </div>
              )}
              {oracleAnalysis.market_metrics.avg_value_perception !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Value Perception</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {oracleAnalysis.market_metrics.avg_value_perception.toFixed(1)}/10
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Brand Preference Distribution */}
          {oracleAnalysis.market_metrics?.brand_preference_distribution && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <div>
                <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">Brand Preference Distribution</h3>
                <div className="h-80">
                  <InteractivePieChart
                    data={Object.entries(oracleAnalysis.market_metrics.brand_preference_distribution).map(([name, value]) => ({
                      name,
                      value: (value as number) * 100,
                    }))}
                    title="Brand Preference"
                    colors={['#a855f7', '#3b82f6', '#22c55e', '#eab308', '#ef4444']}
                  />
                </div>
              </div>
              <div>
                <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">Competitive Position</h3>
                {oracleAnalysis.competitive_position && (
                  <div className="h-80">
                    <InteractiveBarChart
                      data={Object.entries(oracleAnalysis.competitive_position)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .map(([name, value]) => ({
                          name,
                          value: (value as number) * 100,
                        }))}
                      title="Competitive Position"
                      horizontal
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Purchase Drivers */}
          {oracleAnalysis.purchase_drivers && oracleAnalysis.purchase_drivers.length > 0 && (
            <div>
              <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">Key Purchase Drivers</h3>
              <div className="flex flex-wrap gap-2">
                {oracleAnalysis.purchase_drivers.map((driver, index) => (
                  <span key={index} className="px-3 py-1.5 bg-purple-500/20 text-purple-300 text-xs font-mono">
                    {driver}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* PULSE Analysis (Political Simulation) */}
      {productType === 'pulse' && pulseAnalysis && (
        <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/5 border border-blue-500/20 p-6 mb-6" ref={chartContainerRef}>
          <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
            <Activity className="h-4 w-4 text-blue-400" />
            <span className="text-blue-400">PULSE</span> POLITICAL INTELLIGENCE
          </h2>

          {/* Election Metrics */}
          {pulseAnalysis.election_metrics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {pulseAnalysis.election_metrics.avg_turnout_likelihood !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Turnout Likelihood</p>
                  <p className="text-2xl font-mono font-bold text-blue-400">
                    {(pulseAnalysis.election_metrics.avg_turnout_likelihood * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {pulseAnalysis.election_metrics.avg_persuadability !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Persuadability</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {pulseAnalysis.election_metrics.avg_persuadability.toFixed(1)}/10
                  </p>
                </div>
              )}
              {pulseAnalysis.election_metrics.avg_enthusiasm !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Voter Enthusiasm</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {pulseAnalysis.election_metrics.avg_enthusiasm.toFixed(1)}/10
                  </p>
                </div>
              )}
              {pulseAnalysis.swing_voter_analysis && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Swing Voters</p>
                  <p className="text-2xl font-mono font-bold text-yellow-400">
                    {(pulseAnalysis.swing_voter_analysis.percentage * 100).toFixed(0)}%
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Vote Distribution */}
          {pulseAnalysis.election_metrics?.vote_distribution && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <div>
                <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">Vote Distribution</h3>
                <div className="h-80">
                  <InteractivePieChart
                    data={Object.entries(pulseAnalysis.election_metrics.vote_distribution).map(([name, value]) => ({
                      name,
                      value: (value as number) * 100,
                    }))}
                    title="Vote Distribution"
                    colors={['#3b82f6', '#ef4444', '#22c55e', '#a3a3a3', '#eab308']}
                  />
                </div>
              </div>
              {pulseAnalysis.issue_importance && (
                <div>
                  <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">Issue Importance</h3>
                  <div className="h-80">
                    <InteractiveBarChart
                      data={Object.entries(pulseAnalysis.issue_importance)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .slice(0, 8)
                        .map(([name, value]) => ({
                          name,
                          value: (value as number) * 100,
                        }))}
                      title="Issue Importance"
                      horizontal
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Swing Voter Analysis */}
          {pulseAnalysis.swing_voter_analysis && (
            <div className="bg-white/5 border border-white/10 p-4 mb-6">
              <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">Swing Voter Analysis</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {pulseAnalysis.swing_voter_analysis.key_issues && (
                  <div>
                    <p className="text-[10px] font-mono text-white/40 mb-2">Key Issues</p>
                    <div className="flex flex-wrap gap-2">
                      {pulseAnalysis.swing_voter_analysis.key_issues.map((issue, index) => (
                        <span key={index} className="px-2 py-1 bg-blue-500/20 text-blue-300 text-xs font-mono">
                          {issue}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {pulseAnalysis.swing_voter_analysis.persuasion_factors && (
                  <div>
                    <p className="text-[10px] font-mono text-white/40 mb-2">Persuasion Factors</p>
                    <div className="flex flex-wrap gap-2">
                      {pulseAnalysis.swing_voter_analysis.persuasion_factors.map((factor, index) => (
                        <span key={index} className="px-2 py-1 bg-cyan-500/20 text-cyan-300 text-xs font-mono">
                          {factor}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* PRISM Analysis (Public Sector) */}
      {productType === 'prism' && prismAnalysis && (
        <div className="bg-gradient-to-br from-emerald-500/10 to-teal-500/5 border border-emerald-500/20 p-6 mb-6" ref={chartContainerRef}>
          <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
            <Gem className="h-4 w-4 text-emerald-400" />
            <span className="text-emerald-400">PRISM</span> PUBLIC SECTOR ANALYTICS
          </h2>

          {/* Policy Metrics */}
          {prismAnalysis.policy_metrics && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
              {prismAnalysis.policy_metrics.avg_support_level !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Support Level</p>
                  <p className="text-2xl font-mono font-bold text-emerald-400">
                    {(prismAnalysis.policy_metrics.avg_support_level * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {prismAnalysis.policy_metrics.avg_trust_level !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Trust Level</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {prismAnalysis.policy_metrics.avg_trust_level.toFixed(1)}/10
                  </p>
                </div>
              )}
              {prismAnalysis.policy_metrics.avg_compliance_likelihood !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Compliance</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {(prismAnalysis.policy_metrics.avg_compliance_likelihood * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {prismAnalysis.policy_metrics.avg_impact_perception !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Impact Perception</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {prismAnalysis.policy_metrics.avg_impact_perception.toFixed(1)}/10
                  </p>
                </div>
              )}
              {prismAnalysis.policy_metrics.awareness_rate !== undefined && (
                <div className="bg-white/5 border border-white/10 p-4 text-center">
                  <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Awareness</p>
                  <p className="text-2xl font-mono font-bold text-white">
                    {(prismAnalysis.policy_metrics.awareness_rate * 100).toFixed(0)}%
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Stakeholder Positions */}
          {prismAnalysis.stakeholder_positions && Object.keys(prismAnalysis.stakeholder_positions).length > 0 && (
            <div className="mb-6">
              <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">Stakeholder Positions</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(prismAnalysis.stakeholder_positions).map(([name, data]) => (
                  <div key={name} className="bg-white/5 border border-white/10 p-4">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-xs font-mono text-white font-bold">{name}</p>
                      <span className={cn(
                        "text-[10px] font-mono px-1.5 py-0.5",
                        data.support > 0.6 ? "bg-green-500/20 text-green-400" :
                        data.support > 0.4 ? "bg-yellow-500/20 text-yellow-400" :
                        "bg-red-500/20 text-red-400"
                      )}>
                        {(data.support * 100).toFixed(0)}% Support
                      </span>
                    </div>
                    <ProgressBar value={data.influence / 10} label="Influence" />
                    {data.concerns && data.concerns.length > 0 && (
                      <div className="mt-2">
                        <p className="text-[10px] font-mono text-white/40 mb-1">Concerns:</p>
                        <div className="flex flex-wrap gap-1">
                          {data.concerns.slice(0, 3).map((concern, index) => (
                            <span key={index} className="text-[10px] font-mono text-white/50">
                              {concern}{index < Math.min(2, data.concerns.length - 1) ? ',' : ''}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Implementation Barriers & Success Factors */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {prismAnalysis.implementation_barriers && prismAnalysis.implementation_barriers.length > 0 && (
              <div className="bg-white/5 border border-white/10 p-4">
                <h3 className="text-[10px] font-mono text-red-400 uppercase mb-3">Implementation Barriers</h3>
                <div className="space-y-2">
                  {prismAnalysis.implementation_barriers.map((barrier, index) => (
                    <div key={index} className="flex items-start gap-2">
                      <AlertTriangle className="w-3 h-3 text-red-400 flex-shrink-0 mt-0.5" />
                      <span className="text-xs font-mono text-white/60">{barrier}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {prismAnalysis.success_factors && prismAnalysis.success_factors.length > 0 && (
              <div className="bg-white/5 border border-white/10 p-4">
                <h3 className="text-[10px] font-mono text-green-400 uppercase mb-3">Success Factors</h3>
                <div className="space-y-2">
                  {prismAnalysis.success_factors.map((factor, index) => (
                    <div key={index} className="flex items-start gap-2">
                      <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0 mt-0.5" />
                      <span className="text-xs font-mono text-white/60">{factor}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Segment Analysis */}
      {segmentAnalysis && Object.keys(segmentAnalysis).length > 0 && (
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
            <PieChart className="h-4 w-4" />
            SEGMENT ANALYSIS
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {segmentAnalysis.by_age && Object.keys(segmentAnalysis.by_age).length > 0 && (
              <div className="bg-white/5 border border-white/10 p-4">
                <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">By Age Group</h3>
                <div className="h-64">
                  <InteractiveBarChart
                    data={Object.entries(segmentAnalysis.by_age).map(([name, data]) => ({
                      name,
                      value: data.count,
                    }))}
                    title="Age Distribution"
                    horizontal
                  />
                </div>
              </div>
            )}

            {segmentAnalysis.by_income && Object.keys(segmentAnalysis.by_income).length > 0 && (
              <div className="bg-white/5 border border-white/10 p-4">
                <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">By Income</h3>
                <div className="h-64">
                  <InteractiveBarChart
                    data={Object.entries(segmentAnalysis.by_income).map(([name, data]) => ({
                      name,
                      value: data.count,
                    }))}
                    title="Income Distribution"
                    horizontal
                  />
                </div>
              </div>
            )}

            {segmentAnalysis.by_gender && Object.keys(segmentAnalysis.by_gender).length > 0 && (
              <div className="bg-white/5 border border-white/10 p-4">
                <h3 className="text-[10px] font-mono text-white/40 uppercase mb-4">By Gender</h3>
                <div className="h-64">
                  <InteractivePieChart
                    data={Object.entries(segmentAnalysis.by_gender).map(([name, data]) => ({
                      name: name.charAt(0).toUpperCase() + name.slice(1),
                      value: data.count,
                    }))}
                    title="Gender Distribution"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {result.recommendations && result.recommendations.length > 0 && (
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
            <FileText className="h-4 w-4" />
            RECOMMENDATIONS
          </h2>
          <div className="space-y-3">
            {result.recommendations.map((rec: string, index: number) => (
              <div
                key={index}
                className="flex items-start gap-4 p-3 bg-white/5 border border-white/10"
              >
                <div className="w-6 h-6 bg-white/10 text-white flex items-center justify-center font-mono text-xs flex-shrink-0">
                  {index + 1}
                </div>
                <p className="text-xs font-mono text-white/60">{rec}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>RESULT DETAIL</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
