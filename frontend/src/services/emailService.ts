import api from "./api";

export interface JobEmailLogItem {
  id: number;
  subject: string;
  content: string | null;
  file_attachment: string | null;
  to_email: string;
  from_email: string | null;
  response: string | null;
  status: string;
  created_at: string;
  job_application_id: number;
  career_job_id: number;
  career_job_title: string;
  career_client_id: number | null;
  career_client_name: string | null;
}

export interface JobEmailLogDetail {
  id: number;
  subject: string;
  content: string | null;
  file_attachment: string | null;
  to_email: string;
  from_email: string | null;
  response: string | null;
  status: string;
  created_at: string;
  job_application: {
    id: number;
    application_name: string;
    subject: string | null;
    cover_letter: string | null;
    to_emails: string[];
  };
  career_job: {
    id: number;
    title: string;
    description: string | null;
    url: string | null;
  };
  career_client: {
    id: number;
    name: string | null;
    official_website: string | null;
    emails: string[];
  } | null;
}

export const emailService = {
  async getJobEmailLogs(params?: {
    skip?: number;
    limit?: number;
    career_client_id?: number;
    created_date_from?: string;
    created_date_to?: string;
    search?: string;
  }) {
    const { data } = await api.get<{
      items: JobEmailLogItem[];
      total: number;
      page: number;
      limit: number;
    }>("/email/job-logs", { params });
    return data;
  },

  async getJobEmailLogDetail(emailLogId: number) {
    const { data } = await api.get<JobEmailLogDetail>(
      `/email/job-logs/${emailLogId}`
    );
    return data;
  },

  async getAttachmentBlobUrl(emailLogId: number): Promise<string | null> {
    try {
      const { data } = await api.get(`/email/job-logs/${emailLogId}/attachment`, {
        responseType: "blob",
      });
      return URL.createObjectURL(data);
    } catch {
      return null;
    }
  },
};
