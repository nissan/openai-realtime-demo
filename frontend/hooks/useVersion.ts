"use client";
import { useSearchParams } from "next/navigation";

export type Version = "a" | "b";

export function useVersion(): Version {
  const searchParams = useSearchParams();
  return searchParams.get("v") === "b" ? "b" : "a";
}
