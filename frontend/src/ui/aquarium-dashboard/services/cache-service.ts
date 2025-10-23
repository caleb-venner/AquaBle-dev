/**
 * Client-side caching service for metadata and configurations
 * Reduces unnecessary API calls by caching data that rarely changes
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
}

class CacheService {
  private caches = new Map<string, CacheEntry<any>>();

  /**
   * Get cached data if available and not expired
   */
  get<T>(key: string): T | null {
    const entry = this.caches.get(key);
    if (!entry) return null;

    const now = Date.now();
    const age = now - entry.timestamp;

    // Check if cache has expired
    if (age > entry.ttl) {
      this.caches.delete(key);
      return null;
    }

    return entry.data as T;
  }

  /**
   * Set cache entry with TTL
   */
  set<T>(key: string, data: T, ttlMs: number = 5 * 60 * 1000): void {
    this.caches.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttlMs,
    });
  }

  /**
   * Clear specific cache entry
   */
  clear(key: string): void {
    this.caches.delete(key);
  }

  /**
   * Clear all caches
   */
  clearAll(): void {
    this.caches.clear();
  }

  /**
   * Get cache age in milliseconds (-1 if not cached)
   */
  getAge(key: string): number {
    const entry = this.caches.get(key);
    if (!entry) return -1;
    return Date.now() - entry.timestamp;
  }

  /**
   * Check if cache is still valid
   */
  isValid(key: string): boolean {
    const entry = this.caches.get(key);
    if (!entry) return false;
    return Date.now() - entry.timestamp <= entry.ttl;
  }
}

export const cacheService = new CacheService();

// Cache key constants
export const CACHE_KEYS = {
  DOSER_METADATA: 'doser_metadata',
  LIGHT_METADATA: 'light_metadata',
} as const;

// Cache TTLs (in milliseconds)
export const CACHE_TTL = {
  METADATA: 10 * 60 * 1000, // 10 minutes - metadata rarely changes
  STATUS: 30 * 1000,        // 30 seconds - status should be fresh
} as const;

/**
 * Invalidate all metadata caches (call when user performs operations that modify metadata)
 */
export function invalidateMetadataCache(): void {
  cacheService.clear(CACHE_KEYS.DOSER_METADATA);
  cacheService.clear(CACHE_KEYS.LIGHT_METADATA);
}

/**
 * Get debug info about cache state
 */
export function getCacheDebugInfo(): Record<string, any> {
  return {
    doserMetadata: {
      cached: cacheService.get(CACHE_KEYS.DOSER_METADATA) !== null,
      age: cacheService.getAge(CACHE_KEYS.DOSER_METADATA),
      valid: cacheService.isValid(CACHE_KEYS.DOSER_METADATA),
    },
    lightMetadata: {
      cached: cacheService.get(CACHE_KEYS.LIGHT_METADATA) !== null,
      age: cacheService.getAge(CACHE_KEYS.LIGHT_METADATA),
      valid: cacheService.isValid(CACHE_KEYS.LIGHT_METADATA),
    },
  };
}
