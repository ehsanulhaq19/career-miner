import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { scrapClientService } from "@/services/scrapClientService";
import { ScrapClientJob, ScrapClientLog } from "@/types";

interface ScrapClientState {
  items: ScrapClientJob[];
  total: number;
  loading: boolean;
  error: string | null;
  logsByJobId: Record<number, ScrapClientLog[]>;
  logsLoading: boolean;
  status: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  } | null;
}

const initialState: ScrapClientState = {
  items: [],
  total: 0,
  loading: false,
  error: null,
  logsByJobId: {},
  logsLoading: false,
  status: null,
};

export const fetchScrapClientJobs = createAsyncThunk(
  "scrapClient/fetchAll",
  async (
    params?: {
      skip?: number;
      limit?: number;
      status?: string;
    },
    { rejectWithValue }
  ) => {
    try {
      return await scrapClientService.getScrapClientJobs(params);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch scrap client jobs"
      );
    }
  }
);

export const startScrapClientJob = createAsyncThunk(
  "scrapClient/start",
  async (
    params: {
      client_ids?: number[] | null;
      only_clients_without_emails?: boolean;
    },
    { rejectWithValue }
  ) => {
    try {
      return await scrapClientService.startScrapClientJob(params);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to start scrap client job"
      );
    }
  }
);

export const testScrapClientJob = createAsyncThunk(
  "scrapClient/test",
  async (
    params: {
      client_ids?: number[];
      only_clients_without_emails?: boolean;
      url?: string | null;
    },
    { rejectWithValue }
  ) => {
    try {
      return await scrapClientService.testScrapClientJob(params);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to start test scrap client job"
      );
    }
  }
);

export const stopScrapClientJob = createAsyncThunk(
  "scrapClient/stop",
  async (id: number, { rejectWithValue }) => {
    try {
      return await scrapClientService.stopScrapClientJob(id);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to stop scrap client job"
      );
    }
  }
);

export const resumeScrapClientJob = createAsyncThunk(
  "scrapClient/resume",
  async (id: number, { rejectWithValue }) => {
    try {
      return await scrapClientService.resumeScrapClientJob(id);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to resume scrap client job"
      );
    }
  }
);

export const fetchScrapClientStatus = createAsyncThunk(
  "scrapClient/fetchStatus",
  async (_, { rejectWithValue }) => {
    try {
      return await scrapClientService.getScrapClientStatus();
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch status"
      );
    }
  }
);

export const fetchScrapClientLogs = createAsyncThunk(
  "scrapClient/fetchLogs",
  async (scrapClientJobId: number, { rejectWithValue }) => {
    try {
      const data = await scrapClientService.getScrapClientLogs(scrapClientJobId);
      return { scrapClientJobId, logs: data.items };
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch scrap client logs"
      );
    }
  }
);

const scrapClientSlice = createSlice({
  name: "scrapClient",
  initialState,
  reducers: {
    updateScrapClientJobFromSocket(
      state,
      action: { payload: ScrapClientJob }
    ) {
      const index = state.items.findIndex(
        (item) => item.id === action.payload.id
      );
      if (index !== -1) {
        state.items[index] = action.payload;
      } else {
        state.items.unshift(action.payload);
        state.total += 1;
      }
    },
    addScrapClientLogFromSocket(state, action: { payload: ScrapClientLog }) {
      const log = action.payload;
      const jobId = log.scrap_client_job_id;
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
      .addCase(fetchScrapClientJobs.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchScrapClientJobs.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
      })
      .addCase(fetchScrapClientJobs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(startScrapClientJob.fulfilled, (state, action) => {
        const exists = state.items.some(
          (item) => item.id === action.payload.id
        );
        if (!exists) {
          state.items.unshift(action.payload);
          state.total += 1;
        }
      })
      .addCase(testScrapClientJob.fulfilled, (state, action) => {
        const exists = state.items.some(
          (item) => item.id === action.payload.id
        );
        if (!exists) {
          state.items.unshift(action.payload);
          state.total += 1;
        }
      })
      .addCase(stopScrapClientJob.fulfilled, (state, action) => {
        const index = state.items.findIndex(
          (item) => item.id === action.payload.id
        );
        if (index !== -1) {
          state.items[index] = action.payload;
        }
      })
      .addCase(resumeScrapClientJob.fulfilled, (state, action) => {
        const index = state.items.findIndex(
          (item) => item.id === action.payload.id
        );
        if (index !== -1) {
          state.items[index] = action.payload;
        }
      })
      .addCase(fetchScrapClientStatus.fulfilled, (state, action) => {
        state.status = action.payload;
      })
      .addCase(fetchScrapClientLogs.pending, (state) => {
        state.logsLoading = true;
      })
      .addCase(fetchScrapClientLogs.fulfilled, (state, action) => {
        state.logsLoading = false;
        const existing = state.logsByJobId[action.payload.scrapClientJobId] || [];
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
        state.logsByJobId[action.payload.scrapClientJobId] = merged;
      })
      .addCase(fetchScrapClientLogs.rejected, (state) => {
        state.logsLoading = false;
      });
  },
});

export const {
  updateScrapClientJobFromSocket,
  addScrapClientLogFromSocket,
} = scrapClientSlice.actions;
export default scrapClientSlice.reducer;
