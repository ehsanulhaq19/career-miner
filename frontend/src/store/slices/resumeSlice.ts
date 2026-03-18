import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { resumeService } from "@/services/resumeService";
import { Resume } from "@/types";

interface ResumeState {
  items: Resume[];
  total: number;
  page: number;
  limit: number;
  nameFilter: string;
  loading: boolean;
  error: string | null;
}

const initialState: ResumeState = {
  items: [],
  total: 0,
  page: 1,
  limit: 20,
  nameFilter: "",
  loading: false,
  error: null,
};

export const fetchResumes = createAsyncThunk(
  "resume/fetchAll",
  async (
    params?: {
      skip?: number;
      limit?: number;
      name?: string;
    },
    { rejectWithValue }
  ) => {
    try {
      return await resumeService.getResumes(
        params?.skip ?? 0,
        params?.limit ?? 20,
        params?.name
      );
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Failed to fetch resumes"
      );
    }
  }
);

const resumeSlice = createSlice({
  name: "resume",
  initialState,
  reducers: {
    setPage(state, action: PayloadAction<number>) {
      state.page = action.payload;
    },
    setNameFilter(state, action: PayloadAction<string>) {
      state.nameFilter = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchResumes.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchResumes.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
        state.page = action.payload.page ?? state.page;
      })
      .addCase(fetchResumes.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { setPage, setNameFilter } = resumeSlice.actions;
export default resumeSlice.reducer;
