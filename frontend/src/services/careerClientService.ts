import api from "./api";
import { CareerClient, PaginatedResponse } from "@/types";

export const careerClientService = {
  async getCareerClients(
    skip = 0,
    limit = 20,
    hasEmailInformation?: boolean
  ) {
    const params: Record<string, string | number | boolean> = {
      skip,
      limit,
    };
    if (hasEmailInformation === true) {
      params.has_email_information = true;
    }
    const { data } = await api.get<PaginatedResponse<CareerClient>>(
      "/career-clients",
      { params }
    );
    return data;
  },
  async getCareerClientById(id: number) {
    const { data } = await api.get<CareerClient>(`/career-clients/${id}`);
    return data;
  },
};
