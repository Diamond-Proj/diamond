'use client';

import { EndpointStep } from './steps/endpoint-step';
import { ContainerStep } from './steps/container-step';
import { BuildStep } from './steps/build-step';
import { BuilderFormData } from '@/app/(workspace)/images/types';

interface BuilderStepsProps {
  step: number;
  formData: Partial<BuilderFormData>;
  onUpdate: (data: Partial<BuilderFormData>) => void;
}

export function BuilderSteps({ step, formData, onUpdate }: BuilderStepsProps) {
  switch (step) {
    case 0:
      return <EndpointStep formData={formData} onUpdate={onUpdate} />;
    case 1:
      return <ContainerStep formData={formData} onUpdate={onUpdate} />;
    case 2:
      return <BuildStep formData={formData} onUpdate={onUpdate} />;
    default:
      return null;
  }
}
