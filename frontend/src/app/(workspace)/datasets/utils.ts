import { Dataset, DatasetMetadata, DisplayDataset } from './datasets.types';

export function transformDataset(dataset: Dataset): DisplayDataset {
  let metadata: DatasetMetadata = {};

  if (dataset.dataset_metadata) {
    try {
      metadata = JSON.parse(dataset.dataset_metadata) ?? {};
    } catch (error) {
      console.warn('Failed to parse dataset metadata:', error);
    }
  }

  return {
    id: dataset.id,
    collection_uuid: dataset.collection_uuid,
    globus_path: dataset.globus_path,
    system_path: dataset.system_path,
    public: dataset.public,
    machine_name: dataset.machine_name,
    dataset_name: dataset.dataset_name || `Dataset ${dataset.id}`,
    description: metadata.description || 'No description available',
    size: metadata.size || 'Unknown',
    format: metadata.format || 'Unknown'
  };
}

export const VALID_MACHINES = [
  'Delta@NCSA',
  'Frontera@TACC',
  'Lonestar6@TACC',
  'Anvil@RCAC',
  'System@TACC',
  'System@NCSA'
] as const;
