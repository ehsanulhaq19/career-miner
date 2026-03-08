import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { careerJobService } from "@/services/careerJobService";
import { CareerJob } from "@/types";

interface CareerJobFilters {
  job_site_id?: number;
  category?: string;
  search?: string;
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
  filters: {},
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
      });
  },
});

export const { setFilters, clearFilters, setPage } = careerJobSlice.actions;
export default careerJobSlice.reducer;
