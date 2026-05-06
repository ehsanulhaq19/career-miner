import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import {
  workflowService,
  type Workflow,
  type WorkflowCreatePayload,
  type WorkflowDetail,
  type WorkflowExecution,
  type WorkflowExecutionDetail,
  type WorkflowTaskInputPayload,
  type WorkflowTaskUpdatePayload,
  type WorkflowUpdatePayload,
} from "@/services/workflowService";

interface WorkflowState {
  items: Workflow[];
  executions: WorkflowExecution[];
  totalWorkflows: number;
  totalExecutions: number;
  loading: boolean;
  loadingExecutions: boolean;
  detailLoading: boolean;
  executionDetailLoading: boolean;
  error: string | null;
  workflowDetail: WorkflowDetail | null;
  executionDetail: WorkflowExecutionDetail | null;
}

const initialState: WorkflowState = {
  items: [],
  executions: [],
  totalWorkflows: 0,
  totalExecutions: 0,
  loading: false,
  loadingExecutions: false,
  detailLoading: false,
  executionDetailLoading: false,
  error: null,
  workflowDetail: null,
  executionDetail: null,
};

function workflowToListRow(w: WorkflowDetail): Workflow {
  return {
    id: w.id,
    name: w.name,
    next_execution_duration_minutes: w.next_execution_duration_minutes,
    user_id: w.user_id,
    is_active: w.is_active,
    meta_data: w.meta_data ?? {},
    last_execution_at: w.last_execution_at,
    created_at: w.created_at,
    updated_at: w.updated_at,
  };
}

export const fetchWorkflows = createAsyncThunk(
  "workflow/fetchAll",
  async (
    params: { skip?: number; limit?: number } | undefined,
    { rejectWithValue }
  ) => {
    try {
      return await workflowService.getWorkflows(params);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to fetch workflows"
      );
    }
  }
);

export const fetchWorkflowExecutions = createAsyncThunk(
  "workflow/fetchExecutions",
  async (
    params: { skip?: number; limit?: number } | undefined,
    { rejectWithValue }
  ) => {
    try {
      return await workflowService.getWorkflowExecutions(params);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to fetch workflow executions"
      );
    }
  }
);

export const fetchWorkflowDetail = createAsyncThunk(
  "workflow/fetchDetail",
  async (id: number, { rejectWithValue }) => {
    try {
      return await workflowService.getWorkflowDetail(id);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to fetch workflow"
      );
    }
  }
);

export const fetchWorkflowExecutionDetail = createAsyncThunk(
  "workflow/fetchExecutionDetail",
  async (id: number, { rejectWithValue }) => {
    try {
      return await workflowService.getWorkflowExecutionDetail(id);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to fetch execution"
      );
    }
  }
);

export const createWorkflow = createAsyncThunk(
  "workflow/create",
  async (payload: WorkflowCreatePayload, { rejectWithValue }) => {
    try {
      return await workflowService.createWorkflow(payload);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to create workflow"
      );
    }
  }
);

export const updateWorkflow = createAsyncThunk(
  "workflow/update",
  async (
    { id, data }: { id: number; data: WorkflowUpdatePayload },
    { rejectWithValue }
  ) => {
    try {
      return await workflowService.updateWorkflow(id, data);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to update workflow"
      );
    }
  }
);

export const removeWorkflowTask = createAsyncThunk(
  "workflow/removeTask",
  async (
    { workflowId, taskId }: { workflowId: number; taskId: number },
    { rejectWithValue }
  ) => {
    try {
      await workflowService.deleteWorkflowTask(workflowId, taskId);
      return await workflowService.getWorkflowDetail(workflowId);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to delete task"
      );
    }
  }
);

export const patchWorkflowTask = createAsyncThunk(
  "workflow/patchTask",
  async (
    {
      workflowId,
      taskId,
      data,
    }: {
      workflowId: number;
      taskId: number;
      data: WorkflowTaskUpdatePayload;
    },
    { rejectWithValue }
  ) => {
    try {
      await workflowService.patchWorkflowTask(workflowId, taskId, data);
      return await workflowService.getWorkflowDetail(workflowId);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to update task"
      );
    }
  }
);

export const addWorkflowTask = createAsyncThunk(
  "workflow/addTask",
  async (
    {
      workflowId,
      data,
    }: {
      workflowId: number;
      data: WorkflowTaskInputPayload;
    },
    { rejectWithValue }
  ) => {
    try {
      await workflowService.addWorkflowTask(workflowId, data);
      return await workflowService.getWorkflowDetail(workflowId);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to add task"
      );
    }
  }
);

