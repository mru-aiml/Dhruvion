import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export const api = axios.create({
  baseURL,
  timeout: 15000,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { error?: { message?: string; code?: string } } | undefined;
    if (data?.error?.message) return data.error.message;
    if (err.response?.status === 0 || err.code === "ERR_NETWORK") return "Backend unavailable";
    return err.message;
  }
  return err instanceof Error ? err.message : "Unknown error";
}
