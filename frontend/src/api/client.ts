import axios from "axios";
import { userManager } from "../auth/oidcConfig";
import type { ApiError } from "./types";

export const apiClient = axios.create({
  baseURL: "/api/v1",
});

apiClient.interceptors.request.use(async (config) => {
  const user = userManager ? await userManager.getUser() : null;
  if (user && !user.expired) {
    config.headers.Authorization = `Bearer ${user.access_token}`;
  }
  return config;
});

let redirectingToLogin = false;

apiClient.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (body && typeof body === "object" && "data" in body) {
      response.data = "pagination" in body ? { items: body.data, pagination: body.pagination } : body.data;
    }
    return response;
  },
  async (error) => {
    const apiError: ApiError | undefined = error.response?.data?.error;
    if (apiError) {
      error.apiError = apiError;
    }
    if (error.response?.status === 401 && !redirectingToLogin) {
      redirectingToLogin = true;
      if (userManager) {
        await userManager.removeUser();
      }
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
