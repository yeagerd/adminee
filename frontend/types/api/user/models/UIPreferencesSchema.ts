/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DateFormat } from './DateFormat';
import type { Language } from './Language';
import type { ThemeMode } from './ThemeMode';
import type { TimeFormat } from './TimeFormat';
/**
 * UI preferences schema.
 */
export type UIPreferencesSchema = {
    /**
     * Theme mode preference
     */
    theme?: ThemeMode;
    /**
     * Display language
     */
    language?: Language;
    /**
     * Date format preference
     */
    date_format?: DateFormat;
    /**
     * Time format preference
     */
    time_format?: TimeFormat;
    /**
     * Use compact UI layout
     */
    compact_mode?: boolean;
    /**
     * Show helpful tooltips
     */
    show_tooltips?: boolean;
    /**
     * Enable UI animations
     */
    animations_enabled?: boolean;
    /**
     * Keep sidebar expanded by default
     */
    sidebar_expanded?: boolean;
};

