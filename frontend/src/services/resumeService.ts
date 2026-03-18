import api from "./api";
import { PaginatedResponse, Resume } from "@/types";

export interface ResumeUpdatePayload {
  is_active?: boolean;
}

export const resumeService = {
  async uploadResume(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await api.post<Resume>("/resumes", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return data;
  },
  async getResumes(skip = 0, limit = 20, name?: string) {
    const params: Record<string, string | number> = { skip, limit };
    if (name && name.trim()) {
      params.name = name.trim();
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
