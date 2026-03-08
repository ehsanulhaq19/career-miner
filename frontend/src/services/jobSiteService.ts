import api from "./api";
import { JobSite, PaginatedResponse } from "@/types";

export const jobSiteService = {
  async getJobSites(params?: {
    skip?: number;
    limit?: number;
    is_active?: boolean;
  }) {
    const { data } = await api.get<PaginatedResponse<JobSite>>("/job-sites", {
      params,
    });
    return data;
  },

  async getJobSite(id: number) {
    const { data } = await api.get<JobSite>(`/job-sites/${id}`);
    return data;
  },

  async createJobSite(payload: Partial<JobSite>) {
    const { data } = await api.post<JobSite>("/job-sites", payload);
    return data;
  },

  async updateJobSite(id: number, payload: Partial<JobSite>) {
    const { data } = await api.put<JobSite>(`/job-sites/${id}`, payload);
    return data;
  },

  async deleteJobSite(id: number) {
    await api.delete(`/job-sites/${id}`);
  },
};
