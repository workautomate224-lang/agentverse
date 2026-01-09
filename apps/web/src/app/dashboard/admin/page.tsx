'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  ShieldCheck,
  Users,
  Settings,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  Loader2,
  ChevronRight,
  Terminal,
  Building,
  Gauge,
  FileText,
  Search,
  Filter,
  RefreshCw,
  Key,
  RotateCcw,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Calendar,
  Info,
  Cpu,
  Play,
  Edit2,
  Trash2,
  Plus,
  DollarSign,
  Zap,
  BarChart3,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useLLMProfiles,
  useLLMCostReport,
  useAvailableLLMModels,
  useUpdateLLMProfile,
  useDeleteLLMProfile,
  useTestLLMProfile,
} from '@/hooks/useApi';
import type { LLMProfile } from '@/lib/api';

/**
 * Admin Page (Role-Gated)
 * Per Interaction_design.md §5.20:
 * - Tenants management
 * - Quotas and concurrency
 * - Audit logs
 * - Policy flags
 */
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<'tenants' | 'quotas' | 'secrets' | 'audit' | 'policies' | 'models'>('tenants');
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Admin Panel
            </span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Administration</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Tenancy, quotas, audit logs, and policy management
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="font-mono text-xs border-white/20 text-white/60 hover:bg-white/5 hover:text-white"
        >
          <RefreshCw className="w-3 h-3 mr-2" />
          REFRESH
        </Button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        <StatCard
          icon={Building}
          label="TENANTS"
          value="12"
          subtext="Active organizations"
        />
        <StatCard
          icon={Users}
          label="USERS"
          value="156"
          subtext="Across all tenants"
        />
        <StatCard
          icon={Gauge}
          label="QUOTA USAGE"
          value="68%"
          subtext="Average utilization"
          status="warning"
        />
        <StatCard
          icon={Activity}
          label="AUDIT EVENTS"
          value="2.4K"
          subtext="Last 24 hours"
        />
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 mb-6 border-b border-white/10 pb-1">
        <TabButton
          active={activeTab === 'tenants'}
          onClick={() => setActiveTab('tenants')}
          icon={Building}
          label="Tenants"
        />
        <TabButton
          active={activeTab === 'quotas'}
          onClick={() => setActiveTab('quotas')}
          icon={Gauge}
          label="Quotas"
        />
        <TabButton
          active={activeTab === 'secrets'}
          onClick={() => setActiveTab('secrets')}
          icon={Key}
          label="Secrets"
        />
        <TabButton
          active={activeTab === 'audit'}
          onClick={() => setActiveTab('audit')}
          icon={FileText}
          label="Audit Logs"
        />
        <TabButton
          active={activeTab === 'policies'}
          onClick={() => setActiveTab('policies')}
          icon={ShieldCheck}
          label="Policies"
        />
        <TabButton
          active={activeTab === 'models'}
          onClick={() => setActiveTab('models')}
          icon={Cpu}
          label="Models"
        />
      </div>

      {/* Search Bar */}
      <div className="relative mb-6">
        <Search className="w-3 h-3 absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
        <input
          type="text"
          placeholder={`Search ${activeTab}...`}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
        />
      </div>

      {/* Tab Content */}
      {activeTab === 'tenants' && <TenantsTab />}
      {activeTab === 'quotas' && <QuotasTab />}
      {activeTab === 'secrets' && <SecretsTab />}
      {activeTab === 'audit' && <AuditTab />}
      {activeTab === 'policies' && <PoliciesTab />}
      {activeTab === 'models' && <ModelsTab />}

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>ADMIN PANEL</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ElementType;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-4 py-2 text-xs font-mono transition-colors',
        active
          ? 'bg-white text-black'
          : 'text-white/60 hover:text-white hover:bg-white/5'
      )}
    >
      <Icon className="w-3 h-3" />
      {label}
    </button>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  subtext,
  status,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  subtext: string;
  status?: 'good' | 'warning' | 'error';
}) {
  return (
    <div className={cn(
      'bg-white/5 border p-4 hover:bg-white/[0.07] transition-colors',
      status === 'good' ? 'border-green-500/30' :
      status === 'warning' ? 'border-yellow-500/30' :
      status === 'error' ? 'border-red-500/30' : 'border-white/10'
    )}>
      <div className="flex items-start justify-between mb-2">
        <Icon className={cn(
          'w-4 h-4',
          status === 'good' ? 'text-green-400' :
          status === 'warning' ? 'text-yellow-400' :
          status === 'error' ? 'text-red-400' : 'text-white/40'
        )} />
      </div>
      <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider">{label}</p>
      <p className={cn(
        'text-2xl font-mono font-bold mt-1',
        status === 'good' ? 'text-green-400' :
        status === 'warning' ? 'text-yellow-400' :
        status === 'error' ? 'text-red-400' : 'text-white'
      )}>{value}</p>
      <p className="text-[10px] font-mono text-white/30 mt-1">{subtext}</p>
    </div>
  );
}

