import { createSlice } from "@reduxjs/toolkit";
import { BulkJobApplicationEmailSendLog } from "@/types";

interface BulkEmailSendState {
  logsByBulkId: Record<number, BulkJobApplicationEmailSendLog[]>;
}

const initialState: BulkEmailSendState = {
  logsByBulkId: {},
};

const bulkEmailSendSlice = createSlice({
  name: "bulkEmailSend",
  initialState,
  reducers: {
    setBulkEmailSendLogs(
      state,
      action: { payload: { bulkId: number; logs: BulkJobApplicationEmailSendLog[] } }
    ) {
      const { bulkId, logs } = action.payload;
      state.logsByBulkId[bulkId] = logs;
    },
    addBulkEmailSendLogFromSocket(
      state,
      action: { payload: BulkJobApplicationEmailSendLog }
    ) {
      const log = action.payload;
      const bulkId = log.bulk_job_application_email_send_id;
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
  setBulkEmailSendLogs,
  addBulkEmailSendLogFromSocket,
} = bulkEmailSendSlice.actions;
export default bulkEmailSendSlice.reducer;
