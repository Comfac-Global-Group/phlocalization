# Phlocalization — Architecture & Structure Reference

## Overview

**Comfac Philippine Localization (CPL)** is a Frappe/ERPNext custom app providing BIR (Bureau of Internal Revenue) statutory compliance for Philippine businesses. Built by Ambibuzz Technologies LLP as part of the BetterGov.ph Civic Tech Initiative.

**Core principle:** Zero modifications to ERPNext core. All customizations use Frappe's fixture, hooks, and JavaScript injection mechanisms — keeping the app upgrade-safe.

---

## Directory Structure

```
phlocalization/
├── bureau_of_internal_revenue/              # Frappe app root (app_name)
│   ├── __init__.py
│   ├── hooks.py                             # Frappe hook definitions
│   ├── modules.txt                          # Declares module: "Bureau of Internal Revenue"
│   ├── patches.txt                          # Migration patches (pre/post model sync)
│   │
│   ├── bureau_of_internal_revenue/          # Module package (matches module name)
│   │   ├── __init__.py
│   │   └── report/
│   │       ├── balance_sheet_bir/           # Script Report: Balance Sheet BIR
│   │       │   ├── balance_sheet_bir.json   #   Report DocType definition
│   │       │   ├── balance_sheet_bir.py     #   Server-side report logic
│   │       │   ├── balance_sheet_bir.js     #   Client-side filters & formatting
│   │       │   ├── balance_sheet_bir.html   #   HTML template (includes ERPNext base)
│   │       │   └── test_balance_sheet_bir.py
│   │       └── balance_sheet_schedule_bir/  # Script Report: Schedule-grouped variant
│   │           ├── balance_sheet_schedule_bir.json
│   │           ├── balance_sheet_schedule_bir.py
│   │           ├── balance_sheet_schedule_bir.js
│   │           ├── balance_sheet_schedule_bir.html
│   │           └── test_balance_sheet_schedule_bir.py
│   │
│   ├── config/                              # App configuration (empty)
│   ├── fixtures/
│   │   └── custom_field.json                # Custom "Schedule" field on Account DocType
│   ├── public/
│   │   └── js/
│   │       └── account.js                   # Client script injected into Account form
│   └── templates/pages/                     # Web templates (empty)
│
├── docs/
│   ├── Project Requirements Document.md
│   └── Roadmap.md
├── pyproject.toml                           # Python packaging & Frappe dependency config
└── README.md
```

---

## Component Details

### 1. hooks.py — Frappe Integration Point

The central configuration file that registers the app with Frappe.

| Hook | Value | Purpose |
|------|-------|---------|
| `app_name` | `"bureau_of_internal_revenue"` | Internal identifier; must match the top-level directory name |
| `app_title` | `"Bureau of Internal Revenue"` | Display name in Frappe desk |
| `doctype_js` | `{"Account": "public/js/account.js"}` | Injects custom JS into the Account form |
| `fixtures` | Custom Field where module = "Bureau of Internal Revenue" | Auto-imports the Schedule field on `bench migrate` |

**Commented-out hooks available for future use:**
- `before_install` / `after_install` — setup scripts
- `scheduler_events` — cron-like scheduled tasks
- `doc_events` — hooks on document save/cancel/trash
- `override_whitelisted_methods` — replace API endpoints
- `permission_query_conditions` / `has_permission` — custom permissions

### 2. modules.txt

Single line: `Bureau of Internal Revenue`. Registers this as a Frappe module, which is required for reports, doctypes, and fixtures to be associated with the app.

### 3. patches.txt

Contains `[pre_model_sync]` and `[post_model_sync]` sections (currently empty). This is where database migration scripts are registered when schema changes are needed.

### 4. fixtures/custom_field.json — Schedule Field

Adds a **"Schedule"** dropdown field to the standard **Account** DocType:

- **Position:** After `parent_account`
- **Field type:** Select
- **Options:** SCHED 1 through SCHED 23
- **Visibility:** Controlled by `account.js` — only shown when `is_group` is checked

This maps Chart of Accounts groups to BIR schedule categories, enabling schedule-based financial reporting without modifying the Account DocType source.

### 5. public/js/account.js — Client-Side Logic

Injected into the Account form via `doctype_js` hook:

- **Shows** the Schedule field only when `is_group` is true
- **Clears** the schedule value when `is_group` is unchecked
- Triggers on form `refresh` and `is_group` field change

### 6. Balance Sheet BIR Report

**Type:** Frappe Script Report (ref doctype: GL Entry)

**Server (`.py`):**
- Reuses ERPNext's `erpnext.accounts.report.financial_statements` functions (`get_period_list`, `get_data`, `get_columns`)
- Renames standard labels to BIR terminology (e.g., "Total Asset (Debit)" → "Total Current Assets (Debit)")
- Adds **level-based filtering** (show hierarchy levels 1–4 or All)
- Calculates provisional Profit/Loss row
- Checks for unclosed prior fiscal years
- Generates chart data (bar or line)

