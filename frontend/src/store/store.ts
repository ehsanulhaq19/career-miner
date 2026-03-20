import { configureStore } from "@reduxjs/toolkit";
import { useDispatch, useSelector, TypedUseSelectorHook } from "react-redux";
import authReducer from "./slices/authSlice";
import themeReducer from "./slices/themeSlice";
import jobSiteReducer from "./slices/jobSiteSlice";
import careerJobReducer from "./slices/careerJobSlice";
import careerClientReducer from "./slices/careerClientSlice";
import dashboardReducer from "./slices/dashboardSlice";
import scrapJobReducer from "./slices/scrapJobSlice";
import resumeReducer from "./slices/resumeSlice";
import scrapClientReducer from "./slices/scrapClientSlice";
import bulkJobApplicationReducer from "./slices/bulkJobApplicationSlice";
import bulkEmailSendReducer from "./slices/bulkEmailSendSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    theme: themeReducer,
    jobSite: jobSiteReducer,
    careerJob: careerJobReducer,
    careerClient: careerClientReducer,
    dashboard: dashboardReducer,
    resume: resumeReducer,
    scrapJob: scrapJobReducer,
    scrapClient: scrapClientReducer,
    bulkJobApplication: bulkJobApplicationReducer,
    bulkEmailSend: bulkEmailSendReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
