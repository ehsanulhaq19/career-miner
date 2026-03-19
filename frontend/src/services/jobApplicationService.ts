import api from "./api";
import {
  BulkJobApplicationLog,
  JobApplication,
  PaginatedResponse,
} from "@/types";

export interface CreateJobApplicationPayload {
  career_job_id: number;
  resume_id: number;
}

export interface BulkJobApplicationCreatePayload {
  resume_id: number;
  career_job_ids: number[];
}

export interface JobApplicationUpdatePayload {
  is_active?: boolean;
}

export const jobApplicationService = {
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

  async createBulkJobApplications(payload: BulkJobApplicationCreatePayload) {
    const { data } = await api.post<{ id: number; status: string }>(
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
};
