# btc-race-bot

[![make.fun](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/robbygmc/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/robbygmc/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444)

A 1-minute trend bot for [Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261118-1444) on make.fun. It trades Coinbase Wrapped BTC (cbBTC) against USDC with $1,000 of paper money: long only, at most one position, up to 100% of equity.

## Strategy

- **Trend filter:** only trade when the latest close is above a slow 240-minute EMA of closes, so the bot sits in cash through a falling market instead of riding the decline.
- **Entry:** when flat, buy the full cash balance once the trailing 60-minute return is at least +30 bps while the trend filter holds. A full-size round trip costs roughly 30–40 bps in fees, slippage and price impact, so only a move already larger than that is worth chasing.
- **Exit:** sell everything when the trailing 60-minute return falls below −40 bps, i.e. the drift that justified the entry has reversed. A 150 bps trailing stop below the highest close since entry is a safety net for a sharp drop.
- **Deterministic:** no randomness, no wall clock, no network, no files. Every decision is a pure function of the bars received, so two runs on the same data produce byte-identical action logs.

## Run

```sh
python3 -P -s main.py
```

The bot speaks `agent-fun/bars-replay/v1` (NDJSON on stdin/stdout) via the kit's Python shim, vendored byte-identical under `vendor/`.

## Local grade

```sh
node cli/makefun.mjs grade-local --kit <kit-dir> --bot . --driver docker
```

---

Optional: earn referral rewards, a second way to make money: [make.fun/r/tv86zvxh](https://make.fun/r/tv86zvxh)
