export interface TaskSubmissionData {
  [key: string]: string | number | undefined;
  endpoint: string;
  taskName: string;
  partition: string;
  account: string;
  reservation?: string;
  container: string;
  task?: string;
  num_of_nodes?: number;
  time_duration: string;
  dataset_id?: string;
  slurm_options?: string;
  input_path?: string;
  input_content?: string;
  output_path?: string;
  model?: string;
  engine?: 'vllm' | 'ollama' | '';
  batch_size?: number;
  hf_token?: string;
}

export interface TemplateCustomField {
  key: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  /** Required only when the referenced field is empty (e.g. image_path unless image_upload). */
  requiredUnless?: string;
  /** 'file' renders an upload input; the file is stored base64-encoded under `key`
   *  and its sanitized name under `${key}_filename`. 'number' renders a numeric
   *  input validated as a positive integer. Defaults to a text input. */
  type?: 'text' | 'file' | 'number';
  /** Accept attribute for file inputs, e.g. "image/*". */
  accept?: string;
  /** Hint text rendered under the field. */
  help?: string;
  optional?: Array<string | { label: string; value: string }>;
}

export interface Task {
  task_id: string;
  identity_id: string;
  task_name: string;
  status: 'COMPLETED' | 'PENDING' | 'RUNNING' | 'FAILED';
  task_type?: 'default' | 'vllm_chat' | string;
  details: {
    endpoint_id: string;
    endpoint_name?: string;
    task_create_time: string;
  };
  result: string | null;
  error: string | null;
  artifact_path?: string | null;
  chat?: {
    port?: number | null;
    model?: string | null;
  } | null;
}

export interface TasksApiResponse {
  [taskId: string]: Task;
}

export interface TaskOutputEntry {
  name: string;
  is_dir: boolean;
  size: number | null;
}

export interface TaskOutputFilesApiResponse {
  artifact_path: string;
  entries: TaskOutputEntry[];
  truncated: boolean;
  error?: string;
}

export interface Endpoint {
  endpoint_name: string;
  endpoint_uuid: string;
  endpoint_host: string;
  endpoint_status: string;
  diamond_dir: string;
  is_managed?: boolean;
}

export interface Container {
  container_task_id: string;
  status: string;
  base_image: string;
  location: string;
  host_name?: string;
  is_public?: boolean;
  owner_identity_id?: string;
  is_owner?: boolean;
}

export interface ContainersResponse {
  [containerName: string]: Container;
}

export interface EndpointContainersApiResponse {
  private: ContainersResponse;
  public: ContainersResponse;
}

export interface Dataset {
  id: number;
  collection_uuid: string;
  globus_path: string;
  system_path: string;
  public: boolean;
  machine_name: string;
  dataset_name: string;
  dataset_metadata: string | null;
}

export interface DatasetsApiResponse {
  datasets: Dataset[];
}

export interface TaskTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  submissionEndpoint?: '/api/submit_task' | '/api/launch_llmflux';
  taskTemplate?: string;
  hiddenFields?: string[];
  customFields?: TemplateCustomField[];
  defaults: Partial<TaskSubmissionData>;
}
