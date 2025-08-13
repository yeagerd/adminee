"use client";

import { useEffect, useMemo, useState } from "react";

type PageProps = {
  params: { token: string };
};

export default function PublicBookingPage({ params }: PageProps) {
  const { token } = params;
  const [timezone, setTimezone] = useState<string>(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  );

  const durationOptions = useMemo(() => [15, 30, 60, 120], []);
  const [duration, setDuration] = useState<number>(30);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<any | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);
    fetch(`/api/v1/bookings/public/${token}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("Link not found or expired");
        }
        return res.json();
      })
      .then((data) => {
        if (!isMounted) return;
        setMeta(data?.data ?? null);
      })
      .catch((e) => {
        if (!isMounted) return;
        setError(e?.message || "Unable to load booking link");
      })
      .finally(() => {
        if (!isMounted) return;
        setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [token]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">Public Booking</h1>
      <p className="text-sm text-muted-foreground mb-4">Token: {token}</p>

      {loading && <p className="text-sm">Loading…</p>}
      {!loading && error && (
        <div className="border border-red-200 bg-red-50 text-red-700 p-3 rounded mb-4">
          {error}
        </div>
      )}
      {!loading && !error && !meta && (
        <div className="border bg-yellow-50 text-yellow-800 p-3 rounded mb-4">
          Link not found.
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Meeting duration</label>
          <select
            className="border rounded px-2 py-1"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
          >
            {durationOptions.map((d) => (
              <option key={d} value={d}>
                {d} minutes
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Your timezone</label>
          <input
            className="border rounded px-2 py-1 w-full"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
          />
          <p className="text-xs text-muted-foreground mt-1">
            Detected automatically. Adjust if needed.
          </p>
        </div>
      </div>
    </div>
  );
}


