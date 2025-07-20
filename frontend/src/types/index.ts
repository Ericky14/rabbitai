export interface User {
  name: string;
  email: string;
  picture: string;
}

export interface JobStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  input_file?: string;
  output_key?: string;
  processing_time?: number;
  downloadUrl?: string;
  error?: string;
}

export interface GoogleCredentialResponse {
  credential: string;
}

export interface UploadResponse {
  job_id: string;
  status: string;
  input_file: string;
}

export interface DownloadResponse {
  download_url: string;
}