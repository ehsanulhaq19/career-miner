import api from "./api";
import {
  CareerJob,
  CareerJobDateGroup,
  CareerJobWithApplicationCounts,
  PaginatedResponse,
} from "@/types";

export const careerJobService = {
  async getCareerJobs(params?: {
    skip?: number;
    limit?: number;
    job_site_id?: number;
    career_client_id?: number;
    category?: string;
    search?: string;
    show_unseen_jobs?: boolean;
    has_client_emails?: boolean;
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

  async getCareerJobDatesGrouped(skip = 0, limit = 50) {
    const { data } = await api.get<{
      items: CareerJobDateGroup[];
      total: number;
      page: number;
      limit: number;
    }>("/career-jobs/grouped-by-date", { params: { skip, limit } });
    return data;
  },

  async getCareerJobsByDate(
    date: string,
    skip = 0,
    limit = 50
  ) {
    const { data } = await api.get<{
      items: CareerJobWithApplicationCounts[];
      total: number;
      page: number;
      limit: number;
    }>("/career-jobs/by-date", { params: { date, skip, limit } });
    return data;
  },

  async markAllJobsSeen() {
    const { data } = await api.post<{ marked_count: number }>(
      "/career-jobs/mark-all-seen"
    );
    return data;
  },
};
