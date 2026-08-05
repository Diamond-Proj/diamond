interface DatasetBase {
  id: number;
  collection_uuid: string;
  globus_path: string;
  system_path: string;
  public: boolean;
  machine_name: string;
  dataset_name: string;
}

export interface Dataset extends DatasetBase {
  dataset_metadata: string | null;
}

export interface DatasetMetadata {
  description?: string;
  size?: string;
  format?: string;
}

export interface DisplayDataset extends DatasetBase {
  description: string;
  size: string;
  format: string;
}

export interface CreateDatasetRequest {
  collection_uuid: string;
  globus_path: string;
  system_path: string;
  machine_name: string;
  dataset_name: string;
  dataset_metadata?: string;
}

export interface DatasetFormData {
  collection_uuid: string;
  globus_path: string;
  system_path: string;
  machine_name: string;
  dataset_name: string;
  description: string;
  size: string;
  format: string;
}

export interface DatasetsApiResponse {
  datasets: Dataset[];
}

export interface CreateDatasetApiResponse {
  status: string;
  message: string;
}
