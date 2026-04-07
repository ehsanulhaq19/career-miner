import api from "./api";
import { AnalyticsSummary } from "@/types";

export const analyticsService = {
  async getSummary(dateFrom?: string, dateTo?: string) {
    const params: Record<string, string> = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    const { data } = await api.get<AnalyticsSummary>("/analytics/summary", {
      params,
    });
    return data;
  },
};
