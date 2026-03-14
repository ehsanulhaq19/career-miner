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
  job_seen?: boolean;
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
  detail: string | null;
  link: string | null;
  size: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DashboardStats {
  total_jobs_executed: number;
  total_job_records: number;
  total_job_sites: number;
  total_clients: number;
  job_site_cards: JobSiteCard[];
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
