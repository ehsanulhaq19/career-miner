import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { scrapJobService } from "@/services/scrapJobService";
import { ScrapJob } from "@/types";

interface ScrapJobState {
  items: ScrapJob[];
  total: number;
  loading: boolean;
  error: string | null;
}

const initialState: ScrapJobState = {
  items: [],
  total: 0,
  loading: false,
  error: null,
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
  async (job_site_id: number, { rejectWithValue }) => {
    try {
      return await scrapJobService.startScrapJob(job_site_id);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to start scrap job"
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
      });
  },
});

export const { updateScrapJobFromSocket } = scrapJobSlice.actions;
export default scrapJobSlice.reducer;
