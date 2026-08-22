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
