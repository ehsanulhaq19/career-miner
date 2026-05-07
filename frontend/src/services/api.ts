import axios from "axios";
import Cookies from "js-cookie";

const basePath = (
  process.env.NEXT_PUBLIC_BASE_PATH ?? ""
)
  .trim()
  .replace(/\/+$/, "");

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
});

api.interceptors.request.use((config) => {
  const token = Cookies.get("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove("token");
      if (typeof window !== "undefined") {
        window.location.href = `${basePath}/login`;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