// Tenants Tab Component
function TenantsTab() {
  const tenants = [
    { id: '1', name: 'Acme Corp', slug: 'acme', users: 24, projects: 12, status: 'active' },
    { id: '2', name: 'TechStart Inc', slug: 'techstart', users: 8, projects: 5, status: 'active' },
    { id: '3', name: 'Global Research', slug: 'global-research', users: 45, projects: 28, status: 'active' },
    { id: '4', name: 'Beta Labs', slug: 'beta-labs', users: 3, projects: 1, status: 'trial' },
  ];

  return (
    <div className="bg-white/5 border border-white/10">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Building className="w-3 h-3 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Tenants
          </span>
        </div>
        <Button size="sm" className="h-7 text-[10px]">
          ADD TENANT
        </Button>
      </div>
      <div className="divide-y divide-white/5">
        {tenants.map((tenant) => (
          <div key={tenant.id} className="p-4 hover:bg-white/5 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-mono text-white font-medium">{tenant.name}</h4>
                  <span className={cn(
                    'text-[9px] font-mono uppercase px-1.5 py-0.5',
                    tenant.status === 'active' ? 'bg-green-500/20 text-green-400' :
                    tenant.status === 'trial' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  )}>
                    {tenant.status}
                  </span>
                </div>
                <div className="flex items-center gap-4 mt-1 text-[10px] font-mono text-white/40">
                  <span>@{tenant.slug}</span>
                  <span className="flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {tenant.users} users
                  </span>
                  <span className="flex items-center gap-1">
                    <Database className="w-3 h-3" />
                    {tenant.projects} projects
                  </span>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-white/30" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Quotas Tab Component
function QuotasTab() {
  const [selectedTenant, setSelectedTenant] = useState<string>('all');

  // Global quotas (system-wide)
  const globalQuotas = [
    { name: 'Concurrent Runs', used: 28, limit: 50, unit: 'runs' },
    { name: 'Total Storage', used: 245.8, limit: 500, unit: 'GB' },
    { name: 'API Requests', used: 85000, limit: 100000, unit: '/hr' },
    { name: 'Active Jobs', used: 12, limit: 100, unit: 'jobs' },
  ];

  // Per-tenant quotas
  const tenantQuotas = [
    {
      tenantId: 'acme',
      tenantName: 'Acme Corp',
      tier: 'enterprise',
      quotas: {
        concurrentRuns: { used: 8, limit: 20 },
        storage: { used: 45.2, limit: 100 },
        apiRequests: { used: 8500, limit: 50000 },
        projects: { used: 12, limit: 50 },
        personas: { used: 5000, limit: 100000 },
      },
    },
    {
      tenantId: 'techstart',
      tenantName: 'TechStart Inc',
      tier: 'pro',
      quotas: {
        concurrentRuns: { used: 3, limit: 10 },
        storage: { used: 12.5, limit: 50 },
        apiRequests: { used: 2100, limit: 20000 },
        projects: { used: 5, limit: 20 },
        personas: { used: 1500, limit: 50000 },
      },
    },
    {
      tenantId: 'beta-labs',
      tenantName: 'Beta Labs',
      tier: 'trial',
      quotas: {
        concurrentRuns: { used: 1, limit: 2 },
        storage: { used: 0.8, limit: 5 },
        apiRequests: { used: 450, limit: 1000 },
        projects: { used: 1, limit: 3 },
        personas: { used: 200, limit: 1000 },
      },
    },
  ];

  // Concurrency controls
  const concurrencySettings = {
    maxGlobalConcurrentRuns: 50,
    maxTenantConcurrentRuns: 20,
    queueDepth: 100,
    queueTimeout: 300, // seconds
    workerPoolSize: 10,
    backpressureThreshold: 80, // percentage
  };

  return (
    <div className="space-y-6">
      {/* Global System Quotas */}
      <div className="bg-white/5 border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Gauge className="w-3 h-3 text-cyan-400" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              System-Wide Resource Usage
            </h3>
          </div>
          <span className="text-[9px] font-mono text-cyan-400/60 bg-cyan-400/10 px-2 py-0.5">
            REAL-TIME
          </span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {globalQuotas.map((quota) => {
            const percentage = (quota.used / quota.limit) * 100;
            const status = percentage >= 90 ? 'error' : percentage >= 70 ? 'warning' : 'good';
            return (
              <div key={quota.name} className="p-4 bg-white/5 border border-white/10">
                <p className="text-[10px] font-mono text-white/40 uppercase">{quota.name}</p>
                <p className={cn(
                  'text-xl font-mono font-bold mt-1',
                  status === 'error' ? 'text-red-400' :
                  status === 'warning' ? 'text-yellow-400' : 'text-white'
                )}>
                  {quota.used.toLocaleString()}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <div className="flex-1 bg-white/10 h-1">
                    <div
                      className={cn(
                        'h-1 transition-all',
                        status === 'good' ? 'bg-green-500' :
                        status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                      )}
                      style={{ width: `${Math.min(percentage, 100)}%` }}
                    />
                  </div>
                  <span className="text-[9px] font-mono text-white/40">
                    {Math.round(percentage)}%
                  </span>
                </div>
                <p className="text-[9px] font-mono text-white/30 mt-1">
                  of {quota.limit.toLocaleString()} {quota.unit}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Concurrency Controls */}
      <div className="bg-white/5 border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Settings className="w-3 h-3 text-white/40" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Concurrency Controls
            </h3>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] font-mono border-white/20 text-white/60 hover:bg-white/5"
          >
            CONFIGURE
          </Button>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <ConcurrencyControl
            label="Max Global Concurrent Runs"
            value={concurrencySettings.maxGlobalConcurrentRuns}
            description="Maximum runs across all tenants"
          />
          <ConcurrencyControl
            label="Max Per-Tenant Concurrent"
            value={concurrencySettings.maxTenantConcurrentRuns}
            description="Maximum runs per tenant"
          />
          <ConcurrencyControl
            label="Queue Depth"
            value={concurrencySettings.queueDepth}
            description="Max pending jobs in queue"
          />
          <ConcurrencyControl
            label="Queue Timeout"
            value={`${concurrencySettings.queueTimeout}s`}
            description="Max wait time in queue"
          />
          <ConcurrencyControl
            label="Worker Pool Size"
            value={concurrencySettings.workerPoolSize}
            description="Active worker processes"
          />
          <ConcurrencyControl
            label="Backpressure Threshold"
            value={`${concurrencySettings.backpressureThreshold}%`}
            description="Slow down new requests above"
          />
        </div>
      </div>

      {/* Per-Tenant Quotas */}
      <div className="bg-white/5 border border-white/10">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Building className="w-3 h-3 text-white/40" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Per-Tenant Quotas
            </h3>
          </div>
          <select
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
            className="bg-white/5 border border-white/20 text-xs font-mono text-white px-2 py-1 focus:outline-none focus:border-white/40"
          >
            <option value="all">All Tenants</option>
            {tenantQuotas.map((t) => (
              <option key={t.tenantId} value={t.tenantId}>{t.tenantName}</option>
            ))}
          </select>
        </div>
        <div className="divide-y divide-white/5">
          {tenantQuotas
            .filter(t => selectedTenant === 'all' || t.tenantId === selectedTenant)
            .map((tenant) => (
              <div key={tenant.tenantId} className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-white font-medium">{tenant.tenantName}</span>
                    <span className={cn(
                      'text-[9px] font-mono uppercase px-1.5 py-0.5',
                      tenant.tier === 'enterprise' ? 'bg-purple-500/20 text-purple-400' :
                      tenant.tier === 'pro' ? 'bg-cyan-500/20 text-cyan-400' :
                      'bg-white/10 text-white/40'
                    )}>
                      {tenant.tier}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-[10px] font-mono text-white/40 hover:text-white"
                  >
                    EDIT LIMITS
                  </Button>
                </div>
                <div className="grid grid-cols-5 gap-3">
                  <QuotaBar
                    label="Concurrent"
                    used={tenant.quotas.concurrentRuns.used}
                    limit={tenant.quotas.concurrentRuns.limit}
                  />
                  <QuotaBar
                    label="Storage"
                    used={tenant.quotas.storage.used}
                    limit={tenant.quotas.storage.limit}
                    unit="GB"
                  />
                  <QuotaBar
                    label="API/day"
                    used={tenant.quotas.apiRequests.used}
                    limit={tenant.quotas.apiRequests.limit}
                  />
                  <QuotaBar
                    label="Projects"
                    used={tenant.quotas.projects.used}
                    limit={tenant.quotas.projects.limit}
                  />
                  <QuotaBar
                    label="Personas"
                    used={tenant.quotas.personas.used}
                    limit={tenant.quotas.personas.limit}
                  />
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Alert Rules */}
      <div className="bg-white/5 border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-3 h-3 text-yellow-400" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Quota Alert Rules
            </h3>
          </div>
          <Button size="sm" className="h-7 text-[10px]">
            ADD RULE
          </Button>
        </div>
        <div className="space-y-2">
          <AlertRule
            condition="Concurrent Runs > 80%"
            action="Notify admin via email"
            status="active"
          />
          <AlertRule
            condition="Storage > 90%"
            action="Block new uploads, notify tenant"
            status="active"
          />
          <AlertRule
            condition="API Requests > 95%"
            action="Rate limit to 1 req/sec"
            status="active"
          />
          <AlertRule
            condition="Queue Depth > 50"
            action="Enable backpressure mode"
            status="active"
          />
        </div>
      </div>
    </div>
  );
}

function ConcurrencyControl({
  label,
  value,
  description,
}: {
  label: string;
  value: number | string;
  description: string;
}) {
  return (
    <div className="p-3 bg-white/5 border border-white/10">
      <p className="text-[10px] font-mono text-white/40 uppercase">{label}</p>
      <p className="text-xl font-mono font-bold text-white mt-1">{value}</p>
      <p className="text-[9px] font-mono text-white/30 mt-1">{description}</p>
    </div>
  );
}

function QuotaBar({
  label,
  used,
  limit,
  unit = '',
}: {
  label: string;
  used: number;
  limit: number;
  unit?: string;
}) {
  const percentage = (used / limit) * 100;
  const status = percentage >= 90 ? 'error' : percentage >= 70 ? 'warning' : 'good';

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] font-mono text-white/40 uppercase">{label}</span>
        <span className={cn(
          'text-[9px] font-mono',
          status === 'error' ? 'text-red-400' :
          status === 'warning' ? 'text-yellow-400' : 'text-white/60'
        )}>
          {Math.round(percentage)}%
        </span>
      </div>
      <div className="w-full bg-white/10 h-1.5">
        <div
          className={cn(
            'h-1.5 transition-all',
            status === 'good' ? 'bg-green-500' :
            status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
          )}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <p className="text-[8px] font-mono text-white/30 mt-0.5">
        {used.toLocaleString()}/{limit.toLocaleString()} {unit}
      </p>
    </div>
  );
}

function AlertRule({
  condition,
  action,
  status,
}: {
  condition: string;
  action: string;
  status: 'active' | 'disabled';
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-white/5 border border-white/10">
      <div className="flex items-center gap-3">
        <span className={cn(
          'w-2 h-2 rounded-full',
          status === 'active' ? 'bg-green-500' : 'bg-white/30'
        )} />
        <div>
          <p className="text-xs font-mono text-white">{condition}</p>
          <p className="text-[10px] font-mono text-white/40">{action}</p>
        </div>
      </div>
      <button className="text-[9px] font-mono text-white/40 hover:text-white uppercase">
        Edit
      </button>
    </div>
  );
}

// Secrets Tab Component (P9-003)
function SecretsTab() {
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const [rotatingSecret, setRotatingSecret] = useState<string | null>(null);

  const toggleShowValue = (name: string) => {
    setShowValues((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  // Mock secret data
  const secrets = [
    {
      name: 'SECRET_KEY',
      type: 'JWT Signing Key',
      lastRotated: '2025-11-15',
      daysUntilRotation: 45,
      needsRotation: false,
      version: 3,
      masked: 'av_s3cr3t****************************',
    },
    {
      name: 'DATABASE_PASSWORD',
      type: 'Database Credential',
      lastRotated: '2025-10-01',
      daysUntilRotation: 0,
      needsRotation: true,
      version: 2,
      masked: 'db_pwd_*****************************',
    },
    {
      name: 'OPENROUTER_API_KEY',
      type: 'API Key',
      lastRotated: '2025-12-20',
      daysUntilRotation: 355,
      needsRotation: false,
      version: 1,
      masked: 'sk-or-v1-***************************',
    },
    {
      name: 'STORAGE_ACCESS_KEY',
      type: 'Storage Credential',
      lastRotated: '2025-09-15',
      daysUntilRotation: 15,
      needsRotation: false,
      version: 2,
      masked: 'AKIA****************************',
    },
    {
      name: 'STORAGE_SECRET_KEY',
      type: 'Storage Credential',
      lastRotated: '2025-09-15',
      daysUntilRotation: 15,
      needsRotation: false,
      version: 2,
      masked: '****************************************',
    },
  ];

  const rotationSchedule = [
    { name: 'DATABASE_PASSWORD', daysOverdue: 0, priority: 'critical' },
    { name: 'STORAGE_ACCESS_KEY', daysUntil: 15, priority: 'warning' },
    { name: 'SECRET_KEY', daysUntil: 45, priority: 'normal' },
    { name: 'OPENROUTER_API_KEY', daysUntil: 355, priority: 'low' },
  ];

  const handleRotate = async (secretName: string) => {
    setRotatingSecret(secretName);
    // Simulate rotation
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setRotatingSecret(null);
  };

  return (
    <div className="space-y-6">
      {/* Health Status */}
      <div className="bg-white/5 border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-3 h-3 text-cyan-400" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Secret Health Status
            </h3>
          </div>
          <div className="flex items-center gap-2">
            {secrets.some((s) => s.needsRotation) ? (
              <span className="text-[9px] font-mono text-red-400 bg-red-400/10 px-2 py-0.5">
                ACTION REQUIRED
              </span>
            ) : (
              <span className="text-[9px] font-mono text-green-400 bg-green-400/10 px-2 py-0.5">
                ALL SECRETS HEALTHY
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-white/5 border border-white/10">
            <p className="text-[10px] font-mono text-white/40 uppercase">Total Secrets</p>
            <p className="text-2xl font-mono font-bold text-white mt-1">{secrets.length}</p>
            <p className="text-[9px] font-mono text-white/30 mt-1">Managed secrets</p>
          </div>
          <div className="p-4 bg-white/5 border border-red-500/30">
            <p className="text-[10px] font-mono text-white/40 uppercase">Need Rotation</p>
            <p className="text-2xl font-mono font-bold text-red-400 mt-1">
              {secrets.filter((s) => s.needsRotation).length}
            </p>
            <p className="text-[9px] font-mono text-red-400/60 mt-1">Overdue secrets</p>
          </div>
          <div className="p-4 bg-white/5 border border-yellow-500/30">
            <p className="text-[10px] font-mono text-white/40 uppercase">Rotate Soon</p>
            <p className="text-2xl font-mono font-bold text-yellow-400 mt-1">
              {secrets.filter((s) => s.daysUntilRotation <= 30 && !s.needsRotation).length}
            </p>
            <p className="text-[9px] font-mono text-yellow-400/60 mt-1">Within 30 days</p>
          </div>
          <div className="p-4 bg-white/5 border border-green-500/30">
            <p className="text-[10px] font-mono text-white/40 uppercase">Healthy</p>
            <p className="text-2xl font-mono font-bold text-green-400 mt-1">
              {secrets.filter((s) => s.daysUntilRotation > 30).length}
            </p>
            <p className="text-[9px] font-mono text-green-400/60 mt-1">No action needed</p>
          </div>
        </div>
      </div>

      {/* Rotation Schedule */}
      <div className="bg-white/5 border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-3 h-3 text-white/40" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Rotation Schedule
            </h3>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] font-mono border-white/20 text-white/60 hover:bg-white/5"
          >
            CONFIGURE POLICIES
          </Button>
        </div>
        <div className="space-y-2">
          {rotationSchedule.map((item) => (
            <div
              key={item.name}
              className={cn(
                'flex items-center justify-between p-3 border',
                item.priority === 'critical'
                  ? 'bg-red-500/10 border-red-500/30'
                  : item.priority === 'warning'
                  ? 'bg-yellow-500/10 border-yellow-500/30'
                  : 'bg-white/5 border-white/10'
              )}
            >
              <div className="flex items-center gap-3">
                <RotateCcw
                  className={cn(
                    'w-4 h-4',
                    item.priority === 'critical'
                      ? 'text-red-400'
                      : item.priority === 'warning'
                      ? 'text-yellow-400'
                      : 'text-white/40'
                  )}
                />
                <div>
                  <p className="text-sm font-mono text-white">{item.name}</p>
                  <p
                    className={cn(
                      'text-[10px] font-mono',
                      item.priority === 'critical'
                        ? 'text-red-400'
                        : item.priority === 'warning'
                        ? 'text-yellow-400'
                        : 'text-white/40'
                    )}
                  >
                    {item.daysOverdue !== undefined
                      ? `${item.daysOverdue === 0 ? 'Due now' : `${item.daysOverdue} days overdue`}`
                      : `${item.daysUntil} days until rotation`}
                  </p>
                </div>
              </div>
              {item.priority === 'critical' && (
                <Button
                  size="sm"
                  className="h-7 text-[10px] bg-red-500 hover:bg-red-600 text-white"
                  onClick={() => handleRotate(item.name)}
                  disabled={rotatingSecret === item.name}
                >
                  {rotatingSecret === item.name ? (
                    <>
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      ROTATING...
                    </>
                  ) : (
                    'ROTATE NOW'
                  )}
                </Button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Secret List */}
      <div className="bg-white/5 border border-white/10">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Key className="w-3 h-3 text-white/40" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Managed Secrets
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-[10px] font-mono border-white/20 text-white/60 hover:bg-white/5"
            >
              ADD SECRET
            </Button>
          </div>
        </div>
        <div className="divide-y divide-white/5">
          {secrets.map((secret) => (
            <div key={secret.name} className="p-4 hover:bg-white/5 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {secret.needsRotation ? (
                      <Unlock className="w-3 h-3 text-red-400" />
                    ) : (
                      <Lock className="w-3 h-3 text-green-400" />
                    )}
                    <span className="text-sm font-mono text-white font-medium">
                      {secret.name}
                    </span>
                    <span className="text-[9px] font-mono text-white/40 bg-white/10 px-1.5 py-0.5">
                      v{secret.version}
                    </span>
                    {secret.needsRotation && (
                      <span className="text-[9px] font-mono text-red-400 bg-red-400/10 px-1.5 py-0.5">
                        ROTATION REQUIRED
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] font-mono text-white/40 mt-1">{secret.type}</p>
                  <div className="flex items-center gap-4 mt-2">
                    <div className="flex items-center gap-1.5 bg-white/5 px-2 py-1">
                      <code className="text-[10px] font-mono text-white/60">
                        {showValues[secret.name] ? secret.masked : '••••••••••••••••••••••••'}
                      </code>
                      <button
                        onClick={() => toggleShowValue(secret.name)}
                        className="text-white/40 hover:text-white"
                      >
                        {showValues[secret.name] ? (
                          <EyeOff className="w-3 h-3" />
                        ) : (
                          <Eye className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <div className="text-[10px] font-mono text-white/40">
                    Last rotated: {secret.lastRotated}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-[10px] font-mono text-white/40 hover:text-white"
                      onClick={() => handleRotate(secret.name)}
                      disabled={rotatingSecret === secret.name}
                    >
                      {rotatingSecret === secret.name ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <>
                          <RotateCcw className="w-3 h-3 mr-1" />
                          ROTATE
                        </>
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-[10px] font-mono text-white/40 hover:text-white"
                    >
                      <Settings className="w-3 h-3 mr-1" />
                      CONFIG
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Documentation */}
      <div className="bg-white/5 border border-white/10 p-6">
        <div className="flex items-start gap-3">
          <Info className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-mono text-white font-medium mb-2">
              Secret Management Best Practices
            </h3>
            <ul className="space-y-1 text-[11px] font-mono text-white/50">
              <li>
                • <span className="text-cyan-400/80">JWT Keys:</span> Rotate every 90 days minimum
              </li>
              <li>
                • <span className="text-cyan-400/80">Database Passwords:</span> Rotate every 180
                days
              </li>
              <li>
                • <span className="text-cyan-400/80">API Keys:</span> Review annually, rotate if
                compromised
              </li>
              <li>
                • <span className="text-cyan-400/80">Storage Keys:</span> Rotate every 180 days or
                on personnel change
              </li>
              <li>
                • All secret access is audited and logged for compliance
              </li>
              <li>
                • Secrets are never exposed in logs or error messages
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

// Audit Tab Component
function AuditTab() {
  const auditLogs = [
    { id: '1', action: 'project.created', user: 'john@acme.com', tenant: 'acme', timestamp: '2026-01-08 14:23:45', status: 'success' },
    { id: '2', action: 'run.started', user: 'jane@acme.com', tenant: 'acme', timestamp: '2026-01-08 14:22:12', status: 'success' },
    { id: '3', action: 'user.login', user: 'admin@global-research.com', tenant: 'global-research', timestamp: '2026-01-08 14:20:00', status: 'success' },
    { id: '4', action: 'run.failed', user: 'test@beta-labs.com', tenant: 'beta-labs', timestamp: '2026-01-08 14:18:30', status: 'error' },
    { id: '5', action: 'quota.exceeded', user: 'system', tenant: 'techstart', timestamp: '2026-01-08 14:15:00', status: 'warning' },
  ];

  return (
    <div className="bg-white/5 border border-white/10">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <FileText className="w-3 h-3 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Audit Log
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] font-mono border-white/20 text-white/60 hover:bg-white/5"
          >
            <Filter className="w-3 h-3 mr-1" />
            FILTER
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] font-mono border-white/20 text-white/60 hover:bg-white/5"
          >
            EXPORT
          </Button>
        </div>
      </div>
      <div className="divide-y divide-white/5">
        {auditLogs.map((log) => (
          <div key={log.id} className="p-4 hover:bg-white/5 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {log.status === 'success' && <CheckCircle className="w-3 h-3 text-green-500" />}
                {log.status === 'error' && <AlertTriangle className="w-3 h-3 text-red-500" />}
                {log.status === 'warning' && <AlertTriangle className="w-3 h-3 text-yellow-500" />}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-white">{log.action}</span>
                    <span className="text-[10px] font-mono text-white/40">@{log.tenant}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5 text-[10px] font-mono text-white/40">
                    <span>{log.user}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-3 h-3 text-white/30" />
                <span className="text-[10px] font-mono text-white/30">{log.timestamp}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Policies Tab Component
function PoliciesTab() {
  const policies = [
    { name: 'Sensitive Domain Flag', description: 'Require additional confirmation for sensitive domains', enabled: true },
    { name: 'Data Retention', description: 'Auto-delete telemetry older than 90 days', enabled: true },
    { name: 'Public Sharing', description: 'Allow public sharing of replay links', enabled: false },
    { name: 'API Rate Limiting', description: 'Enforce rate limits on API requests', enabled: true },
    { name: 'Audit Logging', description: 'Log all user actions for audit', enabled: true },
  ];

  return (
    <div className="bg-white/5 border border-white/10">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-3 h-3 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Policy Flags
          </span>
        </div>
      </div>
      <div className="divide-y divide-white/5">
        {policies.map((policy) => (
          <div key={policy.name} className="p-4 hover:bg-white/5 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h4 className="text-sm font-mono text-white">{policy.name}</h4>
                <p className="text-[10px] font-mono text-white/40 mt-0.5">{policy.description}</p>
              </div>
              <button
                className={cn(
                  'w-10 h-5 rounded-full transition-colors relative',
                  policy.enabled ? 'bg-green-500' : 'bg-white/20'
                )}
              >
                <span
                  className={cn(
                    'absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform',
                    policy.enabled ? 'left-5' : 'left-0.5'
                  )}
                />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Models Tab Component (GAPS.md GAP-P0-001)
function ModelsTab() {
  const [selectedProfile, setSelectedProfile] = useState<LLMProfile | null>(null);
  const [testingProfile, setTestingProfile] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; response?: string; error?: string } | null>(null);

  const { data: profilesData, isLoading: profilesLoading, refetch: refetchProfiles } = useLLMProfiles();
  const { data: costReport, isLoading: costLoading } = useLLMCostReport();
  const { data: availableModels } = useAvailableLLMModels();
  const updateProfile = useUpdateLLMProfile();
  const deleteProfile = useDeleteLLMProfile();
  const testProfile = useTestLLMProfile();

  const handleToggleActive = async (profile: LLMProfile) => {
    await updateProfile.mutateAsync({
      profileId: profile.id,
      data: { is_active: !profile.is_active },
    });
    refetchProfiles();
  };

  const handleDeleteProfile = async (profileId: string) => {
    if (confirm('Are you sure you want to delete this profile?')) {
      await deleteProfile.mutateAsync(profileId);
      refetchProfiles();
    }
  };

  const handleTestProfile = async (profile: LLMProfile) => {
    setTestingProfile(profile.id);
    setTestResult(null);
    try {
      const result = await testProfile.mutateAsync({
        profileId: profile.id,
        testPrompt: 'What is 2 + 2? Reply with just the number.',
      });
      setTestResult({
        success: result.success,
        response: result.response || undefined,
        error: result.error || undefined,
      });
    } catch (err) {
      setTestResult({
        success: false,
        error: err instanceof Error ? err.message : 'Test failed',
      });
    } finally {
      setTestingProfile(null);
    }
  };

  const profiles = profilesData?.profiles || [];

  return (
    <div className="space-y-6">
      {/* Cost Overview */}
      <div className="bg-white/5 border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <DollarSign className="w-3 h-3 text-cyan-400" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              LLM Usage & Costs
            </h3>
          </div>
          <span className="text-[9px] font-mono text-cyan-400/60 bg-cyan-400/10 px-2 py-0.5">
            THIS PERIOD
          </span>
        </div>
        {costLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-white/40" />
          </div>
        ) : costReport ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <CostStatCard
              icon={Zap}
              label="Total Calls"
              value={costReport.summary.total_calls.toLocaleString()}
              subtext="API requests"
            />
            <CostStatCard
              icon={DollarSign}
              label="Total Cost"
              value={`$${costReport.summary.total_cost_usd.toFixed(4)}`}
              subtext="This period"
              status={costReport.summary.total_cost_usd > 10 ? 'warning' : 'good'}
            />
            <CostStatCard
              icon={BarChart3}
              label="Tokens Used"
              value={(costReport.summary.total_tokens / 1000).toFixed(1) + 'K'}
              subtext={`${(costReport.summary.total_input_tokens / 1000).toFixed(1)}K in / ${(costReport.summary.total_output_tokens / 1000).toFixed(1)}K out`}
            />
            <CostStatCard
              icon={TrendingUp}
              label="Cache Hit Rate"
              value={`${(costReport.summary.cache_hit_rate * 100).toFixed(1)}%`}
              subtext={`${costReport.summary.cache_hits} cache hits`}
              status={costReport.summary.cache_hit_rate > 0.5 ? 'good' : 'warning'}
            />
          </div>
        ) : (
          <p className="text-sm font-mono text-white/40">No cost data available</p>
        )}

        {/* Cost by Profile */}
        {costReport && costReport.by_profile.length > 0 && (
          <div className="mt-6">
            <h4 className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-3">
              Cost by Profile
            </h4>
            <div className="space-y-2">
              {costReport.by_profile.map((item) => {
                const percentage = costReport.summary.total_cost_usd > 0
                  ? (item.total_cost_usd / costReport.summary.total_cost_usd) * 100
                  : 0;
                return (
                  <div key={item.profile_key} className="flex items-center gap-4">
                    <div className="w-40 text-xs font-mono text-white/60 truncate">
                      {item.profile_key}
                    </div>
                    <div className="flex-1 bg-white/10 h-2">
                      <div
                        className="h-2 bg-cyan-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <div className="w-24 text-right text-[10px] font-mono text-white/40">
                      ${item.total_cost_usd.toFixed(4)}
                    </div>
                    <div className="w-16 text-right text-[10px] font-mono text-white/30">
                      {item.call_count} calls
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Profile List */}
      <div className="bg-white/5 border border-white/10">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Cpu className="w-3 h-3 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              LLM Profiles ({profiles.length})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchProfiles()}
              className="h-7 text-[10px] font-mono border-white/20 text-white/60 hover:bg-white/5"
            >
              <RefreshCw className="w-3 h-3 mr-1" />
              REFRESH
            </Button>
          </div>
        </div>

        {profilesLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-white/40" />
          </div>
        ) : profiles.length === 0 ? (
          <div className="p-8 text-center">
            <Cpu className="w-8 h-8 mx-auto text-white/20 mb-2" />
            <p className="text-sm font-mono text-white/40">No LLM profiles configured</p>
            <p className="text-xs font-mono text-white/30 mt-1">
              Profiles are seeded from the API on first run
            </p>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {profiles.map((profile) => (
              <div
                key={profile.id}
                className={cn(
                  'p-4 hover:bg-white/5 transition-colors',
                  selectedProfile?.id === profile.id && 'bg-white/5'
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-mono text-white font-medium">
                        {profile.label}
                      </h4>
                      <span className={cn(
                        'text-[9px] font-mono uppercase px-1.5 py-0.5',
                        profile.is_active
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-white/10 text-white/40'
                      )}>
                        {profile.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                      {profile.is_default && (
                        <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400">
                          DEFAULT
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] font-mono text-white/40 mt-1">
                      {profile.profile_key}
                    </p>
                    <div className="flex items-center gap-4 mt-2 text-[10px] font-mono text-white/30">
                      <span className="flex items-center gap-1">
                        <Cpu className="w-3 h-3" />
                        {profile.model}
                      </span>
                      <span>temp: {profile.temperature}</span>
                      <span>max_tokens: {profile.max_tokens}</span>
                      {profile.cache_enabled && (
                        <span className="text-cyan-400/60">cache: on</span>
                      )}
                    </div>
                    {profile.description && (
                      <p className="text-[10px] font-mono text-white/30 mt-2 line-clamp-1">
                        {profile.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTestProfile(profile)}
                      disabled={testingProfile === profile.id}
                      className="h-7 text-[10px] font-mono text-white/40 hover:text-white"
                    >
                      {testingProfile === profile.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <>
                          <Play className="w-3 h-3 mr-1" />
                          TEST
                        </>
                      )}
                    </Button>
                    <button
                      onClick={() => handleToggleActive(profile)}
                      className={cn(
                        'w-10 h-5 rounded-full transition-colors relative',
                        profile.is_active ? 'bg-green-500' : 'bg-white/20'
                      )}
                    >
                      <span
                        className={cn(
                          'absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform',
                          profile.is_active ? 'left-5' : 'left-0.5'
                        )}
                      />
                    </button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteProfile(profile.id)}
                      className="h-7 text-[10px] font-mono text-red-400/60 hover:text-red-400"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>

                {/* Test Result */}
                {testResult && testingProfile === null && selectedProfile?.id === profile.id && (
                  <div className={cn(
                    'mt-3 p-3 border',
                    testResult.success
                      ? 'bg-green-500/10 border-green-500/30'
                      : 'bg-red-500/10 border-red-500/30'
                  )}>
                    <div className="flex items-center gap-2 mb-1">
                      {testResult.success ? (
                        <CheckCircle className="w-3 h-3 text-green-400" />
                      ) : (
                        <AlertTriangle className="w-3 h-3 text-red-400" />
                      )}
                      <span className={cn(
                        'text-[10px] font-mono uppercase',
                        testResult.success ? 'text-green-400' : 'text-red-400'
                      )}>
                        {testResult.success ? 'Test Passed' : 'Test Failed'}
                      </span>
                    </div>
                    <p className="text-[10px] font-mono text-white/60">
                      {testResult.response || testResult.error}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Available Models Reference */}
      {availableModels && availableModels.models.length > 0 && (
        <div className="bg-white/5 border border-white/10 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-3 h-3 text-cyan-400" />
            <h3 className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Available Models
            </h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {availableModels.models.slice(0, 8).map((model) => (
              <div
                key={model.model}
                className="p-3 bg-white/5 border border-white/10"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-white">{model.model}</span>
                  <span className="text-[9px] font-mono text-white/40 bg-white/10 px-1.5 py-0.5">
                    {model.provider}
                  </span>
                </div>
                <p className="text-[10px] font-mono text-white/30 mt-1 line-clamp-1">
                  {model.description}
                </p>
                <div className="flex items-center gap-3 mt-2 text-[9px] font-mono text-white/40">
                  <span>${model.cost_per_1k_input_tokens}/1K in</span>
                  <span>${model.cost_per_1k_output_tokens}/1K out</span>
                  <span>{(model.max_context_length / 1000).toFixed(0)}K ctx</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CostStatCard({
  icon: Icon,
  label,
  value,
  subtext,
  status,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  subtext: string;
  status?: 'good' | 'warning' | 'error';
}) {
  return (
    <div className={cn(
      'p-4 bg-white/5 border',
      status === 'good' ? 'border-green-500/30' :
      status === 'warning' ? 'border-yellow-500/30' :
      status === 'error' ? 'border-red-500/30' : 'border-white/10'
    )}>
      <div className="flex items-start justify-between mb-2">
        <Icon className={cn(
          'w-4 h-4',
          status === 'good' ? 'text-green-400' :
          status === 'warning' ? 'text-yellow-400' :
          status === 'error' ? 'text-red-400' : 'text-white/40'
        )} />
      </div>
      <p className="text-[10px] font-mono text-white/40 uppercase">{label}</p>
      <p className={cn(
        'text-xl font-mono font-bold mt-1',
        status === 'good' ? 'text-green-400' :
        status === 'warning' ? 'text-yellow-400' :
        status === 'error' ? 'text-red-400' : 'text-white'
      )}>{value}</p>
      <p className="text-[9px] font-mono text-white/30 mt-1">{subtext}</p>
    </div>
  );
}