export const runWorkflow = createAsyncThunk(
  "workflow/run",
  async (id: number, { rejectWithValue }) => {
    try {
      return await workflowService.runWorkflow(id);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to start workflow run"
      );
    }
  }
);

export const runWorkflowFromPriority = createAsyncThunk(
  "workflow/runFromPriority",
  async (
    {
      workflowId,
      fromPriority,
      sourceExecutionId,
    }: {
      workflowId: number;
      fromPriority: number;
      sourceExecutionId?: number | null;
    },
    { rejectWithValue }
  ) => {
    try {
      return await workflowService.runWorkflowFromPriority(
        workflowId,
        fromPriority,
        sourceExecutionId
      );
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to start partial workflow run"
      );
    }
  }
);

export const resumeWorkflowExecution = createAsyncThunk(
  "workflow/resumeExecution",
  async (executionId: number, { rejectWithValue }) => {
    try {
      return await workflowService.resumeWorkflowExecution(executionId);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to resume workflow execution"
      );
    }
  }
);

const workflowSlice = createSlice({
  name: "workflow",
  initialState,
  reducers: {
    clearWorkflowDetail(state) {
      state.workflowDetail = null;
    },
    clearExecutionDetail(state) {
      state.executionDetail = null;
    },
    clearWorkflowError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchWorkflows.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchWorkflows.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.totalWorkflows = action.payload.total;
      })
      .addCase(fetchWorkflows.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchWorkflowExecutions.pending, (state) => {
        state.loadingExecutions = true;
        state.error = null;
      })
      .addCase(fetchWorkflowExecutions.fulfilled, (state, action) => {
        state.loadingExecutions = false;
        state.executions = action.payload.items;
        state.totalExecutions = action.payload.total;
      })
      .addCase(fetchWorkflowExecutions.rejected, (state, action) => {
        state.loadingExecutions = false;
        state.error = action.payload as string;
      })
      .addCase(fetchWorkflowDetail.pending, (state) => {
        state.detailLoading = true;
        state.error = null;
      })
      .addCase(fetchWorkflowDetail.fulfilled, (state, action) => {
        state.detailLoading = false;
        state.workflowDetail = action.payload;
      })
      .addCase(fetchWorkflowDetail.rejected, (state, action) => {
        state.detailLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchWorkflowExecutionDetail.pending, (state) => {
        state.executionDetailLoading = true;
        state.error = null;
      })
      .addCase(fetchWorkflowExecutionDetail.fulfilled, (state, action) => {
        state.executionDetailLoading = false;
        state.executionDetail = action.payload;
      })
      .addCase(fetchWorkflowExecutionDetail.rejected, (state, action) => {
        state.executionDetailLoading = false;
        state.error = action.payload as string;
      })
      .addCase(createWorkflow.fulfilled, (state, action) => {
        const row = workflowToListRow(action.payload);
        state.items.unshift(row);
        state.totalWorkflows += 1;
      })
      .addCase(createWorkflow.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(updateWorkflow.fulfilled, (state, action) => {
        const detail = action.payload;
        const idx = state.items.findIndex((i) => i.id === detail.id);
        if (idx !== -1) {
          state.items[idx] = workflowToListRow(detail);
        }
        if (state.workflowDetail?.id === detail.id) {
          state.workflowDetail = detail;
        }
      })
      .addCase(updateWorkflow.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(removeWorkflowTask.fulfilled, (state, action) => {
        state.workflowDetail = action.payload;
        const idx = state.items.findIndex((i) => i.id === action.payload.id);
        if (idx !== -1) {
          state.items[idx] = workflowToListRow(action.payload);
        }
      })
      .addCase(removeWorkflowTask.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(patchWorkflowTask.fulfilled, (state, action) => {
        state.workflowDetail = action.payload;
        const idx = state.items.findIndex((i) => i.id === action.payload.id);
        if (idx !== -1) {
          state.items[idx] = workflowToListRow(action.payload);
        }
      })
      .addCase(patchWorkflowTask.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(addWorkflowTask.fulfilled, (state, action) => {
        if (state.workflowDetail?.id === action.payload.id) {
          state.workflowDetail = action.payload;
        }
        const idx = state.items.findIndex((i) => i.id === action.payload.id);
        if (idx !== -1) {
          state.items[idx] = workflowToListRow(action.payload);
        }
      })
      .addCase(addWorkflowTask.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(runWorkflow.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(runWorkflowFromPriority.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      .addCase(resumeWorkflowExecution.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const {
  clearWorkflowDetail,
  clearExecutionDetail,
  clearWorkflowError,
} = workflowSlice.actions;
export default workflowSlice.reducer;
