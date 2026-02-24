"use client";
import { useState, useEffect } from "react";

export function useCsrfToken(backendUrl: string): string | null {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchToken = () =>
      fetch(`${backendUrl}/csrf/token`)
        .then(r => r.json())
        .then(data => { if (!cancelled) setToken(data.token); })
        .catch(() => {}); // never block the app

    fetchToken();
    // Refresh at 80% of TTL (240s) so token never expires mid-session
    const id = setInterval(fetchToken, 240_000);
    return () => { cancelled = true; clearInterval(id); };
  }, [backendUrl]);

  return token;
}
