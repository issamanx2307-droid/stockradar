\# Radar System Architecture (Complete Blueprint)



This document describes the complete architecture of the Radar platform — a high-performance stock scanning SaaS similar to TradingView.



The system is designed to scan \*\*10,000 – 50,000 stocks in under 1 second\*\* and support thousands of users simultaneously.



\---



\# System Overview



Radar consists of four major layers:



1\. Market Data Layer

2\. Indicator \& Scanning Engine

3\. Backend API Layer

4\. Frontend SaaS Application



\---



\# High Level Architecture



```

Market Data Sources

&#x20;       │

&#x20;       ▼

Market Data Pipeline

&#x20;       │

&#x20;       ▼

Indicator Engine

&#x20;       │

&#x20;       ▼

Indicator Cache

&#x20;       │

&#x20;       ▼

Scanner Engine

&#x20;       │

&#x20;       ▼

Radar API

&#x20;       │

&#x20;       ▼

Frontend UI

&#x20;       │

&#x20;       ▼

Users

```



\---



\# Core System Modules



The Radar platform consists of the following core components:



Market Data Pipeline

Indicator Engine

Scanner Language

Scanner Parser

Query Optimizer

Scanner Execution Engine

Backend API

Frontend UI

SaaS Infrastructure

Subscription System

Backtesting Engine



\---



\# 1 Market Data Pipeline



Responsible for collecting and preparing market data.



Functions



• Fetch market data from vendors

• Normalize OHLCV data

• Store historical data

• Deliver data to indicator engine



Data Schema



```

ticker

timestamp

open

high

low

close

volume

```



Pipeline Flow



```

Market Data Vendor

&#x20;       ↓

Data Ingestion

&#x20;       ↓

Data Normalization

&#x20;       ↓

Database Storage

&#x20;       ↓

Indicator Engine

```



Recommended Databases



PostgreSQL

TimescaleDB

ClickHouse



\---



\# 2 Indicator Engine



Computes technical indicators used by scanners.



Indicators



EMA

SMA

ATR

ADX

RSI



Example



```

ema20 = close.ewm(span=20).mean()

ema50 = close.ewm(span=50).mean()

ema200 = close.ewm(span=200).mean()

```



Indicators are calculated \*\*once\*\* and stored in the indicator cache.



\---



\# 3 Indicator Cache System



Stores precomputed indicators to avoid recalculation.



Structure



```

ticker | ema20 | ema50 | ema200 | atr | adx | rsi

```



Cache Options



In-memory dataframe

Redis

Columnar storage



Benefits



• Faster scanning

• Reduced CPU load

• Reusable indicators



\---



\# 4 Scanner Language



Radar provides a formula language for defining scanners.



Example



```

close > ema(200)

ema(20) > ema(50)

volume > avg\_volume(20)

```



Supported Functions



ema()

sma()

atr()

rsi()

adx()

highest()

lowest()



Logical Operators



AND

OR

NOT



Cross Functions



```

cross\_above(ema(50), ema(200))

cross\_below(ema(50), ema(200))

```



\---



\# 5 Scanner Language Parser



Converts scanner formulas into an Abstract Syntax Tree (AST).



Pipeline



```

Formula

&#x20;  ↓

Tokenizer

&#x20;  ↓

Parser

&#x20;  ↓

AST

```



Example AST



```

AND

&#x20; GREATER\_THAN

&#x20;     CLOSE

&#x20;     EMA(200)

&#x20; GREATER\_THAN

&#x20;     EMA(20)

&#x20;     EMA(50)

```



The AST is then sent to the Query Optimizer.



\---



\# 6 Scanner Query Optimizer



Transforms AST into an optimized execution plan.



Functions



• Remove redundant calculations

• Detect required indicators

• Simplify logical expressions

• Compile vectorized expressions



Example optimization



Input



```

(close > ema200) AND (close > ema200)

```



Output



```

close > ema200

```



\---



\# 7 Scanner Execution Engine



Responsible for ultra-fast scanning.



Design principle



Never iterate stock by stock.



Bad



```

for stock in stocks

```



Good



```

vectorized dataframe evaluation

```



Example execution



```

scan = (

&#x20;   (df.close > df.ema200) \&

&#x20;   (df.ema20 > df.ema50) \&

&#x20;   (df.ema50 > df.ema200)

)

```



Performance targets



```

10,000 stocks → <100ms

50,000 stocks → <400ms

```



Recommended libraries



NumPy

Pandas

Polars



\---



\# 8 Radar API Layer



Backend API used by frontend applications.



Recommended Framework



Django

Django REST Framework



Example Endpoints (Implemented in this repository)



Core Radar

```
GET  /api/dashboard/
GET  /api/symbols/?exchange=SET&sector=...
GET  /api/prices/{symbol}/?days=365
GET  /api/indicators/{symbol}/?days=100
GET  /api/signals/?days=30&exchange=SET&min_score=80
GET  /api/scanner/?exchange=SET&formula=close%20%3E%20ema(200)
POST /api/scanner/run/
POST /api/backtest/
```

Cache Management

```
GET  /api/cache/stats/
POST /api/cache/warmup/
POST /api/cache/invalidate/
```

Dictionary / Tooltip Assistant (Dictionary-first, no external AI)