**Client (`.js`):**
- Extends `erpnext.financial_statements` report class
- Adds filters: `selected_view`, `accumulated_values`, `include_default_book_entries`, `level`
- Custom formatter hides numeric values on indent-0 (top-level) rows

**Template (`.html`):**
- Includes ERPNext's `accounts/report/financial_statements.html`

### 7. Balance Sheet Schedule BIR Report

**Type:** Frappe Script Report (ref doctype: GL Entry)

**Key difference from Balance Sheet BIR:** Groups accounts by their assigned BIR Schedule (SCHED 1–23) and inserts subtotal rows per schedule.

**Server (`.py`):**
- Queries all Accounts that have a non-empty `schedule` field
- Iterates through standard balance sheet data, grouping rows under their schedule
- Inserts "Total" subtotal rows at the end of each schedule group
- Adds a "Schedule" column at position 0
- Removes `cost_center` and `project` filters (not relevant for BIR schedules)
- No chart generation

**Client (`.js`):**
- Filters out `cost_center` and `project` from the standard filter set
- Same indent-0 numeric hiding as the Balance Sheet BIR

---

## Key Elements for Frappe Cloud / Frappe Instance Deployment

These are the files and conventions that make this app installable on any Frappe/ERPNext instance (including Frappe Cloud):

### Required Files

| File | Role |
|------|------|
| **`pyproject.toml`** | Declares the Python package, build system (`flit_core`), and **`frappe~=15.95.0` dependency**. The `[tool.bench.frappe-dependencies]` section tells Bench which Frappe version is required. |
| **`bureau_of_internal_revenue/__init__.py`** | Makes the top-level directory a Python package (required for `bench get-app` / `pip install`) |
| **`bureau_of_internal_revenue/hooks.py`** | **The single most critical file.** Frappe reads this to discover `app_name`, `app_title`, fixtures, JS includes, and all integration hooks. Without this, Frappe doesn't recognize the app. |
| **`bureau_of_internal_revenue/modules.txt`** | Registers the module name. Without this, reports and doctypes won't be associated with the app. |
| **`bureau_of_internal_revenue/patches.txt`** | Required by Frappe's migration system even if empty. Lists migration scripts to run during `bench migrate`. |

### Deployment Mechanism

```
# Standard Bench installation flow:
bench get-app https://github.com/xunema/phlocalization
bench --site <site-name> install-app bureau_of_internal_revenue
bench --site <site-name> migrate    # applies fixtures + patches
```

**What happens on install/migrate:**
1. Frappe reads `hooks.py` to register the app
2. `modules.txt` creates the module record in the database
3. `patches.txt` runs any pending migrations
4. `fixtures` array in `hooks.py` triggers import of `custom_field.json`, creating the Schedule field on Account
5. `doctype_js` registers `account.js` for injection into Account forms
6. Report JSON files (`balance_sheet_bir.json`, etc.) are loaded as Script Report records

### Frappe Cloud Specifics

For **Frappe Cloud** deployment, the repo needs:
1. A valid `pyproject.toml` with `[tool.bench.frappe-dependencies]` — **present**
2. The app directory name must match `app_name` in `hooks.py` — **matches** (`bureau_of_internal_revenue`)
3. The repo must be a valid Python package (has `__init__.py`) — **present**
4. Dependencies on `frappe` (and optionally `erpnext`) declared — **declared** (`frappe~=15.95.0`)

**Note:** The `pyproject.toml` still has placeholder values (`name = "your_app_name"`, generic author/description) that should be updated to match the actual app identity for proper Frappe Cloud listing.

### Fixture System

The fixture in `hooks.py`:
```python
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [["Custom Field", "module", "=", "Bureau of Internal Revenue"]]
    }
]
```

This means:
- `bench export-fixtures` exports all Custom Fields belonging to this module → `fixtures/custom_field.json`
- `bench migrate` on a fresh site imports them back, creating the Schedule field automatically
- This is the upgrade-safe pattern for extending standard DocTypes without touching core

---

## Data Flow Summary

```
Account Form (Desk UI)
  ↓ hooks.py doctype_js
  ↓ account.js toggles Schedule field visibility
  ↓
Account DocType + Schedule custom field (from fixtures)
  ↓
GL Entry data (standard ERPNext)
  ↓
balance_sheet_bir.py          →  Standard BIR Balance Sheet (level-filtered)
balance_sheet_schedule_bir.py →  Schedule-grouped Balance Sheet (SCHED 1-23 subtotals)
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | Frappe v15 |
| ERP | ERPNext v15 |
| Language | Python >= 3.10 |
| Build | flit_core |
| Formatter | Black (99 chars), isort (Black-compatible) |
| License | MIT |
