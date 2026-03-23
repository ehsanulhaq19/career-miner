import api from "./api";
import { ClientSite, PaginatedResponse } from "@/types";

export const clientSiteService = {
  async getClientSites(params?: {
    skip?: number;
    limit?: number;
    is_active?: boolean;
  }) {
    const { data } = await api.get<PaginatedResponse<ClientSite>>(
      "/client-sites",
      { params }
    );
    return data;
  },

  async getClientSite(id: number) {
    const { data } = await api.get<ClientSite>(`/client-sites/${id}`);
    return data;
  },

  async createClientSite(payload: Partial<ClientSite>) {
    const { data } = await api.post<ClientSite>("/client-sites", payload);
    return data;
  },

  async updateClientSite(id: number, payload: Partial<ClientSite>) {
    const { data } = await api.put<ClientSite>(`/client-sites/${id}`, payload);
    return data;
  },

  async deleteClientSite(id: number) {
    await api.delete(`/client-sites/${id}`);
  },
};
