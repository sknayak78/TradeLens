/** Formatting helpers for immutable Mentor snapshots on journal trades. */

export interface MentorSnapshot {
  action: string | null;
  strategy: string | null;
  entry_range_low: number | null;
  entry_range_high: number | null;
  actual_entry_price: number | null;
  planned_stop_loss: number | null;
  target_1: number | null;
  target_2: number | null;
  risk_reward: number | null;
  holding_period: string | null;
  reason: string | null;
  captured_at: string | null;
}

export function hasMentorSnapshot(
  snapshot: MentorSnapshot | null | undefined,
): boolean {
  if (!snapshot) return false;
  return Boolean(
    snapshot.action ||
      snapshot.strategy ||
      snapshot.entry_range_low != null ||
      snapshot.entry_range_high != null ||
      snapshot.planned_stop_loss != null ||
      snapshot.target_1 != null ||
      snapshot.target_2 != null ||
      snapshot.risk_reward != null ||
      snapshot.holding_period ||
      snapshot.reason ||
      snapshot.captured_at,
  );
}

export function formatMoney(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "Not available at entry";
  }
  return `₹${value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatEntryRange(
  low: number | null | undefined,
  high: number | null | undefined,
): string {
  if (low == null || high == null || Number.isNaN(low) || Number.isNaN(high)) {
    return "Not available at entry";
  }
  return `${formatMoney(low)} – ${formatMoney(high)}`;
}

export function formatRiskReward(
  value: number | null | undefined,
): string {
  if (value == null || Number.isNaN(value)) {
    return "Not available at entry";
  }
  return `1 : ${value.toFixed(2)}`;
}

export function formatSnapshotLabel(
  value: string | null | undefined,
): string {
  if (!value || !value.trim()) {
    return "Not available at entry";
  }
  return value;
}

export function mentorSnapshotRows(snapshot: MentorSnapshot) {
  return [
    { label: "Mentor view", value: formatSnapshotLabel(snapshot.action) },
    { label: "Strategy", value: formatSnapshotLabel(snapshot.strategy) },
    {
      label: "Entry range",
      value: formatEntryRange(snapshot.entry_range_low, snapshot.entry_range_high),
    },
    {
      label: "Actual entry",
      value: formatMoney(snapshot.actual_entry_price),
    },
    {
      label: "Planned stop",
      value: formatMoney(snapshot.planned_stop_loss),
    },
    { label: "Target 1", value: formatMoney(snapshot.target_1) },
    { label: "Target 2", value: formatMoney(snapshot.target_2) },
    {
      label: "Risk / Reward",
      value: formatRiskReward(snapshot.risk_reward),
    },
    {
      label: "Holding period",
      value: formatSnapshotLabel(snapshot.holding_period),
    },
  ];
}
