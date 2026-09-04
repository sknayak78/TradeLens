import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  createLearningProgressRepository,
  type LearningProgress,
  type LearningProgressRepository,
  type StorageLike,
} from "@/lib/learningProgress";
import {
  LESSONS,
  lessonCount,
  type LessonId,
} from "@/lib/howToUseLessons";

/**
 * Feature-scoped progress state for the TradeLens Academy interactive
 * learning experience (ER-0043). Deliberately local to the learning feature —
 * NOT a generic global onboarding context.
 */

interface LearningProgressContextValue {
  /** Lesson ids marked complete. */
  completed: string[];
  /** Number of completed lessons (of the ten total). */
  completedCount: number;
  totalLessons: number;
  /** True when a given lesson is complete. */
  isComplete: (id: LessonId) => boolean;
  /** Mark a lesson complete (or incomplete). */
  toggleLessonComplete: (id: LessonId) => void;
  /** Clear all progress. */
  resetProgress: () => void;
}

const LearningProgressContext =
  createContext<LearningProgressContextValue | undefined>(undefined);

interface LearningProgressProviderProps {
  children: ReactNode;
  /** Test seam: swap the storage backend without touching components. */
  repository?: LearningProgressRepository;
  storage?: StorageLike;
}

export function LearningProgressProvider({
  children,
  repository,
  storage,
}: LearningProgressProviderProps) {
  const repo = useMemo<LearningProgressRepository>(
    () => repository ?? createLearningProgressRepository(storage),
    [repository, storage],
  );

  const [completed, setCompleted] = useState<string[]>(() => {
    const loaded = repo.load();
    return loaded ? loaded.completed : [];
  });

  useEffect(() => {
    const snapshot: LearningProgress = {
      completed,
      updatedAt: new Date().toISOString(),
      version: 1,
    };
    repo.save(snapshot);
  }, [completed, repo]);

  const toggleLessonComplete = useCallback(
    (id: LessonId) => {
      setCompleted((prev) => {
        const set = new Set(prev);
        if (set.has(id)) {
          set.delete(id);
        } else {
          set.add(id);
        }
        return LESSONS.map((lesson) => lesson.id).filter((lid) =>
          set.has(lid),
        );
      });
    },
    [],
  );

  const resetProgress = useCallback(() => {
    setCompleted([]);
    repo.clear();
  }, [repo]);

  const isComplete = useCallback(
    (id: LessonId) => completed.includes(id),
    [completed],
  );

  const value = useMemo<LearningProgressContextValue>(
    () => ({
      completed,
      completedCount: completed.length,
      totalLessons: lessonCount(),
      isComplete,
      toggleLessonComplete,
      resetProgress,
    }),
    [completed, isComplete, toggleLessonComplete, resetProgress],
  );

  return (
    <LearningProgressContext.Provider value={value}>
      {children}
    </LearningProgressContext.Provider>
  );
}

export function useLearningProgress(): LearningProgressContextValue {
  const ctx = useContext(LearningProgressContext);
  if (!ctx) {
    throw new Error(
      "useLearningProgress must be used within a LearningProgressProvider",
    );
  }
  return ctx;
}
