import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { careerJobService } from "@/services/careerJobService";
import { CareerJob } from "@/types";

export const markJobSeen = createAsyncThunk(
  "careerJob/markSeen",
  async (careerJobId: number, { rejectWithValue }) => {
    try {
      await careerJobService.markJobSeen(careerJobId);
      return careerJobId;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to mark job as seen"
      );
    }
  }
);

export const markAllJobsSeen = createAsyncThunk(
  "careerJob/markAllSeen",
  async (_, { rejectWithValue }) => {
    try {
      return await careerJobService.markAllJobsSeen();
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to mark all jobs as seen"
      );
    }
  }
);

interface CareerJobFilters {
  job_site_id?: number;
  category?: string;
  search?: string;
  show_unseen_jobs?: boolean;
}

interface CareerJobState {
  items: CareerJob[];
  total: number;
  page: number;
  limit: number;
  loading: boolean;
  error: string | null;
  current: CareerJob | null;
  filters: CareerJobFilters;
}

const initialState: CareerJobState = {
  items: [],
  total: 0,
  page: 1,
  limit: 20,
  loading: false,
  error: null,
  current: null,
  filters: { show_unseen_jobs: true },
};

export const fetchCareerJobs = createAsyncThunk(
  "careerJob/fetchAll",
  async (
    params:
      | {
          skip?: number;
          limit?: number;
          job_site_id?: number;
          category?: string;
          search?: string;
        }
      | undefined,
    { rejectWithValue }
  ) => {
    try {
      return await careerJobService.getCareerJobs(params);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch career jobs"
      );
    }
  }
);

export const fetchCareerJob = createAsyncThunk(
  "careerJob/fetchOne",
  async (id: number, { rejectWithValue }) => {
    try {
      return await careerJobService.getCareerJob(id);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch career job"
      );
    }
  }
);

const careerJobSlice = createSlice({
  name: "careerJob",
  initialState,
  reducers: {
    setFilters(state, action: PayloadAction<CareerJobFilters>) {
      state.filters = { ...state.filters, ...action.payload };
      state.page = 1;
    },
    clearFilters(state) {
      state.filters = {};
      state.page = 1;
    },
    setPage(state, action: PayloadAction<number>) {
      state.page = action.payload;
    },
    setJobSeen(state, action: PayloadAction<number>) {
      const job = state.items.find((j) => j.id === action.payload);
      if (job) job.job_seen = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCareerJobs.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCareerJobs.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
        state.page = action.payload.page ?? state.page;
      })
      .addCase(fetchCareerJobs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchCareerJob.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCareerJob.fulfilled, (state, action) => {
        state.loading = false;
        state.current = action.payload;
      })
      .addCase(fetchCareerJob.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(markJobSeen.fulfilled, (state, action) => {
        const job = state.items.find((j) => j.id === action.payload);
        if (job) job.job_seen = true;
      })
      .addCase(markAllJobsSeen.fulfilled, (state) => {
        state.items.forEach((job) => {
          job.job_seen = true;
        });
      });
  },
});

export const { setFilters, clearFilters, setPage, setJobSeen } =
  careerJobSlice.actions;
export default careerJobSlice.reducer;
