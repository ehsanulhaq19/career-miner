import api from "./api";
import { User } from "@/types";

export const authService = {
  async login(email: string, password: string) {
    const { data } = await api.post<{ access_token: string }>("/auth/login", {
      email,
      password,
    });
    return data;
  },

  async register(payload: {
    first_name: string;
    last_name: string;
    email: string;
    password: string;
  }) {
    const { data } = await api.post<User>("/auth/register", payload);
    return data;
  },

  async forgotPassword(email: string) {
    const { data } = await api.post<{ message: string }>(
      "/auth/forgot-password",
      { email }
    );
    return data;
  },

  async getMe() {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },

  async updatePassword(payload: { current_password: string; new_password: string }) {
    const { data } = await api.put<{ message: string }>(
      "/auth/update-password",
      payload
    );
    return data;
  },
};