```
GET  /api/term/?q=RSI
GET  /api/terms/search/?q=ema
GET  /api/terms/featured/
POST /api/qa/ask/
```

Position Analysis Engine (Rule-based scoring, not financial advice)

```
POST /api/position/analyze/
```

Auth (dj-rest-auth)

```
POST /api/auth/login/
POST /api/auth/logout/
POST /api/auth/registration/
```



\#\#\# 8.1 Dictionary-First Knowledge System (Implemented)



Goal: explain technical terms instantly (TradingView-like tooltip UX) with minimal cost.



Key rules



• Dictionary-first: always resolve from DB/cache first

• No external AI: missing terms become a ticket for superadmin to answer

• Feedback loop: when admin answers a question, it is promoted into the dictionary



Backend data models



• StockTerm: the canonical dictionary entry for a term (short + full definition)

• TermQuestion: unanswered questions (admin queue). When answered, it auto-upserts StockTerm



Frontend behavior



• Hover term → tooltip shows short definition (`/api/term/?q=...`)

• Toggle ON/OFF assistant stored in localStorage

• Auto-highlight runs safely in React tree and skips heavy/fragile DOM areas (tables, svg, inputs)



\#\#\# 8.2 Position Analysis Engine (Implemented)



Goal: analyze a user's position context using latest market data and a rule-based scoring engine.



Important: The system does not provide financial advice. It produces a signal classification and a score.



Inputs



• symbol

• buy_price



Outputs



• decision label: BUY_MORE / HOLD / SELL (classification label only)

• explanation: user-friendly reasons + disclaimer

• score: 0–100

• confidence: 0–95



Data sources



• PriceDaily (latest close)

• Indicator (latest RSI/EMA/ADX, etc.)



Persistence



• PositionAnalysis records each analysis for audit/history



\#\#\# 8.3 Repository Implementation Map



Backend (Django)



• Models: `radar/models.py` (Profile, Symbol, PriceDaily, Indicator, Signal, BusinessProfile, StockTerm, TermQuestion, PositionAnalysis)

• APIs: `radar/views.py` + `radar/urls.py`

• Serializers: `radar/serializers.py`

• Admin: `radar/admin.py`

• Position Analysis Engine: `radar/services/position_analysis.py`

• WebSocket: `radar/consumers.py`, `stockradar/routing.py`, `radar/routing.py`



Frontend (React + Vite)



• App shell / navigation: `frontend/src/App.tsx`

• Term Assistant (tooltip + auto highlight + toggle): `frontend/src/components/TermAssistant.tsx`

• Pages: `frontend/src/pages/*` (Dashboard, Scanner, Signals, Chart, StrategyBuilder, Backtest, PositionAnalysis, Guide, Qna, Profile, Contact)

• API client/types: `frontend/src/api/client.ts`, `frontend/src/api/types.ts`

\#\#\# 8.4 Compliance Note



The Position Analysis Engine intentionally outputs a score-based classification and explanation. It must not be presented as financial advice.



\---



\# 9 Frontend UI



User interface similar to TradingView.



Recommended stack



React

Vite (implemented)

Next.js (optional)

TypeScript



UI Components



Chart Panel

Scanner Panel

Watchlist

Indicator Panel

Dictionary Tooltip Assistant (TradingView-like hover tooltip)

Guide / Dictionary pages

Q\&A Chat (dictionary-first, ticket to admin)

Position Analysis (rule-based scoring)

Profile / Alerts settings

Contact page (Business Profile)



Layout



```

Chart Area



Scanner Results | Watchlist

```



Real-time updates delivered via WebSocket.



\---



\# 10 SaaS Infrastructure



Radar operates as a multi-tenant SaaS platform.



Architecture



```

Load Balancer

&#x20;     ↓

API Servers

&#x20;     ↓

Worker Nodes

&#x20;     ↓

Database \& Cache

```



Core Services



User Service

Scanner Service

Billing Service

Notification Service



\---



\# 11 Subscription System



Manages plans and feature access.



Plans



Free

Pro

Premium



Example Feature Access



Free



• limited scanners

• delayed data



Pro



• unlimited scanners

• real-time scanning



Premium



• backtesting

• advanced indicators



Payment providers



Stripe

Paddle



\---



\# 12 Scanner Backtesting Engine



Allows users to test strategies on historical data.



Workflow



```

User selects scanner

&#x20;       ↓

Choose time period

&#x20;       ↓

Backtesting Engine

&#x20;       ↓

Performance metrics

```



Metrics



Win Rate

Average Return

Max Drawdown

Profit Factor



Example result



```

Trades: 120

Win Rate: 57%

Average Return: 4.2%

```



\---



\# Performance Targets



```

Scan latency < 500 ms

Support 10,000 concurrent users

Handle 50,000+ stocks

```



\---



\# Future Enhancements



AI signal generation

pattern recognition

portfolio backtesting

global market coverage



\---



\# Summary



Radar is composed of the following major systems:



Market Data Pipeline

Indicator Engine

Indicator Cache

Scanner Language

Scanner Parser

Query Optimizer

Execution Engine

Radar API

Frontend UI

SaaS Infrastructure

Subscription System

Backtesting Engine



Together these components form a scalable, high-performance stock scanning platform.



