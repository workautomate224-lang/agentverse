'use client';

/**
 * Exit Confirmation Modal
 * Reference: blueprint.md §4.3
 *
 * Prompts users when they try to leave with unsaved changes.
 * Can be used with ClarifyPanel or any component that needs save protection.
 */

import { useEffect, useCallback } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';

interface ExitConfirmationModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback when modal is closed */
  onOpenChange: (open: boolean) => void;
  /** Callback when user confirms exit (discards changes) */
  onConfirmExit: () => void;
  /** Callback when user saves before exit */
  onSaveAndExit?: () => void;
  /** Whether save is in progress */
  isSaving?: boolean;
  /** Custom title */
  title?: string;
  /** Custom description */
  description?: string;
}

export function ExitConfirmationModal({
  open,
  onOpenChange,
  onConfirmExit,
  onSaveAndExit,
  isSaving = false,
  title = 'Unsaved Changes',
  description = 'You have unsaved changes. Would you like to save them before leaving?',
}: ExitConfirmationModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded bg-yellow-400/10 border border-yellow-400/30">
              <AlertTriangle className="h-5 w-5 text-yellow-400" />
            </div>
            <DialogTitle className="font-mono">{title}</DialogTitle>
          </div>
          <DialogDescription className="font-mono text-sm">
            {description}
          </DialogDescription>
        </DialogHeader>

        <DialogFooter className="mt-4 flex flex-col sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="font-mono text-xs border-white/20 text-gray-400 hover:bg-white/5"
          >
            Cancel
          </Button>
          <Button
            variant="outline"
            onClick={onConfirmExit}
            className="font-mono text-xs border-red-400/30 text-red-400 hover:bg-red-400/10"
          >
            Discard Changes
          </Button>
          {onSaveAndExit && (
            <Button
              onClick={onSaveAndExit}
              disabled={isSaving}
              className="font-mono text-xs bg-cyan-500 hover:bg-cyan-400 text-black"
            >
              {isSaving ? 'Saving...' : 'Save & Exit'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Hook to detect navigation and trigger exit confirmation
 */
interface UseExitConfirmationOptions {
  /** Whether there are unsaved changes */
  hasUnsavedChanges: boolean;
  /** Callback before confirming exit */
  onBeforeExit?: () => Promise<boolean> | boolean;
}

export function useExitConfirmation({
  hasUnsavedChanges,
}: UseExitConfirmationOptions) {
  // Handle browser beforeunload event
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
        return '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // For Next.js route changes, we'd need to use the router events
  // This is handled at the component level with state management

  return { hasUnsavedChanges };
}

export default ExitConfirmationModal;
