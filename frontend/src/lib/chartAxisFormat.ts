export type ChartTimeframe = "1D" | "1W" | "1M" | "3M" | "1Y";

const IST = "Asia/Kolkata";

function parseIstDate(isoTimestamp: string): Date {
  return new Date(isoTimestamp);
}

function formatInIst(date: Date, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: IST,
    ...options,
  }).format(date);
}

export function formatChartAxisTickLabel(
  timeframe: string,
  isoTimestamp: string,
): string {
  const date = parseIstDate(isoTimestamp);
  switch (timeframe as ChartTimeframe) {
    case "1D":
      return formatInIst(date, {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    case "1W":
    case "1M":
    case "3M":
      return formatInIst(date, {
        day: "2-digit",
        month: "short",
      });
    case "1Y":
      return formatInIst(date, {
        month: "short",
        year: "numeric",
      });
    default:
      return formatInIst(date, {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
  }
}

/**
 * Visual presentation for candlestick X-axis tick labels.
 *
 * Angled labels keep intraday and monthly ticks readable without overlap while
 * staying a pure rendering concern: they do NOT alter tick selection, which
 * remains owned by chartTimeAxis.
 */
export interface XAxisLabelPresentation {
  /** Rotation angle in degrees (0 = horizontal, never 90). */
  angle: number;
  /** SVG text anchor so a rotated label stays aligned to its tick. */
  textAnchor: "start" | "middle" | "end";
  /** Vertical offset (px) of the rotated label from the axis baseline. */
  dy: number;
  /** Height (px) Recharts allocates for the axis so labels are not clipped. */
  height: number;
}

const X_AXIS_LABEL_PRESENTATION: Record<
  ChartTimeframe,
  XAxisLabelPresentation
> = {
  // Intraday timestamps: steeper angle to keep them from overlapping.
  "1D": { angle: 40, textAnchor: "end", dy: 7, height: 38 },
  // Daily ticks: gentlest angle.
  "1W": { angle: 26, textAnchor: "end", dy: 5, height: 30 },
  // Short month view.
  "1M": { angle: 32, textAnchor: "end", dy: 6, height: 34 },
  // Quarter view weekly ticks.
  "3M": { angle: 30, textAnchor: "end", dy: 6, height: 34 },
  // Monthly labels across a year: steeper angle to separate "Aug 2025" etc.
  "1Y": { angle: 40, textAnchor: "end", dy: 7, height: 38 },
};

export function getXAxisLabelPresentation(
  timeframe: string,
): XAxisLabelPresentation {
  return X_AXIS_LABEL_PRESENTATION[(timeframe as ChartTimeframe) ?? "1W"] ?? {
    angle: 30,
    textAnchor: "end",
    dy: 6,
    height: 34,
  };
}

export function formatChartTooltipLabel(
  timeframe: string,
  isoTimestamp: string,
): string {
  const date = parseIstDate(isoTimestamp);
  if (timeframe === "1D") {
    return `${formatInIst(date, {
      day: "2-digit",
      month: "short",
      year: "numeric",
    })}, ${formatInIst(date, {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    })} IST`;
  }
  if (timeframe === "1Y") {
    return formatInIst(date, {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }
  return formatInIst(date, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
