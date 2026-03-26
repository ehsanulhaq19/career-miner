import { createSlice } from "@reduxjs/toolkit";
import { BulkCareerClientEmailSendLog } from "@/types";

interface BulkCareerClientEmailState {
  logsByBulkId: Record<number, BulkCareerClientEmailSendLog[]>;
}

const initialState: BulkCareerClientEmailState = {
  logsByBulkId: {},
};

const bulkCareerClientEmailSlice = createSlice({
  name: "bulkCareerClientEmail",
  initialState,
  reducers: {
    setBulkCareerClientEmailLogs(
      state,
      action: {
        payload: { bulkId: number; logs: BulkCareerClientEmailSendLog[] };
      }
    ) {
      const { bulkId, logs } = action.payload;
      state.logsByBulkId[bulkId] = logs;
    },
    addBulkCareerClientEmailLogFromSocket(
      state,
      action: { payload: BulkCareerClientEmailSendLog }
    ) {
      const log = action.payload;
      const bulkId = log.bulk_career_client_email_send_id;
      if (!state.logsByBulkId[bulkId]) {
        state.logsByBulkId[bulkId] = [];
      }
      const existing = state.logsByBulkId[bulkId].find((l) => l.id === log.id);
      if (!existing) {
        const merged = [...state.logsByBulkId[bulkId], log];
        merged.sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
        state.logsByBulkId[bulkId] = merged;
      }
    },
  },
});

export const {
  setBulkCareerClientEmailLogs,
  addBulkCareerClientEmailLogFromSocket,
} = bulkCareerClientEmailSlice.actions;
export default bulkCareerClientEmailSlice.reducer;
