import api from "./api";
import { PaginatedResponse, Resume } from "@/types";

export interface ResumeUpdatePayload {
  is_active?: boolean;
  extra_detail?: string | null;
}

export const resumeService = {
  async uploadResume(file: File, extra_detail?: string | null) {
    const formData = new FormData();
    formData.append("file", file);
    if (extra_detail != null && extra_detail !== "") {
      formData.append("extra_detail", extra_detail);
    }
    const { data } = await api.post<Resume>("/resumes", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return data;
  },
  async getResumes(
    skip = 0,
    limit = 20,
    name?: string,
    is_active?: boolean
  ) {
    const params: Record<string, string | number | boolean> = { skip, limit };
    if (name && name.trim()) {
      params.name = name.trim();
    }
    if (is_active !== undefined) {
      params.is_active = is_active;
    }
    const { data } = await api.get<PaginatedResponse<Resume>>("/resumes", {
      params,
    });
    return data;
  },
  async getResumeById(id: number) {
    const { data } = await api.get<Resume>(`/resumes/${id}`);
    return data;
  },
  async getResumeFileBlobUrl(id: number): Promise<string> {
    const { data } = await api.get<Blob>(`/resumes/${id}/file`, {
      responseType: "blob",
    });
    return URL.createObjectURL(data);
  },
  async updateResume(id: number, payload: ResumeUpdatePayload) {
    const { data } = await api.put<Resume>(`/resumes/${id}`, payload);
    return data;
  },
};
