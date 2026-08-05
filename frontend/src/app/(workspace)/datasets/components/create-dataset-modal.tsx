'use client';

import { useState, useRef, useEffect } from 'react';
import { X, Upload, Loader2, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import { VALID_MACHINES } from '@/app/(workspace)/datasets/utils';
import {
  CreateDatasetRequest,
  DatasetFormData,
  CreateDatasetApiResponse
} from '@/app/(workspace)/datasets/datasets.types';

interface CreateDatasetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDatasetCreated: () => void;
}

export function CreateDatasetModal({
  isOpen,
  onClose,
  onDatasetCreated
}: CreateDatasetModalProps) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [formData, setFormData] = useState<DatasetFormData>({
    collection_uuid: '',
    globus_path: '',
    system_path: '',
    machine_name: '',
    dataset_name: '',
    description: '',
    size: '',
    format: ''
  });

  const [errors, setErrors] = useState<Partial<DatasetFormData>>({});

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const validateForm = (): boolean => {
    const newErrors: Partial<DatasetFormData> = {};

    if (!formData.collection_uuid.trim()) {
      newErrors.collection_uuid = 'Collection UUID is required';
    }
    if (!formData.globus_path.trim()) {
      newErrors.globus_path = 'Globus path is required';
    }
    if (!formData.system_path.trim()) {
      newErrors.system_path = 'System path is required';
    }
    if (!formData.machine_name.trim()) {
      newErrors.machine_name = 'Machine name is required';
    }
    if (!formData.dataset_name.trim()) {
      newErrors.dataset_name = 'Dataset name is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const metadata = {
        description: formData.description.trim() || 'No description provided',
        size: formData.size.trim() || 'Unknown',
        format: formData.format.trim() || 'Unknown'
      };

      const payload: CreateDatasetRequest = {
        collection_uuid: formData.collection_uuid.trim(),
        globus_path: formData.globus_path.trim(),
        system_path: formData.system_path.trim(),
        machine_name: formData.machine_name,
        dataset_name: formData.dataset_name.trim(),
        dataset_metadata: JSON.stringify(metadata)
      };

      const response = await fetch('/api/datasets', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create dataset');
      }

      const result: CreateDatasetApiResponse = await response.json();

      onDatasetCreated();

      toast({
        title: 'Success',
        description: result.message || 'Dataset registered successfully!',
        className: 'bg-green-500 text-white'
      });

      setFormData({
        collection_uuid: '',
        globus_path: '',
        system_path: '',
        machine_name: '',
        dataset_name: '',
        description: '',
        size: '',
        format: ''
      });
      setErrors({});
      onClose();
    } catch (error) {
      console.error('Error creating dataset:', error);
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to create dataset. Please try again.',
        variant: 'destructive'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field: keyof DatasetFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const handleMachineSelect = (machine: string) => {
    handleInputChange('machine_name', machine);
    setIsDropdownOpen(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] shadow-xl dark:border-slate-700/80">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200/70 p-6 dark:border-slate-700/70">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Register New Dataset
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              Register a dataset with Diamond platform
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close"
            className="cursor-pointer text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            disabled={isLoading}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content - Scrollable Area */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100">
                  Required Information
                </h3>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Dataset Name *
                  </label>
                  <Input
                    value={formData.dataset_name}
                    onChange={(e) =>
                      handleInputChange('dataset_name', e.target.value)
                    }
                    placeholder="e.g., My Research Dataset"
                    className={`mt-1 ${errors.dataset_name ? 'border-red-500' : ''}`}
                    disabled={isLoading}
                  />
                  {errors.dataset_name && (
                    <p className="mt-1 text-sm text-red-600">
                      {errors.dataset_name}
                    </p>
                  )}
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    A human-readable name for your dataset
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Collection UUID *
                    </label>
                    <Input
                      value={formData.collection_uuid}
                      onChange={(e) =>
                        handleInputChange('collection_uuid', e.target.value)
                      }
                      placeholder="e.g., abc123-def456-ghi789"
                      className={`mt-1 ${errors.collection_uuid ? 'border-red-500' : ''}`}
                      disabled={isLoading}
                    />
                    {errors.collection_uuid && (
                      <p className="mt-1 text-sm text-red-600">
                        {errors.collection_uuid}
                      </p>
                    )}
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      The Globus collection UUID where your data is stored
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Globus Path *
                    </label>
                    <Input
                      value={formData.globus_path}
                      onChange={(e) =>
                        handleInputChange('globus_path', e.target.value)
                      }
                      placeholder="e.g., /data/project1"
                      className={`mt-1 ${errors.globus_path ? 'border-red-500' : ''}`}
                      disabled={isLoading}
                    />
                    {errors.globus_path && (
                      <p className="mt-1 text-sm text-red-600">
                        {errors.globus_path}
                      </p>
                    )}
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      Path within the Globus collection
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                      System Path *
                    </label>
                    <Input
                      value={formData.system_path}
                      onChange={(e) =>
                        handleInputChange('system_path', e.target.value)
                      }
                      placeholder="e.g., /home/user/data"
                      className={`mt-1 ${errors.system_path ? 'border-red-500' : ''}`}
                      disabled={isLoading}
                    />
                    {errors.system_path && (
                      <p className="mt-1 text-sm text-red-600">
                        {errors.system_path}
                      </p>
                    )}
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      File system path on the compute machine
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Machine Name *
                    </label>
                    <div className="relative mt-1" ref={dropdownRef}>
                      <button
                        type="button"
                        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                        disabled={isLoading}
                        className={`flex h-10 w-full cursor-pointer items-center justify-between rounded-lg border bg-white/80 px-3 py-2 text-sm text-slate-900 transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-rose-500/25 dark:bg-slate-900/80 dark:text-slate-100 ${
                          errors.machine_name
                            ? 'border-red-500'
                            : 'border-slate-200/80 hover:border-slate-300 dark:border-slate-700/80 dark:hover:border-slate-600'
                        }`}
                      >
                        <span
                          className={
                            formData.machine_name
                              ? ''
                              : 'text-slate-500 dark:text-slate-400'
                          }
                        >
                          {formData.machine_name || 'Select a machine'}
                        </span>
                        <ChevronDown
                          className={`h-4 w-4 text-slate-400 transition-transform duration-200 dark:text-slate-500 ${
                            isDropdownOpen ? 'rotate-180' : ''
                          }`}
                        />
                      </button>

                      {isDropdownOpen && (
                        <div className="absolute top-full left-0 z-10 mt-1 w-full rounded-lg border border-slate-200/80 bg-[hsl(var(--dashboard-surface))] p-1 shadow-lg shadow-slate-900/10 dark:border-slate-700/80 dark:shadow-black/35">
                          {VALID_MACHINES.map((machine) => (
                            <button
                              key={machine}
                              type="button"
                              onClick={() => handleMachineSelect(machine)}
                              className={`w-full cursor-pointer rounded-md px-3 py-2 text-left text-sm transition-colors duration-150 ${
                                formData.machine_name === machine
                                  ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/20 dark:text-rose-200'
                                  : 'text-slate-900 hover:bg-slate-100 dark:text-slate-100 dark:hover:bg-slate-800'
                              }`}
                            >
                              {machine}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    {errors.machine_name && (
                      <p className="mt-1 text-sm text-red-600">
                        {errors.machine_name}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100">
                  Optional Information
                </h3>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Description
                  </label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) =>
                      handleInputChange('description', e.target.value)
                    }
                    placeholder="Provide a description of your dataset..."
                    className="mt-1"
                    rows={3}
                    disabled={isLoading}
                  />
                </div>

                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Size
                    </label>
                    <Input
                      value={formData.size}
                      onChange={(e) =>
                        handleInputChange('size', e.target.value)
                      }
                      placeholder="e.g., 2.4 GB"
                      className="mt-1"
                      disabled={isLoading}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Format
                    </label>
                    <Input
                      value={formData.format}
                      onChange={(e) =>
                        handleInputChange('format', e.target.value)
                      }
                      placeholder="e.g., CSV, JSON, HDF5"
                      className="mt-1"
                      disabled={isLoading}
                    />
                  </div>
                </div>
              </div>
            </form>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-slate-200/70 bg-slate-50/70 p-6 dark:border-slate-700/70 dark:bg-slate-900/60">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
            className="cursor-pointer"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading}
            className="cursor-pointer bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Registering...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Register Dataset
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
