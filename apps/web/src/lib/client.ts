import type { components } from "./api.generated";
export type Career = components["schemas"]["CareerView"];
export type EvidenceProfile = components["schemas"]["EvidenceProfileResponse"];
export type Job = components["schemas"]["Job"];
export type Application = components["schemas"]["Application"];
export type Claim = components["schemas"]["Claim"];
export type Evidence = components["schemas"]["EvidenceRecord"];
export type Assertion = components["schemas"]["Assertion"];

export class ApiFailure extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
  ) {
    super(
      status === 409
        ? "State changed or the operation conflicts. Reload and review the current records."
        : status === 404
          ? "No synthetic workspace exists yet."
          : "The local API is unavailable or rejected this command. No automatic retry was made.",
    );
  }
}
export async function api<T>(path: string, command?: object): Promise<T> {
  const response = await fetch(`/api/actual/${path}`, {
    method: command ? "POST" : "GET",
    cache: "no-store",
    credentials: "omit",
    headers: command ? { "Content-Type": "application/json" } : {},
    body: command ? JSON.stringify(command) : undefined,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiFailure(
      response.status,
      typeof error.error?.code === "string" ? error.error.code : "UNAVAILABLE",
    );
  }
  return response.json();
}
export function id(prefix: string) {
  return `${prefix}_${crypto.randomUUID().replaceAll("-", "")}`;
}
