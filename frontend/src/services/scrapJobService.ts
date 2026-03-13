import api from "./api";
import { PaginatedResponse, ScrapJob, ScrapJobLog } from "@/types";

export const scrapJobService = {
  async getScrapJobs(params?: {
    skip?: number;
    limit?: number;
    job_site_id?: number;
    status?: string;
  }) {
    const { data } = await api.get<PaginatedResponse<ScrapJob>>("/scrap-jobs", {
      params,
    });
    return data;
  },

  async getScrapJob(id: number) {
    const { data } = await api.get<ScrapJob>(`/scrap-jobs/${id}`);
    return data;
  },

  async startScrapJob(job_site_id: number) {
    const { data } = await api.post<ScrapJob>("/scrap-jobs/start", {
      job_site_id,
    });
    return data;
  },

  async stopScrapJob(id: number) {
    const { data } = await api.post<ScrapJob>(`/scrap-jobs/${id}/stop`);
    return data;
  },

  async resumeScrapJob(id: number) {
    const { data } = await api.post<ScrapJob>(`/scrap-jobs/${id}/resume`);
    return data;
  },

  async getScrapJobLogs(scrapJobId: number) {
    const { data } = await api.get<{ items: ScrapJobLog[] }>(
      `/scrap-jobs/${scrapJobId}/logs`
    );
    return data;
  },
};
