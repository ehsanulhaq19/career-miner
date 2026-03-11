import api from "./api";
import { CareerJob, PaginatedResponse } from "@/types";

export const careerJobService = {
  async getCareerJobs(params?: {
    skip?: number;
    limit?: number;
    job_site_id?: number;
    category?: string;
    search?: string;
    show_unseen_jobs?: boolean;
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

  async markJobSeen(careerJobId: number) {
    await api.post("/career-jobs/job-seen", { career_job_id: careerJobId });
  },

  async markAllJobsSeen() {
    const { data } = await api.post<{ marked_count: number }>(
      "/career-jobs/mark-all-seen"
    );
    return data;
  },
};
