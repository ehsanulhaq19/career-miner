import { createSlice } from "@reduxjs/toolkit";
import { BulkJobApplicationLog } from "@/types";

interface BulkJobApplicationState {
  logsByBulkId: Record<number, BulkJobApplicationLog[]>;
}

const initialState: BulkJobApplicationState = {
  logsByBulkId: {},
};

const bulkJobApplicationSlice = createSlice({
  name: "bulkJobApplication",
  initialState,
  reducers: {
    setBulkJobApplicationLogs(
      state,
      action: { payload: { bulkJobApplicationId: number; logs: BulkJobApplicationLog[] } }
    ) {
      const { bulkJobApplicationId, logs } = action.payload;
      state.logsByBulkId[bulkJobApplicationId] = logs;
    },
    addBulkJobApplicationLogFromSocket(
      state,
      action: { payload: BulkJobApplicationLog }
    ) {
      const log = action.payload;
      const bulkId = log.bulk_job_application_id;
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
  setBulkJobApplicationLogs,
  addBulkJobApplicationLogFromSocket,
} = bulkJobApplicationSlice.actions;
export default bulkJobApplicationSlice.reducer;
