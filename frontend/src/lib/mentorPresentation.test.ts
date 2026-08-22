import {
  humanizeRule,
  humanizeWarning,
  TRADELENS_MENTOR,
} from "./mentorPresentation";

/** Internal rule keys that must never appear in user-facing presentation. */
const INTERNAL_RULE_KEYS = [
  "room_to_resistance",
  "clear_of_support",
  "price_above_ema20",
  "price_above_ema50",
  "price_above_ema200",
  "ema_stack_bullish",
  "rsi_healthy",
] as const;

const INTERNAL_WARNING_KEYS = [
  "risk_reward_below_minimum",
  "rsi_overbought",
  "rsi_oversold",
  "price_at_or_above_resistance",
  "no_usable_levels",
] as const;

function assertNoRawIdentifier(text: string, identifier: string) {
  expect(text).not.toContain(identifier);
  expect(text).not.toMatch(new RegExp(identifier.replace(/_/g, "_"), "i"));
}

describe("mentorPresentation regression", () => {
  describe("humanizeRule", () => {
    it.each(INTERNAL_RULE_KEYS)(
      "does not expose raw key %s in title, status, or explanation",
      (ruleKey) => {
        const context = {
          price: 1180.7,
          ema20: 1189.05,
          ema50: 1175,
          ema200: 1150,
          rsi: 62,
          support: 1150,
          resistance: 1250,
        };
        const rule = humanizeRule(ruleKey, context);

        assertNoRawIdentifier(rule.title, ruleKey);
        assertNoRawIdentifier(rule.status, ruleKey);
        assertNoRawIdentifier(rule.explanation, ruleKey);
        rule.values.forEach((row) => {
          assertNoRawIdentifier(row.label, ruleKey);
          assertNoRawIdentifier(row.value, ruleKey);
        });
      },
    );

    it("converts room_to_resistance to human-readable Room to Resistance", () => {
      const rule = humanizeRule("room_to_resistance", {
        price: 1180,
        resistance: 1250,
      });
      expect(rule.title).toBe("Room to Resistance");
      expect(rule.explanation.toLowerCase()).toContain("room");
      expect(rule.explanation.toLowerCase()).toContain("resistance");
    });

    it("converts clear_of_support to human-readable Clear of Support", () => {
      const rule = humanizeRule("clear_of_support", {
        price: 1180,
        support: 1150,
      });
      expect(rule.title).toBe("Clear of Support");
      expect(rule.status).toBe("Clear of support");
      expect(rule.explanation.toLowerCase()).toContain("support");
    });

    it("converts price_above_ema20 with actual values", () => {
      const rule = humanizeRule("price_above_ema20", {
        price: 1180.7,
        ema20: 1189.05,
      });
      expect(rule.title).toBe("Price vs EMA20");
      expect(rule.status).toBe("Below EMA20");
      expect(rule.values.some((v) => v.label === "Current Price")).toBe(true);
      expect(rule.values.some((v) => v.label === "EMA20")).toBe(true);
    });

    it("never surfaces undefined, null, or NaN", () => {
      for (const key of INTERNAL_RULE_KEYS) {
        const rule = humanizeRule(key, {});
        const blob = JSON.stringify(rule);
        expect(blob).not.toMatch(/undefined|null|NaN/i);
      }
    });
  });

  describe("humanizeWarning", () => {
    it.each(INTERNAL_WARNING_KEYS)(
      "does not expose raw warning key %s in title, summary, or explanation",
      (warningKey) => {
        const warning = humanizeWarning(
          warningKey,
          { price: 1180, resistance: 1250, rsi: 85 },
          {
            entryMin: 100,
            entryMax: 102,
            stopLoss: 95,
            target1: 110,
            target2: 115,
            riskReward: 0.9,
          },
        );

        assertNoRawIdentifier(warning.title, warningKey);
        assertNoRawIdentifier(warning.summary, warningKey);
        assertNoRawIdentifier(warning.explanation, warningKey);
      },
    );

    it("converts risk_reward_below_minimum to human-readable copy", () => {
      const warning = humanizeWarning(
        "risk_reward_below_minimum",
        {},
        {
          entryMin: 100,
          entryMax: 102,
          stopLoss: 95,
          target1: 110,
          target2: 115,
          riskReward: 0.9,
        },
      );
      expect(warning.title).toBe("Risk / Reward");
      expect(warning.summary).toContain("below the preferred minimum");
      expect(warning.explanation).toContain(TRADELENS_MENTOR);
    });
  });
});
