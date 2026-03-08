import { configureStore } from "@reduxjs/toolkit";
import { useDispatch, useSelector, TypedUseSelectorHook } from "react-redux";
import authReducer from "./slices/authSlice";
import themeReducer from "./slices/themeSlice";
import jobSiteReducer from "./slices/jobSiteSlice";
import careerJobReducer from "./slices/careerJobSlice";
import dashboardReducer from "./slices/dashboardSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    theme: themeReducer,
    jobSite: jobSiteReducer,
    careerJob: careerJobReducer,
    dashboard: dashboardReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
