# MD-04 Broad Market Scanner

## Objective

MD-04 adds a deterministic first-pass filter over the validated NSE equity
instrument master. It identifies symbols worth deeper analysis without changing
the existing opportunity API or recommendation vocabulary.

## Responsibility

`MarketScanner` owns universe iteration, inexpensive screening, symbol-level
failure handling, candidate results, and funnel metrics. `MarketDataService`
continues to own provider routing and provenance. The scanner requests one
daily OHLCV series per symbol and does not call snapshot, insight, LTP, Mentor,
or LLM logic.

## Screening Stages

The default stages are:

1. Data availability and minimum history
2. Liquidity using latest and recent average volume
3. Trend using close > EMA20 > EMA50
4. Momentum using RSI and a positive lookback return
5. Technical structure using support/resistance proximity, breakout/breakdown,
   and a basic daily-move volatility sanity check

The result is a candidate or a rejected screening result. It is not a Buy,
Watch, Wait, or Avoid decision.

## Funnel Metrics

Each scan returns universe, data-available, liquidity, trend, momentum,
technical, and final-candidate counts. Counts are sequential and deterministic,
so later-stage counts cannot exceed earlier-stage counts.

## Deferred

Deep analysis, opportunity ranking, UI presentation, scheduling, persistence,
and live production activation remain later work. MD-04 uses the MD-03 provider
chain and does not claim that Upstox is live without credentials and an API
validation.
