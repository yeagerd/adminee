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
    onFinish?: () => void; // called after successful parse on blur/enter (even if unchanged)
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

    // 2b) Number followed by a unit word starting with 'h' or 'm' (e.g., "1 hour", "90 minutes", "1.5 hours")
    const numberWord = s.match(/^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$/);
    if (numberWord) {
        const num = parseFloat(numberWord[1]);
        const unit = numberWord[2].toLowerCase();
        if (!(num > 0)) return null;
        if (unit.startsWith('h')) {
            return Math.round(num * 60);
        }
        if (unit.startsWith('m')) {
            return Math.round(num);
        }
    }

    // 2c) Two-part forms like "1 hour 30 minutes" or "1 h 30 m"
    const twoPart = s.match(/^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s+(\d+)\s*([a-zA-Z]+)$/);
    if (twoPart) {
        const firstVal = parseFloat(twoPart[1]);
        const firstUnit = twoPart[2].toLowerCase();
        const secondVal = parseInt(twoPart[3], 10);
        const secondUnit = twoPart[4].toLowerCase();
        if (!(firstVal >= 0) || !(secondVal >= 0)) return null;
        let minutes = 0;
        if (firstUnit.startsWith('h')) minutes += Math.round(firstVal * 60);
        else if (firstUnit.startsWith('m')) minutes += Math.round(firstVal);
        else return null;
        if (secondUnit.startsWith('h')) minutes += secondVal * 60;
        else if (secondUnit.startsWith('m')) minutes += secondVal;
        else return null;
        return minutes > 0 ? minutes : null;
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

function formatParsedHint(minutes: number | null): string | null {
    if (minutes == null) return null;
    if (minutes >= 60) {
        const hours = minutes / 60;
        const roundedHalf = Math.round(hours * 2) / 2;
        return `${roundedHalf} hour${roundedHalf === 1 ? "" : "s"} (${minutes} minute${minutes === 1 ? "" : "s"})`;
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
    onFinish,
}) => {
    const [text, setText] = useState<string>(String(valueMinutes || ""));
    const isFocusedRef = useRef(false);
    const [showError, setShowError] = useState(false);
    const suppressBlurCommitRef = useRef(false);

    // Keep internal text in sync when external value changes and input isn't focused
    useEffect(() => {
        if (!isFocusedRef.current) {
            setText(String(valueMinutes || ""));
        }
    }, [valueMinutes]);

    const parsedMinutes = useMemo(() => parseDurationInput(text), [text]);
    const hint = useMemo(() => formatParsedHint(parsedMinutes), [parsedMinutes]);

    const commitIfValid = () => {
        const minutes = parseDurationInput(text);
        if (minutes && minutes > 0) {
            setShowError(false);
            if (minutes !== valueMinutes) {
                onChangeMinutes(minutes);
            }
            onFinish?.();
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
                    if (suppressBlurCommitRef.current) {
                        suppressBlurCommitRef.current = false;
                        return;
                    }
                    const ok = commitIfValid();
                    if (!ok) setShowError(true);
                }}
                onKeyDown={(e) => {
                    if (e.key === "Enter") {
                        const ok = commitIfValid();
                        if (!ok) setShowError(true);
                        suppressBlurCommitRef.current = true;
                        (e.target as HTMLInputElement).blur();
                    } else if (e.key === "Escape") {
                        onCancel?.();
                        onFinish?.();
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


