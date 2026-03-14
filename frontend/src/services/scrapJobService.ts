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

  async startScrapJob(params: {
    job_site_id: number;
    load_more_on_scroll?: boolean;
    max_scroll?: number;
  }) {
    const { data } = await api.post<ScrapJob>("/scrap-jobs/start", params);
    return data;
  },

  async testScrapJob(params: {
    job_site_id: number;
    categories: string[];
    max_pages_per_scrap: number;
    process_with_llm: boolean;
    load_more_on_scroll?: boolean;
    max_scroll?: number;
  }) {
    const { data } = await api.post<ScrapJob>("/scrap-jobs/test", params);
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
