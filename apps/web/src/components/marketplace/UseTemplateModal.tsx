'use client';

import { useState } from 'react';
import { X, FileText, ArrowRight, AlertCircle } from 'lucide-react';
import { MarketplaceTemplateDetail, Project } from '@/lib/api';

interface UseTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  template: MarketplaceTemplateDetail;
  projects: Project[];
  onUse: (data: {
    target_project_id?: string;
    name?: string;
    create_type: 'scenario' | 'product';
  }) => Promise<void>;
  isLoading?: boolean;
}

export function UseTemplateModal({
  isOpen,
  onClose,
  template,
  projects,
  onUse,
  isLoading = false,
}: UseTemplateModalProps) {
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [createNewProject, setCreateNewProject] = useState(false);
  const [customName, setCustomName] = useState('');
  const [createType, setCreateType] = useState<'scenario' | 'product'>('scenario');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    setError(null);

    if (!createNewProject && !selectedProjectId) {
      setError('Please select a project or choose to create a new one');
      return;
    }

    try {
      await onUse({
        target_project_id: createNewProject ? undefined : selectedProjectId,
        name: customName || undefined,
        create_type: createType,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to use template');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-lg w-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Use Template
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 space-y-6">
            {/* Template info */}
            <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">{template.name}</h3>
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                  {template.short_description || template.description}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                    {template.category_name || 'Uncategorized'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {template.recommended_population_size} agents recommended
                  </span>
                </div>
              </div>
            </div>

            {/* Create type selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                What would you like to create?
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setCreateType('scenario')}
                  className={`p-4 rounded-lg border-2 text-left transition-all ${
                    createType === 'scenario'
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span className="font-medium text-gray-900">Scenario</span>
                  <p className="text-xs text-gray-500 mt-1">
                    Create a reusable scenario for simulations
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setCreateType('product')}
                  className={`p-4 rounded-lg border-2 text-left transition-all ${
                    createType === 'product'
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span className="font-medium text-gray-900">Product</span>
                  <p className="text-xs text-gray-500 mt-1">
                    Create a complete product with scenarios
                  </p>
                </button>
              </div>
            </div>

            {/* Project selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Project
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={createNewProject}
                    onChange={() => setCreateNewProject(true)}
                    className="text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-700">
                    Create a new project
                  </span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={!createNewProject}
                    onChange={() => setCreateNewProject(false)}
                    className="text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-700">
                    Add to existing project
                  </span>
                </label>
              </div>

              {!createNewProject && (
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="mt-3 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
                >
                  <option value="">Select a project...</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Custom name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Custom Name (optional)
              </label>
              <input
                type="text"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder={`${template.name} (Copy)`}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                'Creating...'
              ) : (
                <>
                  Use Template
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UseTemplateModal;
