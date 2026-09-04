import {
  LEARNING_PROGRESS_KEY,
  computeProgress,
  createLearningProgressRepository,
  isLessonCompleted,
  toggleLessonCompletion,
  type StorageLike,
} from "./learningProgress";

function memoryStorage(initial: Record<string, string> = {}): StorageLike {
  const store: Record<string, string> = { ...initial };
  return {
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => {
      store[key] = value;
    },
    removeItem: (key) => {
      delete store[key];
    },
  };
}

const ALL_IDS = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"];

describe("learningProgress repository", () => {
  it("returns null when storage is empty", () => {
    const storage = memoryStorage();
    const repo = createLearningProgressRepository(storage);
    expect(repo.load()).toBeNull();
  });

  it("round-trips a progress payload through storage", () => {
    const storage = memoryStorage();
    const repo = createLearningProgressRepository(storage);
    const progress = { completed: ["a", "b"], updatedAt: "2026-01-01T00:00:00Z", version: 1 as const };
    repo.save(progress);
    expect(storage.getItem(LEARNING_PROGRESS_KEY)).not.toBeNull();
    expect(storage.getItem(LEARNING_PROGRESS_KEY)).toContain('"a"');
    expect(repo.load()).toEqual(progress);
  });

  it("ignores a stored payload with the wrong version", () => {
    const storage = memoryStorage({
      [LEARNING_PROGRESS_KEY]: JSON.stringify({ completed: ["a"], version: 2 }),
    });
    const repo = createLearningProgressRepository(storage);
    expect(repo.load()).toBeNull();
  });

  it("tolerates malformed JSON without throwing", () => {
    const storage = memoryStorage({ [LEARNING_PROGRESS_KEY]: "not-json{{{" });
    const repo = createLearningProgressRepository(storage);
    expect(repo.load()).toBeNull();
  });

  it("clear removes the stored key", () => {
    const storage = memoryStorage();
    const repo = createLearningProgressRepository(storage);
    repo.save({ completed: ["a"], updatedAt: null, version: 1 });
    expect(repo.load()).not.toBeNull();
    repo.clear();
    expect(storage.getItem(LEARNING_PROGRESS_KEY)).toBeNull();
  });

  it("survives a simulated reload (persistence across sessions)", () => {
    const storage = memoryStorage();
    const first = createLearningProgressRepository(storage);
    first.save({ completed: ["a", "c"], updatedAt: "2026-01-01T00:00:00Z", version: 1 });

    const second = createLearningProgressRepository(storage);
    const loaded = second.load();
    expect(loaded?.completed).toEqual(["a", "c"]);
  });
});

describe("learningProgress helpers", () => {
  it("computes progress counts", () => {
    const snapshot = computeProgress(["a", "c"], ALL_IDS);
    expect(snapshot.completed).toEqual(["a", "c"]);
    expect(snapshot.total).toBe(10);
    expect(snapshot.remaining).toHaveLength(8);
    expect(snapshot.remaining).not.toContain("a");
  });

  it("isLessonCompleted reflects membership", () => {
    expect(isLessonCompleted(["a"], "a")).toBe(true);
    expect(isLessonCompleted(["a"], "b")).toBe(false);
  });

  it("toggleLessonCompletion adds then removes an id", () => {
    const add = toggleLessonCompletion([], "a");
    expect(add.changed).toBe(false);
    expect(add.completed).toEqual(["a"]);

    const remove = toggleLessonCompletion(["a"], "a");
    expect(remove.changed).toBe(true);
    expect(remove.completed).toEqual([]);
  });

  it("toggleLessonCompletion respects the lesson order when provided", () => {
    const result = toggleLessonCompletion(["a"], "b", ALL_IDS);
    expect(result.completed).toEqual(["a", "b"]);
  });
});
