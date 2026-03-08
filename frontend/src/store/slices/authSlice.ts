import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { authService } from "@/services/authService";
import { AuthState } from "@/types";
import Cookies from "js-cookie";

const initialState: AuthState = {
  user: null,
  token: typeof window !== "undefined" ? Cookies.get("token") || null : null,
  loading: false,
  error: null,
};

export const loginUser = createAsyncThunk(
  "auth/login",
  async (
    { email, password }: { email: string; password: string },
    { dispatch, rejectWithValue }
  ) => {
    try {
      const { access_token } = await authService.login(email, password);
      Cookies.set("token", access_token, { expires: 7 });
      await dispatch(fetchCurrentUser());
      return access_token;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Login failed"
      );
    }
  }
);

export const registerUser = createAsyncThunk(
  "auth/register",
  async (
    data: {
      first_name: string;
      last_name: string;
      email: string;
      password: string;
    },
    { rejectWithValue }
  ) => {
    try {
      return await authService.register(data);
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Registration failed"
      );
    }
  }
);

export const fetchCurrentUser = createAsyncThunk(
  "auth/fetchCurrentUser",
  async (_, { rejectWithValue }) => {
    try {
      return await authService.getMe();
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.detail || "Failed to fetch user"
      );
    }
  }
);

export const logoutUser = createAsyncThunk("auth/logout", async () => {
  Cookies.remove("token");
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false;
        state.token = action.payload;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(registerUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchCurrentUser.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
      })
      .addCase(fetchCurrentUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null;
        state.token = null;
        state.loading = false;
        state.error = null;
      });
  },
});

export const { clearError } = authSlice.actions;
export default authSlice.reducer;
