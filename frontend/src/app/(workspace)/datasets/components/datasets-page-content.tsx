'use client';

import { useEffect, useMemo, useState } from 'react';
import { Plus } from 'lucide-react';

import { CreateDatasetModal } from './create-dataset-modal';
import { DatasetStats } from './dataset-stats';
import { DatasetControls } from './dataset-controls';
import { DatasetList } from './dataset-list';
import {
  DisplayDataset,
  Dataset,
  DatasetsApiResponse
} from '../datasets.types';
import { transformDataset } from '../utils';

export function DatasetsPageContent() {
  const [datasets, setDatasets] = useState<DisplayDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'public' | 'private'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchDatasets = async () => {
    try {
      setLoading(true);

      const response = await fetch('/api/datasets', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        console.error('Failed to fetch datasets:', await response.text());
        throw new Error('Failed to fetch datasets');
      }

      const data: DatasetsApiResponse = await response.json();
      const transformedDatasets = data.datasets.map((dataset: Dataset) =>
        transformDataset(dataset)
      );

      setDatasets(transformedDatasets);
    } catch (error) {
      console.error('Error fetching datasets:', error);
      setDatasets([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleDatasetCreated = () => {
    fetchDatasets();
    setShowCreateModal(false);
  };

  const filteredDatasets = useMemo(() => {
    return datasets.filter((dataset) => {
      const matchesFilter =
        filter === 'all' ||
        (filter === 'public' && dataset.public) ||
        (filter === 'private' && !dataset.public);

      const matchesSearch =
        dataset.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        dataset.globus_path.toLowerCase().includes(searchTerm.toLowerCase()) ||
        dataset.system_path.toLowerCase().includes(searchTerm.toLowerCase()) ||
        dataset.machine_name.toLowerCase().includes(searchTerm.toLowerCase());

      return matchesFilter && matchesSearch;
    });
  }, [datasets, filter, searchTerm]);

  return (
    <div className="space-y-6">
      <section className="dashboard-card relative overflow-hidden p-5 md:p-6">
        <div className="pointer-events-none absolute -right-10 -top-16 h-40 w-40 rounded-full bg-indigo-400/6 blur-2xl" />
        <div className="pointer-events-none absolute -left-8 -bottom-12 h-36 w-36 rounded-full bg-primary/5 blur-2xl" />

        <div className="relative z-10 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Datasets
            </h1>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="group inline-flex cursor-pointer items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary/90"
          >
            <Plus className="h-4 w-4 transition-transform duration-200 group-hover:scale-110" />
            Create Dataset
          </button>
        </div>
      </section>

      <DatasetStats datasets={datasets} loading={loading} />

      <DatasetControls
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        filter={filter}
        setFilter={setFilter}
      />

      <DatasetList datasets={filteredDatasets} loading={loading} />

      <CreateDatasetModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onDatasetCreated={handleDatasetCreated}
      />
    </div>
  );
}
