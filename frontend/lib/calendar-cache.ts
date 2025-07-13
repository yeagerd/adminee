import { CalendarEvent } from '@/types/office-service';

interface CachedCalendarData {
    events: CalendarEvent[];
    timestamp: number;
    providers: string[];
    dateRange: string;
    limit: number;
}

interface CacheEntry {
    data: CachedCalendarData;
    expiresAt: number;
}

class CalendarCache {
    private cache = new Map<string, CacheEntry>();
    private readonly DEFAULT_TTL = 10 * 60 * 1000; // 10 minutes in milliseconds

    private generateCacheKey(
        userId: string,
        providers: string[],
        dateRange: string,
        limit: number
    ): string {
        const sortedProviders = providers.sort().join(',');
        return `${userId}:${sortedProviders}:${dateRange}:${limit}`;
    }

    set(
        userId: string,
        providers: string[],
        dateRange: string,
        limit: number,
        events: CalendarEvent[],
        ttlMs: number = this.DEFAULT_TTL
    ): void {
        const key = this.generateCacheKey(userId, providers, dateRange, limit);
        const expiresAt = Date.now() + ttlMs;

        this.cache.set(key, {
            data: {
                events,
                timestamp: Date.now(),
                providers,
                dateRange,
                limit,
            },
            expiresAt,
        });

        // Clean up expired entries
        this.cleanup();
    }

    get(
        userId: string,
        providers: string[],
        dateRange: string,
        limit: number
    ): CalendarEvent[] | null {
        const key = this.generateCacheKey(userId, providers, dateRange, limit);
        const entry = this.cache.get(key);

        if (!entry) {
            return null;
        }

        if (Date.now() > entry.expiresAt) {
            this.cache.delete(key);
            return null;
        }

        return entry.data.events;
    }

    invalidate(userId: string): void {
        const keysToDelete: string[] = [];
        for (const key of this.cache.keys()) {
            if (key.startsWith(`${userId}:`)) {
                keysToDelete.push(key);
            }
        }
        keysToDelete.forEach(key => this.cache.delete(key));
    }

    clear(): void {
        this.cache.clear();
    }

    private cleanup(): void {
        const now = Date.now();
        const keysToDelete: string[] = [];

        for (const [key, entry] of this.cache.entries()) {
            if (now > entry.expiresAt) {
                keysToDelete.push(key);
            }
        }

        keysToDelete.forEach(key => this.cache.delete(key));
    }

    getStats(): { size: number; keys: string[] } {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys()),
        };
    }
}

// Export singleton instance
export const calendarCache = new CalendarCache(); 