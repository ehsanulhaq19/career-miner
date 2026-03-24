import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface ClientInvalidEmailRow {
  client_id: number;
  client_name: string;
  invalid_emails: string[];
}

export interface ClientEmailValidationProgress {
  current: number;
  total: number;
  client_id: number;
  client_name: string;
}

interface ClientEmailValidationState {
  status: "idle" | "running" | "completed" | "error";
  progress: ClientEmailValidationProgress | null;
  results: ClientInvalidEmailRow[] | null;
  error: string | null;
}

const initialState: ClientEmailValidationState = {
  status: "idle",
  progress: null,
  results: null,
  error: null,
};

const clientEmailValidationSlice = createSlice({
  name: "clientEmailValidation",
  initialState,
  reducers: {
    resetClientEmailValidation() {
      return initialState;
    },
    startClientEmailValidation(state) {
      state.status = "running";
      state.progress = null;
      state.results = null;
      state.error = null;
    },
    clientEmailValidationProgressFromSocket(
      state,
      action: PayloadAction<ClientEmailValidationProgress>
    ) {
      state.progress = action.payload;
    },
    clientEmailValidationCompletedFromSocket(
      state,
      action: PayloadAction<{ invalid_clients: ClientInvalidEmailRow[] }>
    ) {
      state.status = "completed";
      state.progress = null;
      state.results = action.payload.invalid_clients;
    },
    clientEmailValidationErrorFromSocket(
      state,
      action: PayloadAction<{ message: string }>
    ) {
      state.status = "error";
      state.progress = null;
      state.error = action.payload.message;
    },
    clientEmailValidationHttpError(
      state,
      action: PayloadAction<{ message: string }>
    ) {
      state.status = "error";
      state.progress = null;
      state.error = action.payload.message;
    },
  },
});

export const {
  resetClientEmailValidation,
  startClientEmailValidation,
  clientEmailValidationProgressFromSocket,
  clientEmailValidationCompletedFromSocket,
  clientEmailValidationErrorFromSocket,
  clientEmailValidationHttpError,
} = clientEmailValidationSlice.actions;
export default clientEmailValidationSlice.reducer;
