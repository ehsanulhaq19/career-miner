import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { jobSiteService } from "@/services/jobSiteService";
import { JobSite } from "@/types";

interface JobSiteState {
  items: JobSite[];
  total: number;
  loading: boolean;
  error: string | null;
  current: JobSite | null;
}

const initialState: JobSiteState = {
  items: [],
  total: 0,
  loading: false,
  error: null,
  current: null,
};

export const fetchJobSites = createAsyncThunk(
  "jobSite/fetchAll",
  async (
    params: { skip?: number; limit?: number; is_active?: boolean } | undefined,
    { rejectWithValue }
  ) => {
    try {
      return await jobSiteService.getJobSites(params);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch job sites"
      );
    }
  }
);

export const fetchJobSite = createAsyncThunk(
  "jobSite/fetchOne",
  async (id: number, { rejectWithValue }) => {
    try {
      return await jobSiteService.getJobSite(id);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch job site"
      );
    }
  }
);

export const addJobSite = createAsyncThunk(
  "jobSite/add",
  async (data: Partial<JobSite>, { rejectWithValue }) => {
    try {
      return await jobSiteService.createJobSite(data);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to create job site"
      );
    }
  }
);

export const editJobSite = createAsyncThunk(
  "jobSite/edit",
  async (
    { id, data }: { id: number; data: Partial<JobSite> },
    { rejectWithValue }
  ) => {
    try {
      return await jobSiteService.updateJobSite(id, data);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to update job site"
      );
    }
  }
);

export const removeJobSite = createAsyncThunk(
  "jobSite/remove",
  async (id: number, { rejectWithValue }) => {
    try {
      await jobSiteService.deleteJobSite(id);
      return id;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to delete job site"
      );
    }
  }
);

const jobSiteSlice = createSlice({
  name: "jobSite",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchJobSites.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchJobSites.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
      })
      .addCase(fetchJobSites.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchJobSite.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchJobSite.fulfilled, (state, action) => {
        state.loading = false;
        state.current = action.payload;
      })
      .addCase(fetchJobSite.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(addJobSite.fulfilled, (state, action) => {
        state.items.push(action.payload);
        state.total += 1;
      })
      .addCase(editJobSite.fulfilled, (state, action) => {
        const index = state.items.findIndex(
          (item) => item.id === action.payload.id
        );
        if (index !== -1) {
          state.items[index] = action.payload;
        }
        if (state.current?.id === action.payload.id) {
          state.current = action.payload;
        }
      })
      .addCase(removeJobSite.fulfilled, (state, action) => {
        state.items = state.items.filter((item) => item.id !== action.payload);
        state.total -= 1;
      });
  },
});

export default jobSiteSlice.reducer;
