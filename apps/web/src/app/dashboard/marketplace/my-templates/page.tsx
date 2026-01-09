'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Plus,
  ArrowLeft,
  Terminal,
  Store,
  Loader2,
  Star,
  Users,
  MoreVertical,
  Edit,
  Trash2,
  Eye,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useMyTemplates, useDeleteMarketplaceTemplate } from '@/hooks/useApi';
import type { MarketplaceTemplateListItem } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function MyTemplatesPage() {
  const { data: templatesData, isLoading } = useMyTemplates();
  const deleteTemplate = useDeleteMarketplaceTemplate();

  const templates = templatesData?.items || [];

  const handleDelete = async (templateId: string) => {
    if (confirm('Are you sure you want to delete this template?')) {
      await deleteTemplate.mutateAsync(templateId);
    }
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard/marketplace">
          <button className="p-2 hover:bg-white/5 transition-colors">
            <ArrowLeft className="w-4 h-4 text-white/60" />
          </button>
        </Link>
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Marketplace / My Templates
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-mono font-bold text-white">My Templates</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Manage your published templates
          </p>
        </div>
        <Link href="/dashboard/marketplace/publish">
          <Button size="sm">
            <Plus className="w-3 h-3 mr-2" />
            PUBLISH NEW
          </Button>
        </Link>
      </div>

      {/* Templates List */}
      <div className="bg-white/5 border border-white/10">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Store className="w-3 h-3 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Your Templates
            </span>
          </div>
          <span className="text-xs font-mono text-white/30">
            {templates.length} templates
          </span>
        </div>

        {isLoading ? (
          <div className="p-12 flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-white/40" />
          </div>
        ) : templates.length > 0 ? (
          <div className="divide-y divide-white/5">
            {templates.map((template: MarketplaceTemplateListItem) => (
              <TemplateRow
                key={template.id}
                template={template}
                onDelete={() => handleDelete(template.id)}
              />
            ))}
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Store className="w-5 h-5 text-white/30" />
            </div>
            <p className="text-sm font-mono text-white/60 mb-1">
              No templates published
            </p>
            <p className="text-xs font-mono text-white/30 mb-4">
              Share your scenarios with the community
            </p>
            <Link href="/dashboard/marketplace/publish">
              <Button
                variant="outline"
                size="sm"
                className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
              >
                PUBLISH TEMPLATE
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>MARKETPLACE MODULE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function TemplateRow({
  template,
  onDelete,
}: {
  template: MarketplaceTemplateListItem;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors">
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <StatusBadge status={template.status} />
        <div className="flex-1 min-w-0">
          <Link
            href={`/dashboard/marketplace/${template.slug}`}
            className="text-sm font-mono font-medium text-white hover:text-white/80 truncate block"
          >
            {template.name}
          </Link>
          <div className="flex items-center gap-3 text-[10px] font-mono text-white/40 mt-1">
            <span>{template.category_name || 'General'}</span>
            <span className="flex items-center gap-1">
              <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
              {template.rating_average?.toFixed(1) || '-'}
            </span>
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {template.usage_count} uses
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDistanceToNow(new Date(template.created_at), {
                addSuffix: true,
              })}
            </span>
          </div>
        </div>
      </div>

      <div className="relative">
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="p-2 hover:bg-white/10 transition-colors"
        >
          <MoreVertical className="w-4 h-4 text-white/40" />
        </button>

        {showMenu && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setShowMenu(false)}
            />
            <div className="absolute right-0 mt-1 w-40 bg-black border border-white/20 z-20">
              <Link
                href={`/dashboard/marketplace/${template.slug}`}
                className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 hover:bg-white/10"
              >
                <Eye className="w-3 h-3" />
                View Details
              </Link>
              <button
                onClick={() => {
                  setShowMenu(false);
                  // TODO: Implement edit
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-mono text-white/60 hover:bg-white/10"
              >
                <Edit className="w-3 h-3" />
                Edit Template
              </button>
              <button
                onClick={() => {
                  setShowMenu(false);
                  onDelete();
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-mono text-red-400 hover:bg-white/10"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    { icon: typeof CheckCircle; className: string; label: string }
  > = {
    draft: {
      icon: Clock,
      className: 'bg-white/10 text-white/50',
      label: 'DRAFT',
    },
    pending_review: {
      icon: AlertCircle,
      className: 'bg-yellow-500/20 text-yellow-400',
      label: 'PENDING',
    },
    published: {
      icon: CheckCircle,
      className: 'bg-green-500/20 text-green-400',
      label: 'LIVE',
    },
    rejected: {
      icon: XCircle,
      className: 'bg-red-500/20 text-red-400',
      label: 'REJECTED',
    },
    archived: {
      icon: Clock,
      className: 'bg-white/10 text-white/40',
      label: 'ARCHIVED',
    },
  };

  const { icon: Icon, className, label } = config[status] || config.draft;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase',
        className
      )}
    >
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}
