/**
 * Learning-progress persistence for the How to Use TradeLens interactive
 * education feature (ER-0043).
 *
 * Persistence is isolated behind a small repository so that a future ER can
 * swap localStorage for IndexedDB without rewriting the consuming UI. Only
 * educational lesson-completion state is stored here — never trading or
 * journal data.
 *
 * Storage key is namespaced and versioned: `tradelens.learning.v1`.
 */

export const LEARNING_PROGRESS_KEY = "tradelens.learning.v1";

export interface LearningProgress {
  /** Completed lesson ids. */
  completed: string[];
  /** ISO timestamp of the last change. */
  updatedAt: string | null;
  /** Shape/version of the stored payload. */
  version: 1;
}

export const EMPTY_PROGRESS: LearningProgress = {
  completed: [],
  updatedAt: null,
  version: 1,
};

/**
 * Abstraction over whatever storage backend backs progress. The UI only talks
 * to this interface, so `localStorage` can later be replaced with IndexedDB
 * without touching components.
 */
export interface LearningProgressRepository {
  load(): LearningProgress | null;
  save(progress: LearningProgress): void;
  clear(): void;
}

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** A repository backed by the provided storage (defaults to localStorage). */
export function createLearningProgressRepository(
  storage: StorageLike = globalThis.localStorage,
  key: string = LEARNING_PROGRESS_KEY,
): LearningProgressRepository {
  return {
    load() {
      try {
        const raw = storage.getItem(key);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as unknown;
        return normalizeStoredProgress(parsed);
      } catch {
        return null;
      }
    },
    save(progress) {
      try {
        storage.setItem(key, JSON.stringify(progress));
      } catch {
        // Persistence failures (e.g. storage unavailable/quota) are non-fatal
        // for the interactive experience: the lesson still works in-memory.
      }
    },
    clear() {
      try {
        storage.removeItem(key);
      } catch {
        // no-op
      }
    },
  };
}

function normalizeStoredProgress(value: unknown): LearningProgress | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (record.version !== 1) return null;
  const completed = Array.isArray(record.completed)
    ? record.completed.filter(
        (id): id is string => typeof id === "string" && id.length > 0,
      )
    : [];
  return {
    completed,
    updatedAt: typeof record.updatedAt === "string" ? record.updatedAt : null,
    version: 1,
  };
}

/** Pure helpers for deriving progress from a lesson completion list. */
export interface ProgressSnapshot {
  completed: string[];
  total: number;
  remaining: string[];
}

export function computeProgress(
  completed: string[],
  totalLessonIds: string[],
): ProgressSnapshot {
  const done = totalLessonIds.filter((id) => completed.includes(id));
  return {
    completed: done,
    total: totalLessonIds.length,
    remaining: totalLessonIds.filter((id) => !completed.includes(id)),
  };
}

export function isLessonCompleted(
  completed: string[],
  lessonId: string,
): boolean {
  return completed.includes(lessonId);
}

/** Toggle a lesson id on/off, preserving order independent of input order. */
export function toggleLessonCompletion(
  completed: string[],
  lessonId: string,
  order: string[] = [],
): { completed: string[]; changed: boolean } {
  const set = new Set(completed);
  const changed = set.has(lessonId);
  if (changed) {
    set.delete(lessonId);
  } else {
    set.add(lessonId);
  }
  const ordered = order.length
    ? order.filter((id) => set.has(id))
    : Array.from(set);
  return { completed: ordered, changed };
}
