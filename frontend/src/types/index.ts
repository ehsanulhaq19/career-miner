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

export interface CareerJob {
  id: number;
  title: string;
  description: string | null;
  url: string | null;
  job_site_id: number;
  scrap_job_id: number;
  meta_data: Record<string, any>;
  contact_details: string | null;
  created_at: string;
  updated_at: string;
  job_site_name?: string;
}

export interface ScrapJob {
  id: number;
  name: string;
  job_site_id: number;
  status: "pending" | "in_progress" | "completed" | "error" | "terminated";
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_jobs_executed: number;
  total_job_records: number;
  total_job_sites: number;
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
