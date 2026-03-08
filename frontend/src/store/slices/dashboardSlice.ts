import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { dashboardService } from "@/services/dashboardService";
import { DashboardStats } from "@/types";

interface DashboardState {
  stats: DashboardStats | null;
  loading: boolean;
  error: string | null;
}

const initialState: DashboardState = {
  stats: null,
  loading: false,
  error: null,
};

export const fetchDashboardStats = createAsyncThunk(
  "dashboard/fetchStats",
  async (_, { rejectWithValue }) => {
    try {
      return await dashboardService.getDashboardStats();
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch dashboard stats"
      );
    }
  }
);

const dashboardSlice = createSlice({
  name: "dashboard",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboardStats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardStats.fulfilled, (state, action) => {
        state.loading = false;
        state.stats = action.payload;
      })
      .addCase(fetchDashboardStats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export default dashboardSlice.reducer;
