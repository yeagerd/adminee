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

  useEffect(() => {
    // Placeholder: will fetch metadata later from /api/v1/bookings/public/{token}
  }, [token]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">Public Booking</h1>
      <p className="text-sm text-muted-foreground mb-4">Token: {token}</p>

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


