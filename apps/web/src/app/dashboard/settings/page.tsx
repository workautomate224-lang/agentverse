'use client';

import { useState } from 'react';
import { useSession, signOut } from 'next-auth/react';
import { Button } from '@/components/ui/button';
import {
  Settings,
  Key,
  Bell,
  CreditCard,
  Shield,
  Loader2,
  Save,
  Eye,
  EyeOff,
  Terminal,
  Cpu,
  Database,
  User,
  Mail,
  Building,
  Lock,
  LogOut,
  AlertTriangle,
  Check,
  X,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SettingsPage() {
  const { data: session } = useSession();
  const [activeTab, setActiveTab] = useState('account');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  // API Keys state
  const [showApiKey, setShowApiKey] = useState(false);

  // Account form state
  const [accountForm, setAccountForm] = useState({
    fullName: session?.user?.name || '',
    email: session?.user?.email || '',
    company: '',
  });

  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Delete account state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');

  const tabs = [
    { id: 'account', label: 'ACCOUNT', icon: User },
    { id: 'security', label: 'SECURITY', icon: Shield },
    { id: 'system', label: 'SYSTEM', icon: Cpu },
    { id: 'api', label: 'API KEYS', icon: Key },
    { id: 'notifications', label: 'ALERTS', icon: Bell },
    { id: 'billing', label: 'BILLING', icon: CreditCard },
  ];

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await signOut({ callbackUrl: '/' });
    } catch {
      setIsLoggingOut(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Settings className="w-4 h-4 text-white/60" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Configuration</span>
        </div>
        <h1 className="text-xl font-mono font-bold text-white">Settings</h1>
        <p className="text-sm font-mono text-white/50 mt-1">
          System configuration and preferences
        </p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center gap-2 px-3 py-2 text-xs font-mono transition-colors',
                    activeTab === tab.id
                      ? 'bg-white/10 text-white border-l-2 border-white'
                      : 'text-white/40 hover:bg-white/5 hover:text-white/60 border-l-2 border-transparent'
                  )}
                >
                  <Icon className="w-3 h-3" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white/5 border border-white/10 p-6">
          {activeTab === 'account' && (
            <div>
              <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
                <User className="w-4 h-4" />
                ACCOUNT SETTINGS
              </h2>

              <div className="space-y-6 max-w-lg">
                {/* Profile Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-4 mb-6">
                    {/* Avatar */}
                    <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center flex-shrink-0">
                      <span className="text-xl font-mono font-bold text-black">
                        {session?.user?.name
                          ? session.user.name
                              .split(' ')
                              .map((n) => n[0])
                              .join('')
                              .toUpperCase()
                              .slice(0, 2)
                          : session?.user?.email?.[0]?.toUpperCase() || 'AG'}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-mono text-white">{session?.user?.name || 'Agent'}</p>
                      <p className="text-xs font-mono text-white/40">{session?.user?.email || 'agent@agentverse.io'}</p>
                      <div className="text-[10px] font-mono text-green-400 mt-1 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full inline-block" />
                        VERIFIED
                      </div>
                    </div>
                  </div>

                  {/* Full Name */}
                  <div>
                    <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                      Full Name
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                      <input
                        type="text"
                        value={accountForm.fullName}
                        onChange={(e) => setAccountForm({ ...accountForm, fullName: e.target.value })}
                        placeholder="Enter your name"
                        className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                      />
                    </div>
                  </div>

                  {/* Email */}
                  <div>
                    <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                      <input
                        type="email"
                        value={accountForm.email}
                        onChange={(e) => setAccountForm({ ...accountForm, email: e.target.value })}
                        placeholder="agent@agentverse.io"
                        className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                      />
                    </div>
                  </div>

                  {/* Company */}
                  <div>
                    <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                      Organization
                    </label>
                    <div className="relative">
                      <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                      <input
                        type="text"
                        value={accountForm.company}
                        onChange={(e) => setAccountForm({ ...accountForm, company: e.target.value })}
                        placeholder="Your company (optional)"
                        className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                      />
                    </div>
                  </div>

                  <Button
                    onClick={handleSave}
                    disabled={isSaving}
                    size="sm"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                        SAVING...
                      </>
                    ) : (
                      <>
                        <Save className="w-3 h-3 mr-2" />
                        UPDATE PROFILE
                      </>
                    )}
                  </Button>
                </div>

                {/* Session Section */}
                <div className="pt-6 border-t border-white/10">
                  <h3 className="text-xs font-mono text-white/60 uppercase mb-4">Active Sessions</h3>

                  <div className="bg-white/5 border border-white/10 p-4 mb-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-green-500/20 flex items-center justify-center">
                          <Terminal className="w-4 h-4 text-green-400" />
                        </div>
                        <div>
                          <p className="text-xs font-mono text-white">Current Session</p>
                          <p className="text-[10px] font-mono text-white/40">This device • Active now</p>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 text-[10px] font-mono bg-green-500/20 text-green-400 uppercase">
                        CURRENT
                      </span>
                    </div>
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLogout}
                    disabled={isLoggingOut}
                    className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                  >
                    {isLoggingOut ? (
                      <>
                        <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                        DISCONNECTING...
                      </>
                    ) : (
                      <>
                        <LogOut className="w-3 h-3 mr-2" />
                        SIGN OUT OF ALL SESSIONS
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div>
              <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
                <Shield className="w-4 h-4" />
                SECURITY SETTINGS
              </h2>

              <div className="space-y-6 max-w-lg">
                {/* Password Change */}
                <div>
                  <h3 className="text-xs font-mono text-white/60 uppercase mb-4 flex items-center gap-2">
                    <Lock className="w-3 h-3" />
                    Change Password
                  </h3>

                  <div className="space-y-4">
                    {/* Current Password */}
                    <div>
                      <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                        Current Password
                      </label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                        <input
                          type={showCurrentPassword ? 'text' : 'password'}
                          value={passwordForm.currentPassword}
                          onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                          placeholder="Enter current password"
                          className="w-full pl-10 pr-10 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                        />
                        <button
                          type="button"
                          onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
                        >
                          {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {/* New Password */}
                    <div>
                      <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                        New Password
                      </label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                        <input
                          type={showNewPassword ? 'text' : 'password'}
                          value={passwordForm.newPassword}
                          onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                          placeholder="Enter new password"
                          className="w-full pl-10 pr-10 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                        />
                        <button
                          type="button"
                          onClick={() => setShowNewPassword(!showNewPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
                        >
                          {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {/* Confirm New Password */}
                    <div>
                      <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                        Confirm New Password
                      </label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                        <input
                          type="password"
                          value={passwordForm.confirmPassword}
                          onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                          placeholder="Confirm new password"
                          className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                        />
                      </div>
                      {passwordForm.confirmPassword && passwordForm.newPassword !== passwordForm.confirmPassword && (
                        <div className="flex items-center gap-1 text-[10px] font-mono text-red-400 mt-1">
                          <X className="w-3 h-3" />
                          Passwords do not match
                        </div>
                      )}
                      {passwordForm.confirmPassword && passwordForm.newPassword === passwordForm.confirmPassword && (
                        <div className="flex items-center gap-1 text-[10px] font-mono text-green-400 mt-1">
                          <Check className="w-3 h-3" />
                          Passwords match
                        </div>
                      )}
                    </div>

                    <Button
                      onClick={handleSave}
                      disabled={isSaving || !passwordForm.currentPassword || !passwordForm.newPassword || passwordForm.newPassword !== passwordForm.confirmPassword}
                      size="sm"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                          UPDATING...
                        </>
                      ) : (
                        <>
                          <Lock className="w-3 h-3 mr-2" />
                          UPDATE PASSWORD
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Two-Factor Auth */}
                <div className="pt-6 border-t border-white/10">
                  <h3 className="text-xs font-mono text-white/60 uppercase mb-4">Two-Factor Authentication</h3>

                  <div className="flex items-center justify-between p-4 bg-white/5 border border-white/10">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-yellow-500/20 flex items-center justify-center">
                        <Shield className="w-4 h-4 text-yellow-400" />
                      </div>
                      <div>
                        <p className="text-xs font-mono text-white">2FA Status</p>
                        <p className="text-[10px] font-mono text-yellow-400">Not enabled</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" className="border-white/20 text-white/60 hover:bg-white/5">
                      ENABLE
                    </Button>
                  </div>
                </div>

                {/* Danger Zone */}
                <div className="pt-6 border-t border-red-500/30">
                  <h3 className="text-xs font-mono text-red-400 uppercase mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-3 h-3" />
                    Danger Zone
                  </h3>

                  <div className="bg-red-500/5 border border-red-500/20 p-4">
                    <p className="text-xs font-mono text-white/60 mb-4">
                      Permanently delete your account and all associated data. This action cannot be undone.
                    </p>

                    {!showDeleteConfirm ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowDeleteConfirm(true)}
                        className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                      >
                        <Trash2 className="w-3 h-3 mr-2" />
                        DELETE ACCOUNT
                      </Button>
                    ) : (
                      <div className="space-y-3">
                        <p className="text-[10px] font-mono text-red-400">
                          Type &quot;DELETE&quot; to confirm:
                        </p>
                        <input
                          type="text"
                          value={deleteConfirmText}
                          onChange={(e) => setDeleteConfirmText(e.target.value)}
                          placeholder="DELETE"
                          className="w-full px-3 py-2 bg-black border border-red-500/30 text-xs font-mono text-red-400 focus:outline-none focus:border-red-500 placeholder:text-red-400/30"
                        />
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setShowDeleteConfirm(false);
                              setDeleteConfirmText('');
                            }}
                            className="border-white/20 text-white/60 hover:bg-white/5"
                          >
                            CANCEL
                          </Button>
                          <Button
                            size="sm"
                            disabled={deleteConfirmText !== 'DELETE'}
                            className="bg-red-500 hover:bg-red-600 text-white disabled:bg-red-500/30 disabled:text-white/30"
                          >
                            <Trash2 className="w-3 h-3 mr-2" />
                            CONFIRM DELETE
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'system' && (
            <div>
              <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
                <Cpu className="w-4 h-4" />
                SYSTEM CONFIGURATION
              </h2>

              <div className="space-y-6 max-w-md">
                {/* Default Model */}
                <div>
                  <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                    Default AI Model
                  </label>
                  <select className="w-full px-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30">
                    <option value="gpt-4o-mini">GPT-4o Mini (Recommended)</option>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                    <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                  </select>
                </div>

                {/* Default Agent Count */}
                <div>
                  <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                    Default Agent Count
                  </label>
                  <input
                    type="number"
                    defaultValue={100}
                    min={10}
                    max={1000}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
                  />
                </div>

                {/* Database Status */}
                <div className="pt-4 border-t border-white/10">
                  <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                    Database Connection
                  </label>
                  <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-xs font-mono text-green-400">CONNECTED</span>
                    <span className="text-[10px] font-mono text-white/30 ml-auto">PostgreSQL</span>
                  </div>
                </div>

                {/* API Status */}
                <div>
                  <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                    API Server
                  </label>
                  <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-xs font-mono text-green-400">ONLINE</span>
                    <span className="text-[10px] font-mono text-white/30 ml-auto">localhost:8000</span>
                  </div>
                </div>

                <Button
                  onClick={handleSave}
                  disabled={isSaving}
                  size="sm"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                      SAVING...
                    </>
                  ) : (
                    <>
                      <Save className="w-3 h-3 mr-2" />
                      SAVE CHANGES
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {activeTab === 'api' && (
            <div>
              <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
                <Key className="w-4 h-4" />
                API KEYS
              </h2>

              <div className="max-w-lg">
                <div className="bg-yellow-500/10 border border-yellow-500/30 p-3 mb-6">
                  <p className="text-xs font-mono text-yellow-400">
                    Keep your API keys secure. Never share them publicly.
                  </p>
                </div>

                {/* OpenAI Key */}
                <div className="bg-white/5 border border-white/10 p-4 mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-white/60">OpenAI API Key</span>
                    <button
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="text-white/40 hover:text-white/60"
                    >
                      {showApiKey ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      defaultValue="sk-••••••••••••••••••••••••••••••••"
                      className="flex-1 px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white focus:outline-none focus:border-white/30"
                    />
                    <Button
                      variant="outline"
                      className="font-mono text-[10px] h-8 border-white/20 text-white/60 hover:bg-white/5"
                    >
                      UPDATE
                    </Button>
                  </div>
                </div>

                {/* Production Key */}
                <div className="bg-white/5 border border-white/10 p-4 mb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-mono text-white/60">Production Key</p>
                      <p className="text-[10px] font-mono text-white/30 mt-1">av_live_••••••••••••••••</p>
                    </div>
                    <Button
                      variant="outline"
                      className="font-mono text-[10px] h-7 border-white/20 text-white/60 hover:bg-white/5"
                    >
                      REGENERATE
                    </Button>
                  </div>
                </div>

                {/* Test Key */}
                <div className="bg-white/5 border border-white/10 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-mono text-white/60">Test Key</p>
                      <p className="text-[10px] font-mono text-white/30 mt-1">av_test_••••••••••••••••</p>
                    </div>
                    <Button
                      variant="outline"
                      className="font-mono text-[10px] h-7 border-white/20 text-white/60 hover:bg-white/5"
                    >
                      REGENERATE
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div>
              <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
                <Bell className="w-4 h-4" />
                ALERT PREFERENCES
              </h2>

              <div className="space-y-3 max-w-md">
                <div className="flex items-center justify-between p-4 bg-white/5 border border-white/10">
                  <div>
                    <p className="text-xs font-mono text-white">Simulation Completed</p>
                    <p className="text-[10px] font-mono text-white/40">Alert when simulations finish</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="sr-only peer" />
                    <div className="w-9 h-5 bg-white/10 peer-checked:bg-green-500 rounded-full peer after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-4"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-white/5 border border-white/10">
                  <div>
                    <p className="text-xs font-mono text-white">Error Alerts</p>
                    <p className="text-[10px] font-mono text-white/40">Alert on simulation failures</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="sr-only peer" />
                    <div className="w-9 h-5 bg-white/10 peer-checked:bg-green-500 rounded-full peer after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-4"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 bg-white/5 border border-white/10">
                  <div>
                    <p className="text-xs font-mono text-white">Usage Reports</p>
                    <p className="text-[10px] font-mono text-white/40">Weekly usage summaries</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" />
                    <div className="w-9 h-5 bg-white/10 peer-checked:bg-green-500 rounded-full peer after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-4"></div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'billing' && (
            <div>
              <h2 className="text-sm font-mono font-bold text-white mb-6 flex items-center gap-2">
                <CreditCard className="w-4 h-4" />
                BILLING & USAGE
              </h2>

              <div className="max-w-lg">
                {/* Current Plan */}
                <div className="bg-white/5 border border-white/20 p-6 mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-[10px] font-mono text-white/40 uppercase">Current Plan</p>
                      <h3 className="text-xl font-mono font-bold text-white mt-1">DEVELOPER</h3>
                    </div>
                    <span className="px-2 py-1 text-[10px] font-mono bg-green-500/20 text-green-400 uppercase">
                      ACTIVE
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-white/40">
                    <span>$0.00/month</span>
                    <span>•</span>
                    <span>Unlimited simulations</span>
                  </div>
                </div>

                {/* Usage Stats */}
                <div className="grid grid-cols-2 gap-3 mb-6">
                  <div className="bg-white/5 border border-white/10 p-4">
                    <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Simulations</p>
                    <p className="text-xl font-mono font-bold text-white">4</p>
                    <p className="text-[10px] font-mono text-white/30">This month</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 p-4">
                    <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Agents</p>
                    <p className="text-xl font-mono font-bold text-white">350</p>
                    <p className="text-[10px] font-mono text-white/30">Total simulated</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 p-4">
                    <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Tokens</p>
                    <p className="text-xl font-mono font-bold text-white">1.2M</p>
                    <p className="text-[10px] font-mono text-white/30">Total used</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 p-4">
                    <p className="text-[10px] font-mono text-white/40 uppercase mb-1">Cost</p>
                    <p className="text-xl font-mono font-bold text-white">$12.50</p>
                    <p className="text-[10px] font-mono text-white/30">API usage</p>
                  </div>
                </div>

                <Button size="sm">
                  <CreditCard className="w-3 h-3 mr-2" />
                  UPGRADE PLAN
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>SETTINGS MODULE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
