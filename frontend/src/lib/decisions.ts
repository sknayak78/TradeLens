/**
 * Shared decision-adjacent types for TradeLens.
 *
 * This module intentionally holds ONLY the `Agreement` concept — the one piece
 * of the decision vocabulary that is genuinely identical across features.
 *
 * The TradeLens Academy Case Lab and the Learning Journey / Trade Journal
 * deliberately use DIFFERENT decision taxonomies, so their enumerations live in
 * their own modules and are NOT merged here:
 *
 *   Academy (`howToUseLessons.ts`): BUY | WATCH | WAIT | AVOID
 *   Journal (`learningJourney.ts`): BUY | SELL | WATCH | AVOID
 *
 * In particular, Academy `WAIT` is a real action bucket (mentor "Wait" maps to
 * `WAIT`), whereas the Journal has no `WAIT` action — there a mentor "Wait"
 * folds into `AVOID`. They must stay distinct.
 */
export type Agreement = "agree" | "partial" | "differ";
