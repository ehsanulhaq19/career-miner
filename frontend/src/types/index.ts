export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface JobSite {
  id: number;
  name: string;
  url: string;
  scrap_duration: number;
  last_scrapped: string | null;
  is_active: boolean;
  categories: string[];
  created_at: string;
  updated_at: string;
}

export interface ClientSite {
  id: number;
  name: string;
  url: string;
  scrap_duration: number;
  last_scrapped: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ParsedData {
  job_title?: string;
  job_type?: string;
  location?: string;
  skills?: string[];
  experience?: string;
  salary?: string;
  company_name?: string;
  company_emails?: string[];
  company_numbers?: string[];
  company_link?: string;
  company_size?: string;
  job_link?: string;
  job_posted_datetime?: string;
}

export interface CareerJob {
  id: number;
  title: string;
  description: string | null;
  url: string | null;
  job_site_id: number;
  scrap_job_id: number;
  meta_data: Record<string, any>;
  parsed_data?: ParsedData;
  created_at: string;
  updated_at: string;
  job_site_name?: string;
  career_client_name?: string;
  career_client_emails?: string[];
  career_client_official_website?: string | null;
  job_seen?: boolean;
}

export interface JobApplication {
  id: number;
  application_name: string;
  resume_id: number;
  user_id: number;
  applied_on: string;
  is_active: boolean;
  subject: string | null;
  cover_letter: string | null;
  output_resume_path: string | null;
  career_job_id: number;
  similarity_score?: number | null;
  meta_data: Record<string, unknown>;
  is_email_send: boolean;
  to_emails: string[];
  created_at: string;
  career_job_title?: string | null;
  career_client_id?: number | null;
  career_client_name?: string | null;
  job_site_name?: string | null;
  resume_name?: string | null;
  email_send_count?: number;
}

export interface EmailLog {
  id: number;
  subject: string;
  content: string | null;
  file_attachment: string | null;
  to_email: string;
  from_email: string | null;
  response: string | null;
  status: string;
  created_at: string;
}

export interface BulkJobApplicationEmailSendLog {
  id: number;
  bulk_job_application_email_send_id: number;
  action: string;
  progress: number;
  status: string;
  details: string | null;
  meta_data: Record<string, unknown>;
  created_at: string;
}

export interface ScrapJob {
  id: number;
  name: string;
  job_site_id: number;
  status:
    | "pending"
    | "in_progress"
    | "completed"
    | "error"
    | "terminated"
    | "stopped";
  meta_data?: {
    total_jobs_scraped_from_html?: number;
    total_jobs_validated?: number;
    total_jobs_created?: number;
    load_more_on_scroll?: boolean;
    max_scroll?: number;
  };
  created_at: string;
  updated_at: string;
}

export interface ScrapJobLog {
  id: number;
  scrap_job_id: number;
  action: string;
  progress: number;
  status: string;
  details: string | null;
  meta_data: Record<string, unknown>;
  created_at: string;
}

export interface ScrapClientJob {
  id: number;
  name: string;
  status:
    | "pending"
    | "in_progress"
    | "completed"
    | "error"
    | "terminated"
    | "stopped";
  meta_data?: {
    total?: number;
    pending?: number;
    processing?: number;
    completed?: number;
    failed?: number;
    client_ids?: number[];
    only_clients_without_emails?: boolean;
  };
  created_at: string;
  updated_at: string;
}

export interface BulkJobApplicationLog {
  id: number;
  bulk_job_application_id: number;
  action: string;
  progress: number;
  status: string;
  details: string | null;
  meta_data: Record<string, unknown>;
  created_at: string;
}

export interface CareerJobDateGroup {
  date: string;
  job_count: number;
}

export interface CareerJobWithApplicationCounts extends CareerJob {
  career_client_id?: number | null;
  active_application_count: number;
  inactive_application_count: number;
}

export interface ScrapClientLog {
  id: number;
  scrap_client_job_id: number;
  action: string;
  progress: number;
  status: string;
  details: string | null;
  meta_data: Record<string, unknown>;
  created_at: string;
}

export interface CareerClient {
  id: number;
  emails: string[];
  official_website?: string | null;
  name: string | null;
  location: string | null;
  meta_data?: Record<string, unknown> | null;
  detail: string | null;
  link: string | null;
  size: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CareerClientEmailRow {
  client_id: number;
  client_name: string | null;
  official_website: string | null;
  location: string | null;
  client_email: string;
  email_count: number;
}

export interface BulkCareerClientEmailSendLog {
  id: number;
  bulk_career_client_email_send_id: number;
  action: string;
  progress: number;
  status: string;
  details: string | null;
  meta_data: Record<string, unknown>;
  created_at: string;
}

export interface ActiveJobsByFit {
  score_100: number;
  above_90: number;
  above_80: number;
  above_70: number;
  above_60: number;
  above_50: number;
  below_50: number;
}

export interface DashboardStats {
  total_jobs_executed: number;
  total_job_records: number;
  total_job_sites: number;
  total_clients: number;
  total_job_email_logs?: number;
  job_site_cards: JobSiteCard[];
  active_jobs_by_fit?: ActiveJobsByFit;
}

export interface JobSiteCard {
  id: number;
  name: string;
  url: string;
  total_jobs: number;
  last_scrapped: string | null;
  is_active: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  limit?: number;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
}

export interface ThemeState {
  mode: "light" | "dark";
}

export interface Resume {
  id: number;
  name: string;
  size: number;
  extension: string;
  content: string | null;
  extra_detail: string | null;
  uploaded_by_id: number;
  is_active: boolean;
  created_at: string;
}
