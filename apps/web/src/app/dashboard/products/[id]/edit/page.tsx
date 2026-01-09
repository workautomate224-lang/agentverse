'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Save,
  Loader2,
  Terminal,
  Settings,
  AlertTriangle,
  Users,
  Target,
  FileText,
} from 'lucide-react';
import { useProduct, useUpdateProduct } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

export default function ProductEditPage() {
  const params = useParams();
  const router = useRouter();
  const productId = params.id as string;

  const { data: product, isLoading: productLoading, error: productError } = useProduct(productId);
  const updateProduct = useUpdateProduct();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    persona_count: 100,
    confidence_target: 0.9,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (product) {
      setFormData({
        name: product.name || '',
        description: product.description || '',
        persona_count: product.persona_count || 100,
        confidence_target: product.confidence_target || 0.9,
      });
    }
  }, [product]);

  if (productLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-white/40" />
      </div>
    );
  }

  if (productError || !product) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-4" />
          <h2 className="text-lg font-mono font-bold text-red-400 mb-2">PRODUCT NOT FOUND</h2>
          <p className="text-sm font-mono text-red-400/70 mb-4">The requested product could not be loaded.</p>
          <Link href="/dashboard/products">
            <Button variant="outline" className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5">
              BACK TO PRODUCTS
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    try {
      await updateProduct.mutateAsync({
        productId,
        data: formData,
      });
      setSuccess(true);
      setTimeout(() => {
        router.push(`/dashboard/products/${productId}`);
      }, 1000);
    } catch (err: any) {
      setError(err.detail || err.message || 'Failed to update product');
    }
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-8">
        <Link href={`/dashboard/products/${productId}`}>
          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/5 font-mono text-xs mb-4">
            <ArrowLeft className="w-3 h-3 mr-2" />
            BACK TO PRODUCT
          </Button>
        </Link>

        <div className="flex items-center gap-2 mb-1">
          <Settings className="w-4 h-4 text-white/60" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Edit Product</span>
        </div>
        <h1 className="text-xl font-mono font-bold text-white">{product.name}</h1>
        <p className="text-sm font-mono text-white/50 mt-1">Update product configuration</p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <h2 className="text-sm font-mono font-bold text-white uppercase mb-6 flex items-center gap-2">
            <FileText className="w-4 h-4 text-white/60" />
            BASIC INFORMATION
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">PRODUCT NAME</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 bg-black border border-white/20 text-white font-mono text-sm focus:border-white/40 focus:outline-none"
                placeholder="Enter product name"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">DESCRIPTION</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 bg-black border border-white/20 text-white font-mono text-sm focus:border-white/40 focus:outline-none resize-none"
                placeholder="Enter product description"
              />
            </div>
          </div>
        </div>

        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <h2 className="text-sm font-mono font-bold text-white uppercase mb-6 flex items-center gap-2">
            <Users className="w-4 h-4 text-white/60" />
            SIMULATION SETTINGS
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">PERSONA COUNT</label>
              <input
                type="number"
                value={formData.persona_count}
                onChange={(e) => setFormData({ ...formData, persona_count: parseInt(e.target.value) || 100 })}
                min={10}
                max={10000}
                className="w-full px-3 py-2 bg-black border border-white/20 text-white font-mono text-sm focus:border-white/40 focus:outline-none"
              />
              <p className="text-[10px] font-mono text-white/30 mt-1">Number of AI personas to simulate (10-10,000)</p>
            </div>

            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">CONFIDENCE TARGET</label>
              <input
                type="number"
                value={formData.confidence_target}
                onChange={(e) => setFormData({ ...formData, confidence_target: parseFloat(e.target.value) || 0.9 })}
                min={0.5}
                max={0.99}
                step={0.01}
                className="w-full px-3 py-2 bg-black border border-white/20 text-white font-mono text-sm focus:border-white/40 focus:outline-none"
              />
              <p className="text-[10px] font-mono text-white/30 mt-1">Target confidence level (0.5-0.99)</p>
            </div>
          </div>
        </div>

        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <h2 className="text-sm font-mono font-bold text-white uppercase mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-white/60" />
            PRODUCT INFO (READ-ONLY)
          </h2>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-mono text-white/40 mb-1">TYPE</label>
              <p className="text-sm font-mono text-white">{product.product_type?.toUpperCase()}</p>
            </div>
            <div>
              <label className="block text-xs font-mono text-white/40 mb-1">SUB-TYPE</label>
              <p className="text-sm font-mono text-white">{product.sub_type?.toUpperCase() || 'N/A'}</p>
            </div>
            <div>
              <label className="block text-xs font-mono text-white/40 mb-1">STATUS</label>
              <p className="text-sm font-mono text-white">{product.status?.toUpperCase()}</p>
            </div>
          </div>
        </div>

        {/* Error/Success */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 p-4 mb-6">
            <p className="text-sm font-mono text-red-400">{error}</p>
          </div>
        )}

        {success && (
          <div className="bg-green-500/10 border border-green-500/30 p-4 mb-6">
            <p className="text-sm font-mono text-green-400">Product updated successfully. Redirecting...</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between">
          <Link href={`/dashboard/products/${productId}`}>
            <Button
              type="button"
              variant="outline"
              className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5"
            >
              CANCEL
            </Button>
          </Link>
          <Button
            type="submit"
            disabled={updateProduct.isPending}
            
          >
            {updateProduct.isPending ? (
              <Loader2 className="w-3 h-3 mr-2 animate-spin" />
            ) : (
              <Save className="w-3 h-3 mr-2" />
            )}
            SAVE CHANGES
          </Button>
        </div>
      </form>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PRODUCT EDIT MODULE</span>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
