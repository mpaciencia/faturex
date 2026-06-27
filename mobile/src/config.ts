const trimTrailingSlash = (value: string) => value.trim().replace(/\/+$/, "");

export const FATUREX_API_BASE_URL = trimTrailingSlash(
  process.env.EXPO_PUBLIC_FATUREX_API_BASE_URL ?? "",
);

export const FATUREX_API_KEY = (process.env.EXPO_PUBLIC_FATUREX_API_KEY ?? "eac9da180d3a70482cd6d145fecabe4d").trim();

export const hasValidBackendConfig =
  FATUREX_API_BASE_URL.length > 0 && FATUREX_API_KEY.length > 0;

export const backendConfigIssues: string[] = [
  FATUREX_API_BASE_URL.length === 0
    ? "Definir EXPO_PUBLIC_FATUREX_API_BASE_URL."
    : "",
  FATUREX_API_KEY.length === 0 ? "Definir EXPO_PUBLIC_FATUREX_API_KEY." : "",
].filter(Boolean);
