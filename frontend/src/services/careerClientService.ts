import api from "./api";
import { CareerClient, PaginatedResponse } from "@/types";

export const careerClientService = {
  async getCareerClients(skip = 0, limit = 20) {
    const { data } = await api.get<PaginatedResponse<CareerClient>>(
      "/career-clients",
      { params: { skip, limit } }
    );
    return data;
  },
};
