import { CalendarEvent } from "@/types/api/office"';

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
    private readonly MAX_CACHE_SIZE = 1000; // Maximum number of cache entries
    private readonly CLEANUP_THRESHOLD = 0.8; // Cleanup when 80% full

    private generateCacheKey(
        userId: string,
        providers: string[],
        dateRange: string,
        limit: number
    ): string {
        // Validate inputs to prevent cache key collisions
        if (!userId || typeof userId !== 'string') {
            throw new Error('Invalid userId for cache key generation');
        }
        if (!Array.isArray(providers)) {
            throw new Error('Invalid providers array for cache key generation');
        }
        if (!dateRange || typeof dateRange !== 'string') {
            throw new Error('Invalid dateRange for cache key generation');
        }
        if (typeof limit !== 'number' || limit <= 0) {
            throw new Error('Invalid limit for cache key generation');
        }

        // Sanitize inputs to prevent injection attacks
        const sanitizedUserId = userId.replace(/[^a-zA-Z0-9_-]/g, '');
        const sanitizedProviders = providers
            .filter(p => typeof p === 'string' && p.length > 0)
            .map(p => p.replace(/[^a-zA-Z0-9_-]/g, ''))
            .sort()
            .join(',');
        const sanitizedDateRange = dateRange.replace(/[^a-zA-Z0-9_-]/g, '');

        return `${sanitizedUserId}:${sanitizedProviders}:${sanitizedDateRange}:${limit}`;
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

        // Clean up if cache is getting too large
        if (this.cache.size > this.MAX_CACHE_SIZE * this.CLEANUP_THRESHOLD) {
            this.cleanup();
        }
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

        // First, remove expired entries
        for (const [key, entry] of this.cache.entries()) {
            if (now > entry.expiresAt) {
                keysToDelete.push(key);
            }
        }

        // If still over limit after removing expired entries, implement LRU eviction
        if (this.cache.size - keysToDelete.length > this.MAX_CACHE_SIZE) {
            const entries = Array.from(this.cache.entries())
                .filter(([key]) => !keysToDelete.includes(key))
                .sort((a, b) => a[1].data.timestamp - b[1].data.timestamp); // Sort by timestamp (oldest first)

            const excessEntries = entries.slice(0, this.cache.size - keysToDelete.length - this.MAX_CACHE_SIZE);
            keysToDelete.push(...excessEntries.map(([key]) => key));
        }

        keysToDelete.forEach(key => this.cache.delete(key));
    }

    getStats(): { size: number; keys: string[]; maxSize: number; hitRate?: number } {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys()),
            maxSize: this.MAX_CACHE_SIZE,
        };
    }
}

// Export singleton instance
export const calendarCache = new CalendarCache(); 