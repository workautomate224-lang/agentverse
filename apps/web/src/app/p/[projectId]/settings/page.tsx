'use client';

/**
 * Project Settings Page (Placeholder)
 * Configure project-level settings
 */

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Settings,
  ArrowLeft,
  Terminal,
  Save,
  Trash2,
  Archive,
  Copy,
  AlertTriangle,
  Eye,
  EyeOff,
  Tag,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ProjectSettingsPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href={`/p/${projectId}/overview`}>
          <Button variant="ghost" size="sm" className="mb-3 text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO OVERVIEW
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <Settings className="w-3.5 h-3.5 md:w-4 md:h-4 text-white/60" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Settings</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Project Settings</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Configure project properties and preferences
        </p>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* General Settings */}
        <div className="bg-white/5 border border-white/10 p-4 md:p-6">
          <h2 className="text-sm font-mono font-bold text-white mb-4">General</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                Project Name
              </label>
              <input
                type="text"
                defaultValue="New Project"
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                Description
              </label>
              <textarea
                rows={3}
                placeholder="Add a description..."
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 resize-none"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                <Tag className="w-3 h-3 inline mr-1" />
                Tags
              </label>
              <input
                type="text"
                placeholder="Add tags separated by commas..."
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
              />
            </div>
          </div>
        </div>

        {/* Visibility */}
        <div className="bg-white/5 border border-white/10 p-4 md:p-6">
          <h2 className="text-sm font-mono font-bold text-white mb-4">Visibility</h2>
          <div className="flex gap-2">
            <button
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 bg-cyan-500/20 border border-cyan-500/50 text-cyan-400 transition-all"
            >
              <Eye className="w-4 h-4" />
              <span className="text-xs font-mono">Public</span>
            </button>
            <button
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 bg-black border border-white/10 text-white/60 hover:border-white/20 transition-all"
            >
              <EyeOff className="w-4 h-4" />
              <span className="text-xs font-mono">Private</span>
            </button>
          </div>
          <p className="text-[10px] font-mono text-white/30 mt-2">
            Public projects are visible to all team members
          </p>
        </div>

        {/* Simulation Defaults */}
        <div className="bg-white/5 border border-white/10 p-4 md:p-6">
          <h2 className="text-sm font-mono font-bold text-white mb-4">Simulation Defaults</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                Default Horizon
              </label>
              <input
                type="number"
                defaultValue={100}
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-white/40 uppercase mb-2">
                Tick Rate
              </label>
              <input
                type="number"
                defaultValue={1}
                className="w-full px-3 py-2 bg-black border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-white/30"
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white/5 border border-white/10 p-4 md:p-6">
          <h2 className="text-sm font-mono font-bold text-white mb-4">Actions</h2>
          <div className="space-y-3">
            <button className="w-full flex items-center gap-3 px-4 py-3 bg-black border border-white/10 hover:border-white/20 transition-colors text-left">
              <Copy className="w-4 h-4 text-white/40" />
              <div className="flex-1">
                <span className="text-sm font-mono text-white">Duplicate Project</span>
                <p className="text-[10px] font-mono text-white/40">Create a copy of this project</p>
              </div>
            </button>
            <button className="w-full flex items-center gap-3 px-4 py-3 bg-black border border-white/10 hover:border-yellow-500/30 transition-colors text-left">
              <Archive className="w-4 h-4 text-yellow-400" />
              <div className="flex-1">
                <span className="text-sm font-mono text-white">Archive Project</span>
                <p className="text-[10px] font-mono text-white/40">Move to archived projects</p>
              </div>
            </button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-red-500/5 border border-red-500/20 p-4 md:p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <h2 className="text-sm font-mono font-bold text-red-400">Danger Zone</h2>
          </div>
          <button className="w-full flex items-center gap-3 px-4 py-3 bg-black border border-red-500/30 hover:bg-red-500/10 transition-colors text-left">
            <Trash2 className="w-4 h-4 text-red-400" />
            <div className="flex-1">
              <span className="text-sm font-mono text-red-400">Delete Project</span>
              <p className="text-[10px] font-mono text-white/40">Permanently delete this project and all data</p>
            </div>
          </button>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button className="text-xs font-mono">
            <Save className="w-3 h-3 mr-2" />
            SAVE CHANGES
          </Button>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-2xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PROJECT SETTINGS</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}
