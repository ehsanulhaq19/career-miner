import api from "./api";
import {
  BulkJobApplicationLog,
  BulkJobApplicationEmailSendLog,
  EmailLog,
  JobApplication,
  JobApplicationDateGroup,
  PaginatedResponse,
} from "@/types";

export interface CreateJobApplicationPayload {
  career_job_id: number;
  resume_id: number;
}

export interface LiveJobApplicationPayload {
  job_details: string;
  resume_id: number;
  action:
    | "create_job_application"
    | "create_and_send_job_application";
}

export interface LiveJobDuplicateCheckResult {
  exists: boolean;
  career_job_id?: number | null;
  title?: string | null;
  description?: string | null;
}

export interface BulkJobApplicationCreatePayload {
  resume_id: number;
  career_job_ids: number[];
}

export interface JobApplicationUpdatePayload {
  is_active?: boolean;
}

export interface BulkJobApplicationUpdatePayload {
  job_application_ids: number[];
  is_active: boolean;
}

export const jobApplicationService = {
  async getJobApplicationDatesGrouped(skip = 0, limit = 50) {
    const { data } = await api.get<{
      items: JobApplicationDateGroup[];
      total: number;
      page: number;
      limit: number;
    }>("/job-applications/grouped-by-date", { params: { skip, limit } });
    return data;
  },

  async getJobApplicationsByCreatedDate(
    date: string,
    skip = 0,
    limit = 50
  ) {
    const { data } = await api.get<PaginatedResponse<JobApplication>>(
      "/job-applications/by-date",
      { params: { date, skip, limit } }
    );
    return data;
  },

  async getJobApplications(
    skip = 0,
    limit = 20,
    is_active?: boolean
  ) {
    const params: Record<string, string | number | boolean> = {
      skip,
      limit,
    };
    if (is_active !== undefined) {
      params.is_active = is_active;
    }
    const { data } = await api.get<PaginatedResponse<JobApplication>>(
      "/job-applications",
      { params }
    );
    return data;
  },

  async getJobApplicationById(id: number) {
    const { data } = await api.get<JobApplication>(
      `/job-applications/${id}`
    );
    return data;
  },

  async getJobApplicationFileBlobUrl(id: number): Promise<string> {
    const { data } = await api.get<Blob>(`/job-applications/${id}/file`, {
      responseType: "blob",
    });
    return URL.createObjectURL(data);
  },

  async createJobApplication(payload: CreateJobApplicationPayload) {
    const { data } = await api.post<JobApplication>(
      "/job-applications",
      payload
    );
    return data;
  },

  async checkLiveJobDuplicate(job_details: string) {
    const { data } = await api.post<LiveJobDuplicateCheckResult>(
      "/job-applications/live/check",
      { job_details }
    );
    return data;
  },

  async createLiveJobApplication(payload: LiveJobApplicationPayload) {
    const { data } = await api.post<JobApplication>(
      "/job-applications/live",
      payload
    );
    return data;
  },

  async createBulkJobApplications(payload: BulkJobApplicationCreatePayload) {
    const { data } = await api.post<{ id: number; status: string }>(
      "/job-applications/bulk",
      payload
    );
    return data;
  },

  async bulkUpdateJobApplications(payload: BulkJobApplicationUpdatePayload) {
    const { data } = await api.patch<{ updated_count: number }>(
      "/job-applications/bulk",
      payload
    );
    return data;
  },

  async getBulkJobApplicationLogs(bulkJobApplicationId: number) {
    const { data } = await api.get<{ items: BulkJobApplicationLog[] }>(
      `/job-applications/bulk/${bulkJobApplicationId}/logs`
    );
    return data;
  },

  async updateJobApplication(
    id: number,
    payload: JobApplicationUpdatePayload
  ) {
    const { data } = await api.put<JobApplication>(
      `/job-applications/${id}`,
      payload
    );
    return data;
  },

  async sendJobApplicationEmail(id: number) {
    const { data } = await api.post<JobApplication>(
      `/job-applications/${id}/send-email`
    );
    return data;
  },

  async getJobApplicationEmailLogs(id: number) {
    const { data } = await api.get<EmailLog[]>(
      `/job-applications/${id}/email-logs`
    );
    return data;
  },

  async fetchJobApplicationsForBulkEmail(
    date: string,
    minSimilarityScore: number,
    skip: number,
    limit: number
  ) {
    const { data } = await api.get<PaginatedResponse<JobApplication>>(
      "/job-applications/bulk-email/fetch",
      {
        params: {
          date,
          min_similarity_score: minSimilarityScore,
          skip,
          limit,
        },
      }
    );
    return data;
  },

  async bulkSendJobApplicationEmails(jobApplicationIds: number[]) {
    const { data } = await api.post<{ id: number; status: string }>(
      "/job-applications/bulk-email/send",
      { job_application_ids: jobApplicationIds }
    );
    return data;
  },

  async getBulkJobApplicationEmailSendLogs(bulkId: number) {
    const { data } = await api.get<{
      items: BulkJobApplicationEmailSendLog[];
    }>(`/job-applications/bulk-email/${bulkId}/logs`);
    return data;
  },
};
