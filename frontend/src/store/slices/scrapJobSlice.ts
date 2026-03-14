import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { scrapJobService } from "@/services/scrapJobService";
import { ScrapJob, ScrapJobLog } from "@/types";

interface ScrapJobState {
  items: ScrapJob[];
  total: number;
  loading: boolean;
  error: string | null;
  logsByJobId: Record<number, ScrapJobLog[]>;
  logsLoading: boolean;
}

const initialState: ScrapJobState = {
  items: [],
  total: 0,
  loading: false,
  error: null,
  logsByJobId: {},
  logsLoading: false,
};

export const fetchScrapJobs = createAsyncThunk(
  "scrapJob/fetchAll",
  async (
    params?: {
      skip?: number;
      limit?: number;
      job_site_id?: number;
      status?: string;
    },
    { rejectWithValue }
  ) => {
    try {
      return await scrapJobService.getScrapJobs(params);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch scrap jobs"
      );
    }
  }
);

export const startScrapJob = createAsyncThunk(
  "scrapJob/start",
  async (
    params: {
      job_site_id: number;
      load_more_on_scroll?: boolean;
      max_scroll?: number;
    },
    { rejectWithValue }
  ) => {
    try {
      return await scrapJobService.startScrapJob(params);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to start scrap job"
      );
    }
  }
);

export const testScrapJob = createAsyncThunk(
  "scrapJob/test",
  async (
    params: {
      job_site_id: number;
      categories: string[];
      max_pages_per_scrap: number;
      process_with_llm: boolean;
      load_more_on_scroll?: boolean;
      max_scroll?: number;
    },
    { rejectWithValue }
  ) => {
    try {
      return await scrapJobService.testScrapJob(params);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to start test scrap job"
      );
    }
  }
);

export const stopScrapJob = createAsyncThunk(
  "scrapJob/stop",
  async (id: number, { rejectWithValue }) => {
    try {
      return await scrapJobService.stopScrapJob(id);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to stop scrap job"
      );
    }
  }
);

export const resumeScrapJob = createAsyncThunk(
  "scrapJob/resume",
  async (id: number, { rejectWithValue }) => {
    try {
      return await scrapJobService.resumeScrapJob(id);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to resume scrap job"
      );
    }
  }
);

export const fetchScrapJobLogs = createAsyncThunk(
  "scrapJob/fetchLogs",
  async (scrapJobId: number, { rejectWithValue }) => {
    try {
      const data = await scrapJobService.getScrapJobLogs(scrapJobId);
      return { scrapJobId, logs: data.items };
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch scrap job logs"
      );
    }
  }
);

const scrapJobSlice = createSlice({
  name: "scrapJob",
  initialState,
  reducers: {
    updateScrapJobFromSocket(state, action: { payload: ScrapJob }) {
      const index = state.items.findIndex(
        (item) => item.id === action.payload.id
      );
      if (index !== -1) {
        state.items[index] = action.payload;
      }
    },
    addScrapJobLogFromSocket(state, action: { payload: ScrapJobLog }) {
      const log = action.payload;
      const jobId = log.scrap_job_id;
      if (!state.logsByJobId[jobId]) {
        state.logsByJobId[jobId] = [];
      }
      const existing = state.logsByJobId[jobId].find((l) => l.id === log.id);
      if (!existing) {
        const merged = [...state.logsByJobId[jobId], log];
        merged.sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
        state.logsByJobId[jobId] = merged;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchScrapJobs.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchScrapJobs.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
      })
      .addCase(fetchScrapJobs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(startScrapJob.fulfilled, (state, action) => {
        const exists = state.items.some(
          (item) => item.id === action.payload.id
        );
        if (!exists) {
          state.items.unshift(action.payload);
          state.total += 1;
        }
      })
      .addCase(testScrapJob.fulfilled, (state, action) => {
        const exists = state.items.some(
          (item) => item.id === action.payload.id
        );
        if (!exists) {
          state.items.unshift(action.payload);
          state.total += 1;
        }
      })
      .addCase(stopScrapJob.fulfilled, (state, action) => {
        const index = state.items.findIndex(
          (item) => item.id === action.payload.id
        );
        if (index !== -1) {
          state.items[index] = action.payload;
        }
      })
      .addCase(resumeScrapJob.fulfilled, (state, action) => {
        const index = state.items.findIndex(
          (item) => item.id === action.payload.id
        );
        if (index !== -1) {
          state.items[index] = action.payload;
        }
      })
      .addCase(fetchScrapJobLogs.pending, (state) => {
        state.logsLoading = true;
      })
      .addCase(fetchScrapJobLogs.fulfilled, (state, action) => {
        state.logsLoading = false;
        const existing = state.logsByJobId[action.payload.scrapJobId] || [];
        const fromApi = action.payload.logs;
        const seen = new Set(fromApi.map((l) => l.id));
        const merged = [...fromApi];
        for (const log of existing) {
          if (!seen.has(log.id)) {
            merged.push(log);
            seen.add(log.id);
          }
        }
        merged.sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
        state.logsByJobId[action.payload.scrapJobId] = merged;
      })
      .addCase(fetchScrapJobLogs.rejected, (state) => {
        state.logsLoading = false;
      });
  },
});

export const {
  updateScrapJobFromSocket,
  addScrapJobLogFromSocket,
} = scrapJobSlice.actions;
export default scrapJobSlice.reducer;
