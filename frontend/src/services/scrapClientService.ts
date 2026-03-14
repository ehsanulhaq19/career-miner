import api from "./api";
import {
  PaginatedResponse,
  ScrapClientJob,
  ScrapClientLog,
} from "@/types";

export interface ScrapClientStatus {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export const scrapClientService = {
  async getScrapClientJobs(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }) {
    const { data } = await api.get<PaginatedResponse<ScrapClientJob>>(
      "/scrap-clients",
      { params }
    );
    return data;
  },

  async getScrapClientJob(id: number) {
    const { data } = await api.get<ScrapClientJob>(`/scrap-clients/${id}`);
    return data;
  },

  async startScrapClientJob(params: {
    client_ids?: number[] | null;
    only_clients_without_emails?: boolean;
  }) {
    const { data } = await api.post<ScrapClientJob>(
      "/scrap-clients/start",
      params
    );
    return data;
  },

  async testScrapClientJob(params: {
    client_ids?: number[];
    only_clients_without_emails?: boolean;
    url?: string | null;
  }) {
    const { data } = await api.post<ScrapClientJob>(
      "/scrap-clients/test",
      params
    );
    return data;
  },

  async stopScrapClientJob(id: number) {
    const { data } = await api.post<ScrapClientJob>(
      `/scrap-clients/${id}/stop`
    );
    return data;
  },

  async resumeScrapClientJob(id: number) {
    const { data } = await api.post<ScrapClientJob>(
      `/scrap-clients/${id}/resume`
    );
    return data;
  },

  async getScrapClientStatus() {
    const { data } = await api.get<ScrapClientStatus>(
      "/scrap-clients/status"
    );
    return data;
  },

  async getScrapClientLogs(scrapClientJobId: number) {
    const { data } = await api.get<{ items: ScrapClientLog[] }>(
      `/scrap-clients/${scrapClientJobId}/logs`
    );
    return data;
  },
};
