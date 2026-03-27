import api from "./api";
import type { PaginatedResponse } from "@/types";

export interface WorkflowTaskInputPayload {
  linked_task_model: string;
  linked_task_model_data: Record<string, unknown>;
  priority: number;
  is_active: boolean;
}

export interface Workflow {
  id: number;
  name: string;
  next_execution_duration_minutes: number;
  user_id?: number;
  is_active: boolean;
  meta_data: Record<string, unknown>;
  last_execution_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTask extends WorkflowTaskInputPayload {
  id: number;
  workflow_id: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends Workflow {
  tasks: WorkflowTask[];
  total_jobs_executed: number;
  last_execution_started_at: string | null;
}

export interface WorkflowExecution {
  id: number;
  workflow_id: number;
  user_id?: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  meta_data: Record<string, unknown>;
  created_at: string;
}

export interface WorkflowJob {
  id: number;
  workflow_execution_id: number;
  workflow_task_id: number;
  status: string;
  created_resource_type: string | null;
  created_resource_id: number | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  meta_data: Record<string, unknown>;
}

export interface WorkflowLog {
  id: number;
  workflow_job_id: number;
  action: string;
  detail: string | null;
  meta_data: Record<string, unknown>;
  created_at: string;
}

export interface WorkflowExecutionDetail extends WorkflowExecution {
  workflow_name: string | null;
  jobs: WorkflowJob[];
  logs_by_job_id: Record<string, WorkflowLog[]>;
}

export interface WorkflowCreatePayload {
  name: string;
  next_execution_duration_minutes: number;
  is_active: boolean;
  meta_data: Record<string, unknown>;
  tasks: WorkflowTaskInputPayload[];
}

export interface WorkflowUpdatePayload {
  name?: string;
  next_execution_duration_minutes?: number;
  is_active?: boolean;
  meta_data?: Record<string, unknown>;
}

export interface WorkflowTaskUpdatePayload {
  linked_task_model?: string;
  linked_task_model_data?: Record<string, unknown>;
  priority?: number;
  is_active?: boolean;
}

export const workflowService = {
  async getWorkflows(params?: { skip?: number; limit?: number }) {
    const { data } = await api.get<PaginatedResponse<Workflow>>("/workflows/", {
      params,
    });
    return data;
  },

  async getWorkflowExecutions(params?: { skip?: number; limit?: number }) {
    const { data } = await api.get<PaginatedResponse<WorkflowExecution>>(
      "/workflows/executions",
      { params }
    );
    return data;
  },

  async getWorkflowDetail(id: number) {
    const { data } = await api.get<WorkflowDetail>(`/workflows/${id}`);
    return data;
  },

  async getWorkflowExecutionDetail(id: number) {
    const { data } = await api.get<WorkflowExecutionDetail>(
      `/workflows/executions/${id}`
    );
    return data;
  },

  async createWorkflow(payload: WorkflowCreatePayload) {
    const { data } = await api.post<WorkflowDetail>("/workflows/", payload);
    return data;
  },

  async updateWorkflow(id: number, payload: WorkflowUpdatePayload) {
    const { data } = await api.patch<WorkflowDetail>(`/workflows/${id}`, payload);
    return data;
  },

  async deleteWorkflowTask(workflowId: number, taskId: number) {
    await api.delete(`/workflows/${workflowId}/tasks/${taskId}`);
  },

  async patchWorkflowTask(
    workflowId: number,
    taskId: number,
    payload: WorkflowTaskUpdatePayload
  ) {
    const { data } = await api.patch<WorkflowTask>(
      `/workflows/${workflowId}/tasks/${taskId}`,
      payload
    );
    return data;
  },

  async runWorkflow(id: number) {
    const { data } = await api.post<{ status: string; workflow_id: number }>(
      `/workflows/${id}/run`
    );
    return data;
  },
};
