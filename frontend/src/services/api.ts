import axios, { AxiosInstance } from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
if (!BACKEND_URL) {
  // eslint-disable-next-line no-console
  console.warn("REACT_APP_BACKEND_URL is not set");
}

export const API_BASE = `${BACKEND_URL}/api`;

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

export interface ApiError {
  status: number;
  message: string;
}

export function toApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    return {
      status: err.response?.status ?? 0,
      message: detail || err.message || "Network error",
    };
  }
  return { status: 0, message: (err as Error)?.message ?? "Unexpected error" };
}
