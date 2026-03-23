import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { clientSiteService } from "@/services/clientSiteService";
import { ClientSite } from "@/types";

interface ClientSiteState {
  items: ClientSite[];
  total: number;
  loading: boolean;
  error: string | null;
  current: ClientSite | null;
}

const initialState: ClientSiteState = {
  items: [],
  total: 0,
  loading: false,
  error: null,
  current: null,
};

export const fetchClientSites = createAsyncThunk(
  "clientSite/fetchAll",
  async (
    params: { skip?: number; limit?: number; is_active?: boolean } | undefined,
    { rejectWithValue }
  ) => {
    try {
      return await clientSiteService.getClientSites(params);
    } catch (error: unknown) {
      return rejectWithValue(
        (error as { response?: { data?: { detail?: string } } })?.response
          ?.data?.detail || "Failed to fetch client sites"
      );
    }
  }
);

export const fetchClientSite = createAsyncThunk(
  "clientSite/fetchOne",
  async (id: number, { rejectWithValue }) => {
    try {
      return await clientSiteService.getClientSite(id);
    } catch (error: unknown) {
      return rejectWithValue(
        (error as { response?: { data?: { detail?: string } } })?.response
          ?.data?.detail || "Failed to fetch client site"
      );
    }
  }
);

export const addClientSite = createAsyncThunk(
  "clientSite/add",
  async (data: Partial<ClientSite>, { rejectWithValue }) => {
    try {
      return await clientSiteService.createClientSite(data);
    } catch (error: unknown) {
      return rejectWithValue(
        (error as { response?: { data?: { detail?: string } } })?.response
          ?.data?.detail || "Failed to create client site"
      );
    }
  }
);

export const editClientSite = createAsyncThunk(
  "clientSite/edit",
  async (
    { id, data }: { id: number; data: Partial<ClientSite> },
    { rejectWithValue }
  ) => {
    try {
      return await clientSiteService.updateClientSite(id, data);
    } catch (error: unknown) {
      return rejectWithValue(
        (error as { response?: { data?: { detail?: string } } })?.response
          ?.data?.detail || "Failed to update client site"
      );
    }
  }
);

export const removeClientSite = createAsyncThunk(
  "clientSite/remove",
  async (id: number, { rejectWithValue }) => {
    try {
      await clientSiteService.deleteClientSite(id);
      return id;
    } catch (error: unknown) {
      return rejectWithValue(
        (error as { response?: { data?: { detail?: string } } })?.response
          ?.data?.detail || "Failed to delete client site"
      );
    }
  }
);

const clientSiteSlice = createSlice({
  name: "clientSite",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchClientSites.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchClientSites.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
      })
      .addCase(fetchClientSites.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchClientSite.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchClientSite.fulfilled, (state, action) => {
        state.loading = false;
        state.current = action.payload;
      })
      .addCase(fetchClientSite.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(addClientSite.fulfilled, (state, action) => {
        state.items.push(action.payload);
        state.total += 1;
      })
      .addCase(editClientSite.fulfilled, (state, action) => {
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
      .addCase(removeClientSite.fulfilled, (state, action) => {
        state.items = state.items.filter((item) => item.id !== action.payload);
        state.total -= 1;
      });
  },
});

export default clientSiteSlice.reducer;
