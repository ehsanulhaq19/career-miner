import api from "./api";
import { CareerJob, PaginatedResponse } from "@/types";

export const careerJobService = {
  async getCareerJobs(params?: {
    skip?: number;
    limit?: number;
    job_site_id?: number;
    category?: string;
    search?: string;
  }) {
    const { data } = await api.get<PaginatedResponse<CareerJob>>(
      "/career-jobs",
      { params }
    );
    return data;
  },

  async getCareerJob(id: number) {
    const { data } = await api.get<CareerJob>(`/career-jobs/${id}`);
    return data;
  },
};
