"use client";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import React, { useEffect, useMemo, useRef, useState } from "react";

export interface SmartTimeDurationInputProps {
    valueMinutes: number;
    onChangeMinutes: (minutes: number) => void;
    placeholder?: string;
    className?: string; // wrapper
    inputClassName?: string; // input element
    autoFocus?: boolean;
    onCancel?: () => void; // e.g., Escape key to cancel edit
}

// Parse a human-friendly duration string into total minutes.
// Supported inputs:
// - HH:MM or H:MM
// - Xh, XhYm, Xh Y, decimal hours like 1.5h
// - Xm
// - Pure numbers: decimals -> hours, integers -> heuristic: >14 => minutes, else hours
export function parseDurationInput(raw: string): number | null {
    const s = raw.trim().toLowerCase();
    if (!s) return null;

    // 1) HH:MM
    const colon = s.match(/^(\d+):(\d{1,2})$/);
    if (colon) {
        const h = parseInt(colon[1], 10);
        const m = parseInt(colon[2], 10);
        if (!Number.isFinite(h) || !Number.isFinite(m) || m >= 60) return null;
        return h * 60 + m;
    }

    // 2) Xh (optional decimal) and optional Ym
    const hm = s.match(/^(\d+(?:\.\d+)?)h(?:\s*(\d+)\s*m?)?$/);
    if (hm) {
        const h = parseFloat(hm[1]);
        const m = hm[2] ? parseInt(hm[2], 10) : 0;
        if (!(h > 0) || m < 0 || m >= 60) return null;
        return Math.round(h * 60) + m;
    }

    // 3) Xm only
    const onlyM = s.match(/^(\d+)\s*m$/);
    if (onlyM) {
        const m = parseInt(onlyM[1], 10);
        return m > 0 ? m : null;
    }

    // 4) Pure number: decimal -> hours, integer -> heuristic
    if (/^\d+(\.\d+)?$/.test(s)) {
        const num = Number(s);
        if (!Number.isFinite(num) || num <= 0) return null;

        if (s.includes(".")) {
            return Math.round(num * 60);
        }

        // Integer heuristic
        if (num > 14) return num; // minutes
        return num * 60; // hours
    }

    return null;
}

function hasExplicitUnit(raw: string): boolean {
    return /\b[hm]/i.test(raw);
}

function formatAutoDetectHint(raw: string, minutes: number | null): string | null {
    if (!raw.trim()) return null;
    if (hasExplicitUnit(raw)) return null; // user already specified units
    if (minutes == null) return null;

    // Prefer simple phrasing: hours if >= 60 and minutes divisible by 30, else minutes
    if (minutes >= 60) {
        const hours = minutes / 60;
        const roundedHalf = Math.round(hours * 2) / 2;
        return `${roundedHalf} hour${roundedHalf === 1 ? "" : "s"}`;
    }
    return `${minutes} minute${minutes === 1 ? "" : "s"}`;
}

export const SmartTimeDurationInput: React.FC<SmartTimeDurationInputProps> = ({
    valueMinutes,
    onChangeMinutes,
    placeholder,
    className,
    inputClassName,
    autoFocus,
    onCancel,
}) => {
    const [text, setText] = useState<string>(String(valueMinutes || ""));
    const isFocusedRef = useRef(false);
    const [showError, setShowError] = useState(false);

    // Keep internal text in sync when external value changes and input isn't focused
    useEffect(() => {
        if (!isFocusedRef.current) {
            setText(String(valueMinutes || ""));
        }
    }, [valueMinutes]);

    const parsedMinutes = useMemo(() => parseDurationInput(text), [text]);
    const hint = useMemo(() => formatAutoDetectHint(text, parsedMinutes), [text, parsedMinutes]);

    const commitIfValid = () => {
        const minutes = parseDurationInput(text);
        if (minutes && minutes > 0) {
            setShowError(false);
            if (minutes !== valueMinutes) {
                onChangeMinutes(minutes);
            }
            return true;
        }
        return false;
    };

    return (
        <div className={cn("inline-flex items-center gap-2", className)}>
            <Input
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onFocus={() => {
                    isFocusedRef.current = true;
                    setShowError(false);
                }}
                onBlur={() => {
                    isFocusedRef.current = false;
                    const ok = commitIfValid();
                    if (!ok) setShowError(true);
                }}
                onKeyDown={(e) => {
                    if (e.key === "Enter") {
                        const ok = commitIfValid();
                        if (!ok) setShowError(true);
                        (e.target as HTMLInputElement).blur();
                    } else if (e.key === "Escape") {
                        onCancel?.();
                    }
                }}
                placeholder={placeholder ?? "e.g. 45, 1.5h, 1:30"}
                className={cn(
                    "w-24 h-7 px-2 py-1 text-sm",
                    showError && "border-destructive focus-visible:ring-destructive",
                    inputClassName
                )}
                autoFocus={autoFocus}
                inputMode="decimal"
            />
            {hint && (
                <span className="text-xs text-muted-foreground">{hint}</span>
            )}
        </div>
    );
};

export default SmartTimeDurationInput;


