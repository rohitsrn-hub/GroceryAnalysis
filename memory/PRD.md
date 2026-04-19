# PRD — Grocery Sales Analytics Application

## Original Problem Statement
Full-stack sales analytics application for a grocery business ("URC 101 Area").
Features: daily/bulk sales data upload (manual + Excel), dashboard with financial
metrics and sales trends, monthly/yearly aggregation, forecasting, and an AI
chatbot ("Sandy") that answers strictly from internal DB.

## Source Control
- GitHub repo: https://github.com/rohitsrn-hub/GroceryAnalysis.git
- Active branch: `Chatbot` (pulled fresh on 2026-04-19)

## Tech Stack / Architecture
- Backend: FastAPI + Motor (async MongoDB) + Pydantic — monolithic `server.py` (~6,600 lines)
- Frontend: React + Tailwind + Recharts + Shadcn UI
- DB: MongoDB
- AI: direct `openai` SDK (user supplies `OPENAI_API_KEY` on Render for the chatbot);
  `extract-canteen-summary` uses `EMERGENT_LLM_KEY` if present
- Deployment target: Render

## User Personas
- Grocery store owner / manager (primary) — uploads daily sales, tracks financial health
- Analyst — reviews aggregations & forecasts

## Core Requirements (static)
1. Daily + bulk (monthly/yearly) Excel sales data upload
2. Dashboard financial summary (Revenue, Profit, Stock Value, etc.)
3. Sales trends chart (daily / last 3 / last 12 periods)
4. Monthly & yearly auto-aggregation
5. Forecasting module
6. AI Chatbot answering strictly from DB
7. Daily Sales PDF Report generation

---

## What's Been Implemented

### 2026-04-19 — Session: Automated Daily Sales Report + Fallback Hardening
- Pulled `Chatbot` branch from GitHub; confirmed services healthy (backend+frontend).
- **Automated daily sales report generation** from the Daily Upload modal:
  - `DailyUploadModal.js` now accepts an optional CSD summary image alongside the Excel file.
  - Auto-fetches previous bank + stock baseline from `/api/previous-financial-data`.
  - When image is attached, the modal orchestrates: upload Excel → extract grocery/liquor
    from image via `/api/extract-canteen-summary` → call `/api/generate-daily-report`
    which persists a `financial_data` record and returns the PDF (auto-downloaded).
  - Inline editable fallback inputs for Previous Bank / Stock values if no prior record exists.
  - Step-wise progress indicator and toasts.
- **Backend hardening — `/api/generate-daily-report`**:
  - `previous_bank_amount` is now **optional**; when omitted, endpoint queries the most
    recent `financial_data` record before the target date (not just yesterday) and uses
    its `current_bank_amount`/`current_stock_value`. Handles holidays/weekly offs/gaps.
  - Returns explicit 400 with a helpful message only when no prior report exists anywhere.
  - `HTTPException` now re-raised before generic `Exception` handler (no more masked 500s).
  - `liquor_sales` defaults to `0.0` for cleaner "sales-only" reports.
  - Covered by 8 new backend tests + 18 existing regression tests (26/26 passing).

### Previously Completed (from handover)
- Chatbot "Sandy" rolled back from `emergentintegrations` to direct `openai` SDK.
- Indentation bug in `server.py` causing system prompt skip for aggregate queries — fixed.
- `DataSummaries.js` component added as a sub-tab under Bulk Data Upload.
- Monthly/yearly aggregation now uses `data_period` instead of `upload_date`.
- Sales Trends chart: Last-3 periods corrected (current + 2 previous),
  strictly filtered by daily upload history, tooltips show exact dates.

---

## Known Open Issues / Backlog

### 🔴 P0
- Dashboard **Current Stock Value** shows 0 (recurring bug).
  Debug `/api/dashboard-summary` stock value calculation; verify source collection.

### 🟡 P1
- Complete Financial Health Report — backend logic for stock value in
  `generate-daily-report` is functionally in place but needs edge-case coverage
  (no prior record / missing W_Amt).

### 🟢 P2
- Flexible DB update modes: append daily/monthly/yearly with corresponding aggregation.
- Bank Transactions Table: track bank credits/debits.
- Refactor `server.py` (6,600+ lines) into modular routers/models.

---

## Tests Status
- Backend: 18/18 API tests pass (test_reports/iteration_1.json).
- Frontend: automated frontend testing skipped per user preference.

## Next Task Suggestions
1. Investigate & fix P0 — Dashboard Current Stock Value = 0.
2. User-verify the new auto-report flow (upload an Excel + CSD image).
3. Optional: add a "Generated last report" badge on the dashboard after auto-generation.
