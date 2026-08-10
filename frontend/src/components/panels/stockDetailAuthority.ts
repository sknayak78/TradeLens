import type { StockDetail } from "@/services/marketService";
import type {
  Ranking,
  RecommendationAction,
  RecommendationStrategy,
  SuggestedAction,
  TradeSetup,
} from "@/types";

/**
 * ER-0021 — display authority for recommendation action/strategy.
 *
 * When a Mentor Engine recommendation (or additive Ranking action/strategy)
 * exists, it owns the decision chips. Legacy suggestedAction / tradeSetup are
 * fallbacks only — including Today's Opportunities / rankings.
 */

export type ChartSuggestedAction = RecommendationAction | SuggestedAction;
export type ChartSetupLabel = RecommendationStrategy | TradeSetup;

type RankingAuthorityRow = Pick<
  Ranking,
  "action" | "strategy" | "suggestedAction" | "tradeSetup"
>;

/** Current Suggested Action for ChartCard — never maps Breakout → Buy on Breakout. */
export function resolveChartSuggestedAction(
  stock: Pick<StockDetail, "recommendation" | "suggestedAction">
): ChartSuggestedAction {
  if (stock.recommendation) {
    return stock.recommendation.action;
  }
  return stock.suggestedAction;
}

/** Setup badge label for ChartCard — prefers recommendation strategy. */
export function resolveChartSetup(
  stock: Pick<StockDetail, "recommendation" | "tradeSetup">
): ChartSetupLabel {
  if (stock.recommendation) {
    return (
      stock.recommendation.setup?.strategy ?? stock.recommendation.strategy
    );
  }
  return stock.tradeSetup;
}

/** Opportunities / rankings Action column — mentor action with legacy fallback. */
export function resolveRankingAction(
  row: RankingAuthorityRow
): ChartSuggestedAction {
  return row.action ?? row.suggestedAction;
}

/** Opportunities / rankings Setup column — mentor strategy with legacy fallback. */
export function resolveRankingSetup(row: RankingAuthorityRow): ChartSetupLabel {
  return row.strategy ?? row.tradeSetup;
}
