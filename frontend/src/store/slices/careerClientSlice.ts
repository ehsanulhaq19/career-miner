import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { careerClientService } from "@/services/careerClientService";
import { CareerClient } from "@/types";

interface CareerClientState {
  items: CareerClient[];
  total: number;
  page: number;
  limit: number;
  loading: boolean;
  error: string | null;
}

const initialState: CareerClientState = {
  items: [],
  total: 0,
  page: 1,
  limit: 20,
  loading: false,
  error: null,
};

export const fetchCareerClients = createAsyncThunk(
  "careerClient/fetchAll",
  async (
    params?: { skip?: number; limit?: number },
    { rejectWithValue }
  ) => {
    try {
      return await careerClientService.getCareerClients(
        params?.skip ?? 0,
        params?.limit ?? 20
      );
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch career clients"
      );
    }
  }
);

const careerClientSlice = createSlice({
  name: "careerClient",
  initialState,
  reducers: {
    setPage(state, action: PayloadAction<number>) {
      state.page = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCareerClients.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCareerClients.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
        state.page = action.payload.page ?? state.page;
      })
      .addCase(fetchCareerClients.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { setPage } = careerClientSlice.actions;
export default careerClientSlice.reducer;
