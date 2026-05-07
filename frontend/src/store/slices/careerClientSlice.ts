import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { careerClientService } from "@/services/careerClientService";
import { CareerClient } from "@/types";

export type ClientListFilter =
  | "all"
  | "with_email"
  | "without_email"
  | "scrape_failed"
  | "scrape_ok";

export type SourceFilter = "all" | "with_source";

interface CareerClientState {
  items: CareerClient[];
  total: number;
  page: number;
  limit: number;
  listFilter: ClientListFilter;
  sourceFilter: SourceFilter;
  loading: boolean;
  error: string | null;
}

const initialState: CareerClientState = {
  items: [],
  total: 0,
  page: 1,
  limit: 20,
  listFilter: "all",
  sourceFilter: "all",
  loading: false,
  error: null,
};

function listFilterToQuery(f: ClientListFilter): {
  hasEmailInformation?: boolean;
  emailFoundError?: boolean;
} {
  switch (f) {
    case "with_email":
      return { hasEmailInformation: true };
    case "without_email":
      return { hasEmailInformation: false };
    case "scrape_failed":
      return { emailFoundError: true };
    case "scrape_ok":
      return { emailFoundError: false };
    default:
      return {};
  }
}

export const fetchCareerClients = createAsyncThunk(
  "careerClient/fetchAll",
  async (
    params: {
      skip?: number;
      limit?: number;
      listFilter?: ClientListFilter;
      sourceFilter?: SourceFilter;
    } = {},
    { rejectWithValue }
  ) => {
    try {
      const lf = params?.listFilter ?? "all";
      const sf = params?.sourceFilter ?? "all";
      const q = listFilterToQuery(lf);
      const hasImportSource =
        sf === "with_source" ? true : undefined;
      return await careerClientService.getCareerClients(
        params?.skip ?? 0,
        params?.limit ?? 20,
        q.hasEmailInformation,
        q.emailFoundError,
        hasImportSource
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
    setListFilter(state, action: PayloadAction<ClientListFilter>) {
      state.listFilter = action.payload;
    },
    setSourceFilter(state, action: PayloadAction<SourceFilter>) {
      state.sourceFilter = action.payload;
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

export const { setPage, setListFilter, setSourceFilter } =
  careerClientSlice.actions;
export default careerClientSlice.reducer;
