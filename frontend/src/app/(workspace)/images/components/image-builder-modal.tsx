'use client';

import { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { BuilderSteps } from './builder/builder-steps';
import { BuilderReview } from './builder/builder-review';
import { BuilderLogs } from './builder/builder-logs';
import { useToast } from '@/components/ui/use-toast';
import {
  BuilderFormData,
  ImageBuilderPayload,
  ImageBuilderResponse
} from '@/app/(workspace)/images/types';

interface ImageBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const STEPS = [
  {
    id: 'endpoint',
    title: 'Endpoint & Resources',
    description:
      'Select the HPC endpoint and configure compute resource allocation settings'
  },
  {
    id: 'container',
    title: 'Container Info',
    description: 'Configure your container name, build location, and base image'
  },
  {
    id: 'build',
    title: 'Build Configuration',
    description:
      'Configure build dependencies, environment variables, and commands'
  },
  {
    id: 'review',
    title: 'Review & Build',
    description: 'Review your configuration before starting the build process'
  }
];

export function ImageBuilderModal({
  isOpen,
  onClose,
  onSuccess
}: ImageBuilderModalProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Partial<BuilderFormData>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [buildData, setBuildData] = useState<{
    task_id: string;
    container_name: string;
  } | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (!isOpen) {
      // Reset state when modal closes
      setCurrentStep(0);
      setFormData({});
      setIsSubmitting(false);
      setBuildData(null);
      setShowLogs(false);
    }
  }, [isOpen]);

  const updateFormData = (stepData: Partial<BuilderFormData>) => {
    setFormData((prev) => ({ ...prev, ...stepData }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0: // Endpoint step
        return (
          formData.endpoint &&
          formData.partition &&
          formData.account &&
          formData.hasDiamondDir !== false
        );
      case 1: // Container step
        return formData.containerName && formData.baseImage;
      case 2: // Build step
        return true;
      case 3: // Review step
        return true;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);

    try {
      const payload: ImageBuilderPayload = {
        endpoint: formData.endpoint || '',
        partition: formData.partition || '',
        name: formData.containerName || '',
        location: formData.location || '',
        base_image: formData.baseImage || '',
        dependencies: formData.dependencies || '',
        environment: formData.environment || '',
        commands: formData.commands || '',
        account: formData.account || '',
        reservation: formData.reservation || ''
      };

      const response = await fetch('/api/image_builder', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok)
        throw new Error('Failed to submit image build configuration');

      const result: ImageBuilderResponse = await response.json();
      setBuildData({
        task_id: result.task_id,
        container_name: result.container_name
      });
      setShowLogs(true);

      toast({
        title: 'Build Started',
        description:
          'Your container image build has been submitted successfully!'
      });
    } catch (error) {
      console.error('Error submitting build:', error);
      toast({
        title: 'Build Failed',
        description:
          'Failed to submit image build configuration. Please try again.',
        variant: 'destructive'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBuildComplete = () => {
    onSuccess();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] shadow-xl dark:border-slate-700/80">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200/70 p-6 dark:border-slate-700/70">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Image Builder
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              {showLogs ? 'Build in Progress' : STEPS[currentStep]?.description}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close"
            className="cursor-pointer text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Progress Bar */}
        {!showLogs && (
          <div className="border-b border-slate-200/70 bg-slate-50/70 px-6 py-4 dark:border-slate-700/70 dark:bg-slate-900/50">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Step {currentStep + 1} of {STEPS.length}
              </span>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {Math.round(((currentStep + 1) / STEPS.length) * 100)}%
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className="h-2 rounded-full bg-slate-900 transition-all duration-300 dark:bg-slate-100"
                style={{
                  width: `${((currentStep + 1) / STEPS.length) * 100}%`
                }}
              />
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {showLogs && buildData ? (
            <BuilderLogs
              taskId={buildData.task_id}
              containerName={buildData.container_name}
              endpoint={formData.endpoint!}
              onComplete={handleBuildComplete}
            />
          ) : (
            <div className="p-6">
              {currentStep < 3 ? (
                <BuilderSteps
                  step={currentStep}
                  formData={formData}
                  onUpdate={updateFormData}
                />
              ) : (
                <BuilderReview formData={formData as BuilderFormData} />
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {!showLogs && (
          <div className="flex items-center justify-between border-t border-slate-200/70 bg-slate-50/70 p-6 dark:border-slate-700/70 dark:bg-slate-900/60">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={currentStep === 0}
              className="flex cursor-pointer items-center gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>

            {currentStep < STEPS.length - 1 ? (
              <Button
                onClick={handleNext}
                disabled={!canProceed()}
                className="flex cursor-pointer items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={!canProceed() || isSubmitting}
                className="flex cursor-pointer items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Play className="h-4 w-4" />
                {isSubmitting ? 'Starting Build...' : 'Start Build'}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
