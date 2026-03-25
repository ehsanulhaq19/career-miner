import api from "./api";
import { CareerClient, PaginatedResponse } from "@/types";

export interface CareerClientUpdatePayload {
  emails?: string[];
  name?: string | null;
  official_website?: string | null;
  location?: string | null;
  link?: string | null;
  detail?: string | null;
  is_active?: boolean;
}

export interface CareerClientBulkUpdatePayload {
  is_active?: boolean;
}

export const careerClientService = {
  async getCareerClients(
    skip = 0,
    limit = 20,
    hasEmailInformation?: boolean | null,
    emailFoundError?: boolean | null
  ) {
    const params: Record<string, string | number | boolean> = {
      skip,
      limit,
    };
    if (hasEmailInformation === true) {
      params.has_email_information = true;
    } else if (hasEmailInformation === false) {
      params.has_email_information = false;
    }
    if (emailFoundError === true) {
      params.email_found_error = true;
    } else if (emailFoundError === false) {
      params.email_found_error = false;
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
  async updateCareerClient(id: number, payload: CareerClientUpdatePayload) {
    const { data } = await api.put<CareerClient>(
      `/career-clients/${id}`,
      payload
    );
    return data;
  },
  async getCareerClientLocations() {
    const { data } = await api.get<{ locations: string[] }>(
      "/career-clients/locations"
    );
    return data;
  },
  async bulkUpdateCareerClientsByLocation(
    location: string,
    payload: CareerClientBulkUpdatePayload
  ) {
    const { data } = await api.put<{ updated_count: number }>(
      "/career-clients/bulk-update/location",
      payload,
      { params: { location } }
    );
    return data;
  },
  async scanCareerClients(criteria: {
    min_description?: number | null;
    matching_words?: string | null;
  }) {
    const { data } = await api.post<{ deactivated_count: number }>(
      "/career-clients/scan",
      criteria
    );
    return data;
  },
  async validateClientEmails(params: {
    client_ids?: number[];
    all_clients?: boolean;
  }) {
    const { data } = await api.post<{ status: string }>(
      "/career-clients/validate-emails",
      params
    );
    return data;
  },
  async removeInvalidEmails(clients: {
    client_id: number;
    invalid_emails: string[];
  }[]) {
    const { data } = await api.post<{ updated_count: number }>(
      "/career-clients/remove-invalid-emails",
      { clients }
    );
    return data;
  },
};
