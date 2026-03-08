import api from "./api";
import { DashboardStats } from "@/types";

export const dashboardService = {
  async getDashboardStats() {
    const { data } = await api.get<DashboardStats>("/dashboard/stats");
    return data;
  },
};
