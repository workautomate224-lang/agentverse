'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, Plus, X, BarChart3, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api, Product, ComparisonResponse, ComparisonResultItem } from '@/lib/api';
import {
  InteractiveBarChart,
  ComparisonChart,
  SignificanceIndicator,
  ExportButton,
} from '@/components/charts';
import { exportToCSV, exportToJSON, exportToPDF, transformComparisonForExport } from '@/lib/exportService';

export default function ProductComparisonPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([]);
  const [isSelectingProduct, setIsSelectingProduct] = useState(false);

  // Initialize from URL params
  useEffect(() => {
    const ids = searchParams.get('ids');
    if (ids) {
      setSelectedProductIds(ids.split(',').filter(Boolean));
    }
  }, [searchParams]);

  // Fetch all products for selection
  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => api.listProducts(),
  });

  // Fetch comparison data when products are selected
  const { data: comparisonData, isLoading: comparisonLoading, error: comparisonError } = useQuery({
    queryKey: ['comparison', selectedProductIds],
    queryFn: () => api.compareProducts(selectedProductIds),
    enabled: selectedProductIds.length >= 2,
  });

  const products = productsData || [];
  const availableProducts = products.filter(
    (p: Product) => !selectedProductIds.includes(p.id) && p.status === 'completed'
  );

  const selectedProducts = products.filter((p: Product) => selectedProductIds.includes(p.id));

  const addProduct = (productId: string) => {
    const newIds = [...selectedProductIds, productId];
    setSelectedProductIds(newIds);
    setIsSelectingProduct(false);
    // Update URL
    router.push(`/dashboard/products/compare?ids=${newIds.join(',')}`);
  };

  const removeProduct = (productId: string) => {
    const newIds = selectedProductIds.filter(id => id !== productId);
    setSelectedProductIds(newIds);
    if (newIds.length > 0) {
      router.push(`/dashboard/products/compare?ids=${newIds.join(',')}`);
    } else {
      router.push('/dashboard/products/compare');
    }
  };

  const handleExport = async (format: 'pdf' | 'png' | 'csv' | 'json') => {
    if (!comparisonData) return;

    const filename = `product-comparison-${new Date().toISOString().split('T')[0]}`;

    switch (format) {
      case 'csv':
        const csvData = transformComparisonForExport(
          comparisonData.products.map((p: ComparisonResultItem) => ({
            id: p.product_id,
            name: p.product_name,
            data: p.data,
          }))
        );
        exportToCSV(csvData, filename);
        break;

      case 'json':
        exportToJSON(comparisonData, filename);
        break;

      case 'pdf':
        const sections = [
          {
            heading: 'Products Compared',
            content: comparisonData.products.map((p: ComparisonResultItem) => p.product_name).join(', '),
            type: 'text' as const,
          },
          {
            heading: 'Comparison Data',
            content: transformComparisonForExport(
              comparisonData.products.map((p: ComparisonResultItem) => ({
                id: p.product_id,
                name: p.product_name,
                data: p.data,
              }))
            ),
            type: 'table' as const,
          },
        ];
        await exportToPDF('Product Comparison Report', sections, filename);
        break;
    }
  };

  // Transform comparison data for charts
  const getChartData = () => {
    if (!comparisonData) return { sentiment: [], purchase: [] };

    const sentimentData: { name: string; [key: string]: string | number }[] = [];
    const purchaseData: { name: string; [key: string]: string | number }[] = [];

    // Build sentiment comparison data
    const sentimentCategories = ['positive', 'neutral', 'negative'];
    sentimentCategories.forEach(category => {
      const item: { name: string; [key: string]: string | number } = { name: category };
      comparisonData.products.forEach((product: ComparisonResultItem) => {
        const dist = product.data?.sentiment_distribution as Record<string, number> | undefined;
        item[product.product_name] = dist?.[category] || 0;
      });
      sentimentData.push(item);
    });

    // Build purchase likelihood comparison data
    const purchaseCategories = ['very_likely', 'likely', 'neutral', 'unlikely', 'very_unlikely'];
    purchaseCategories.forEach(category => {
      const item: { name: string; [key: string]: string | number } = { name: category.replace('_', ' ') };
      comparisonData.products.forEach((product: ComparisonResultItem) => {
        const dist = product.data?.purchase_likelihood as Record<string, number> | undefined;
        item[product.product_name] = dist?.[category] || 0;
      });
      purchaseData.push(item);
    });

    return { sentiment: sentimentData, purchase: purchaseData };
  };

  const chartData = getChartData();
  const productNames = selectedProducts.map((p: Product) => p.name);

  return (
    <div className="min-h-screen bg-black text-white p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/dashboard/results')}
            className="p-2 hover:bg-white/10 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-mono font-bold">PRODUCT COMPARISON</h1>
            <p className="text-white/60 text-sm font-mono">
              Compare results across multiple products
            </p>
          </div>
        </div>

        {comparisonData && (
          <ExportButton
            onExport={handleExport}
            availableFormats={['pdf', 'csv', 'json']}
          />
        )}
      </div>

      {/* Product Selection */}
      <div className="mb-8">
        <h2 className="text-sm font-mono text-white/60 mb-4">SELECTED PRODUCTS</h2>
        <div className="flex flex-wrap gap-3">
          {selectedProducts.map((product: Product) => (
            <div
              key={product.id}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20"
            >
              <span className="font-mono text-sm">{product.name}</span>
              <button
                onClick={() => removeProduct(product.id)}
                className="p-1 hover:bg-white/10 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}

          {selectedProductIds.length < 5 && (
            <div className="relative">
              <button
                onClick={() => setIsSelectingProduct(!isSelectingProduct)}
                className="flex items-center gap-2 px-4 py-2 border border-dashed border-white/30 hover:border-white/50 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span className="font-mono text-sm">Add Product</span>
              </button>

              {isSelectingProduct && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsSelectingProduct(false)}
                  />
                  <div className="absolute top-full left-0 mt-2 w-64 bg-black border border-white/20 z-50 max-h-60 overflow-y-auto">
                    {productsLoading ? (
                      <div className="p-4 text-center">
                        <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                      </div>
                    ) : availableProducts.length === 0 ? (
                      <div className="p-4 text-center text-white/40 text-sm font-mono">
                        No more products available
                      </div>
                    ) : (
                      availableProducts.map((product: Product) => (
                        <button
                          key={product.id}
                          onClick={() => addProduct(product.id)}
                          className="w-full px-4 py-3 text-left hover:bg-white/5 transition-colors border-b border-white/10 last:border-0"
                        >
                          <p className="font-mono text-sm">{product.name}</p>
                          <p className="text-xs text-white/40">{product.persona_count} personas</p>
                        </button>
                      ))
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {selectedProductIds.length < 2 && (
          <p className="text-white/40 text-sm font-mono mt-4">
            Select at least 2 products to compare
          </p>
        )}
      </div>

      {/* Comparison Results */}
      {selectedProductIds.length >= 2 && (
        <>
          {comparisonLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin" />
              <span className="ml-3 font-mono">Loading comparison data...</span>
            </div>
          ) : comparisonError ? (
            <div className="border border-red-500/30 bg-red-500/10 p-6">
              <p className="text-red-400 font-mono">Failed to load comparison data</p>
            </div>
          ) : comparisonData ? (
            <div className="space-y-8">
              {/* Statistical Significance */}
              {comparisonData.statistical_significance && Object.keys(comparisonData.statistical_significance).length > 0 && (
                <div className="border border-white/10 p-6">
                  <h3 className="text-sm font-mono text-white/60 mb-4">STATISTICAL SIGNIFICANCE</h3>
                  <div className="flex flex-wrap gap-4">
                    {Object.entries(comparisonData.statistical_significance).map(([metric, sig]) => (
                      <div key={metric} className="flex items-center gap-2">
                        <span className="text-xs font-mono text-white/60">{metric.replace('_', ' ')}:</span>
                        <SignificanceIndicator pValue={sig.p_value} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sentiment Comparison */}
              <div className="border border-white/10 p-6">
                <h3 className="text-sm font-mono text-white/60 mb-4">SENTIMENT COMPARISON</h3>
                <div className="h-80">
                  <ComparisonChart
                    data={chartData.sentiment}
                    seriesKeys={productNames}
                    title="Sentiment Distribution"
                    chartType="bar"
                  />
                </div>
              </div>

              {/* Purchase Likelihood Comparison */}
              <div className="border border-white/10 p-6">
                <h3 className="text-sm font-mono text-white/60 mb-4">PURCHASE LIKELIHOOD COMPARISON</h3>
                <div className="h-80">
                  <ComparisonChart
                    data={chartData.purchase}
                    seriesKeys={productNames}
                    title="Purchase Likelihood"
                    chartType="bar"
                  />
                </div>
              </div>

              {/* Summary Statistics */}
              <div className="border border-white/10 p-6">
                <h3 className="text-sm font-mono text-white/60 mb-4">SUMMARY STATISTICS</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm font-mono">
                    <thead>
                      <tr className="border-b border-white/20">
                        <th className="text-left py-3 px-4">Metric</th>
                        {comparisonData.products.map((p: ComparisonResultItem) => (
                          <th key={p.product_id} className="text-right py-3 px-4">
                            {p.product_name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-white/10">
                        <td className="py-3 px-4 text-white/60">Positive Sentiment %</td>
                        {comparisonData.products.map((p: ComparisonResultItem) => {
                          const dist = p.data?.sentiment_distribution as Record<string, number> | undefined;
                          const total = dist ? Object.values(dist).reduce((a, b) => a + b, 0) : 0;
                          const positive = dist?.positive || 0;
                          const pct = total > 0 ? ((positive / total) * 100).toFixed(1) : '0.0';
                          return (
                            <td key={p.product_id} className="text-right py-3 px-4">
                              {pct}%
                            </td>
                          );
                        })}
                      </tr>
                      <tr className="border-b border-white/10">
                        <td className="py-3 px-4 text-white/60">Purchase Intent (Likely+)</td>
                        {comparisonData.products.map((p: ComparisonResultItem) => {
                          const dist = p.data?.purchase_likelihood as Record<string, number> | undefined;
                          const total = dist ? Object.values(dist).reduce((a, b) => a + b, 0) : 0;
                          const likely = (dist?.very_likely || 0) + (dist?.likely || 0);
                          const pct = total > 0 ? ((likely / total) * 100).toFixed(1) : '0.0';
                          return (
                            <td key={p.product_id} className="text-right py-3 px-4">
                              {pct}%
                            </td>
                          );
                        })}
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : null}
        </>
      )}

      {/* Empty State */}
      {selectedProductIds.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 border border-white/10">
          <BarChart3 className="w-16 h-16 text-white/20 mb-4" />
          <h3 className="font-mono text-lg mb-2">No Products Selected</h3>
          <p className="text-white/40 text-sm font-mono text-center max-w-md">
            Select products above to compare their simulation results side by side.
            You can compare up to 5 products at once.
          </p>
        </div>
      )}
    </div>
  );
}
