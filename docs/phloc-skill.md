# Phloc Skill Guide — Building & Deploying Frappe/ERPNext Customizations

A hands-on reference for creating custom reports, client scripts, Charts of Accounts templates, and other ERPNext customizations — then packaging them into the phlocalization Frappe app and deploying to a Frappe Cloud $25/month instance.

---

## Table of Contents

1. [Local Development Environment Setup](#1-local-development-environment-setup)
2. [Adding Custom Reports](#2-adding-custom-reports)
3. [Adding Client Scripts](#3-adding-client-scripts)
4. [Adding Custom Fields to Existing DocTypes](#4-adding-custom-fields-to-existing-doctypes)
5. [Adding Chart of Accounts Templates](#5-adding-chart-of-accounts-templates)
6. [Adding Custom DocTypes](#6-adding-custom-doctypes)
7. [Adding Print Formats](#7-adding-print-formats)
8. [Adding Property Setters](#8-adding-property-setters)
9. [Adding Server-Side Hooks](#9-adding-server-side-hooks)
10. [Testing](#10-testing)
11. [Frappe Cloud Deployment ($25/instance)](#11-frappe-cloud-deployment-25instance)
12. [Bench Command Reference](#12-bench-command-reference)
13. [Survival Checklist — Will My Changes Survive `bench update`?](#13-survival-checklist)

---

## 1. Local Development Environment Setup

### Prerequisites

- Python >= 3.10
- Node.js 18+
- MariaDB 10.6+ or PostgreSQL 14+
- Redis
- wkhtmltopdf

### Initialize a Bench

```bash
# Install bench CLI
pip install frappe-bench

# Create a new bench (pulls Frappe v15)
bench init --frappe-branch version-15 frappe-bench
cd frappe-bench

# Create a site
bench new-site phloc.localhost --mariadb-root-password <password> --admin-password admin

# Install ERPNext
bench get-app --branch version-15 erpnext
bench --site phloc.localhost install-app erpnext

# Install phlocalization
bench get-app https://github.com/xunema/phlocalization
bench --site phloc.localhost install-app bureau_of_internal_revenue

# Apply fixtures and migrations
bench --site phloc.localhost migrate

# Start dev server
bench start
```

Access at `http://phloc.localhost:8000`

### Enable Developer Mode (required for creating DocTypes/reports via UI)

```bash
bench --site phloc.localhost set-config developer_mode 1
bench --site phloc.localhost clear-cache
```

---

## 2. Adding Custom Reports

Custom reports are the primary deliverable in phlocalization. The app uses **Script Reports** that extend ERPNext's financial statements.

### File Structure (one directory per report)

All files must share the same snake_case name:

```
bureau_of_internal_revenue/
  bureau_of_internal_revenue/
    report/
      your_report_name/
        __init__.py                    # Empty, required
        your_report_name.json          # Report metadata (DocType record)
        your_report_name.py            # Server-side logic
        your_report_name.js            # Client-side filters & formatting
        your_report_name.html          # HTML template (optional)
        test_your_report_name.py       # Tests
```

### Step-by-Step: Create a New Report

#### A. Create the report JSON definition

```json
{
  "add_total_row": 0,
  "columns": [],
  "creation": "2026-03-09 00:00:00.000000",
  "disabled": 0,
  "docstatus": 0,
  "doctype": "Report",
  "filters": [],
  "idx": 0,
  "is_standard": "Yes",
  "letterhead": null,
  "modified": "2026-03-09 00:00:00.000000",
  "modified_by": "Administrator",
  "module": "Bureau of Internal Revenue",
  "name": "Your Report Name",
  "owner": "Administrator",
  "prepared_report": 0,
  "ref_doctype": "GL Entry",
  "report_name": "Your Report Name",
  "report_type": "Script Report",
  "roles": [
    {"role": "Accounts User"},
    {"role": "Accounts Manager"},
    {"role": "Auditor"}
  ],
  "timeout": 0
}
```

**Critical fields:**
- `report_type`: `"Script Report"` — runs your Python
- `ref_doctype`: `"GL Entry"` for financial reports (determines base permissions)
- `module`: Must match your module name exactly
- `is_standard`: `"Yes"` — marks it as part of the app (not user-created)

#### B. Create the Python report (`your_report_name.py`)

```python
import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
    get_columns,
    get_data,
    get_period_list,
)


def execute(filters=None):
    """Main entry point. Frappe calls this automatically."""
    period_list = get_period_list(
        filters.from_fiscal_year,
        filters.to_fiscal_year,
        filters.period_start_date,
        filters.period_end_date,
        filters.filter_based_on,
        filters.periodicity,
        company=filters.company,
    )

    # Fetch account data from ERPNext
    asset = get_data(
        filters.company,
        "Asset",
        "Debit",
        period_list,
        only_current_fiscal_year=False,
        filters=filters,
        accumulated_values=filters.accumulated_values,
    )

    columns = get_columns(
        filters.periodicity, period_list, filters.accumulated_values, filters.company
    )

    data = []
    data.extend(asset or [])

    # Return tuple: (columns, data, message, chart, report_summary)
    return columns, data, None, None, None
```

**Return value is always a tuple:** `(columns, data, message, chart, report_summary)`

#### C. Create the JavaScript file (`your_report_name.js`)

```javascript
frappe.query_reports["Your Report Name"] = $.extend(
    {},
    erpnext.financial_statements,
    {
        // Override the formatter to customize display
        formatter(value, row, column, data, df) {
            const formatted = erpnext.financial_statements.formatter
                ? erpnext.financial_statements.formatter(value, row, column, data, df)
                : value;

            // Hide numeric values for top-level group rows
            if (data && data.indent === 0 && typeof value === "number") {
                return "";
            }
            return formatted;
        },
    }
);

// Add ERPNext dimension filters (Cost Center, Project, etc.)
erpnext.utils.add_dimensions("Your Report Name", 10);

// Add custom filters
frappe.query_reports["Your Report Name"]["filters"].push({
    fieldname: "accumulated_values",
    label: __("Accumulated Values"),
    fieldtype: "Check",
    default: 1,
});

frappe.query_reports["Your Report Name"]["filters"].push({
    fieldname: "level",
    label: __("Show Levels Upto"),
    fieldtype: "Select",
    options: ["1", "2", "3", "4", "All"],
    default: "All",
});
```

**Patterns:**
- `$.extend({}, erpnext.financial_statements, {...})` — inherit standard financial statement behavior
- Push additional filters after the extend
- Filter object: `{fieldname, label, fieldtype, default, options?, reqd?}`
- To remove inherited filters: `.filter(f => !["cost_center"].includes(f.fieldname))`

#### D. Create the HTML template (`your_report_name.html`)

For financial reports, reuse ERPNext's template:

```html
{% include "accounts/report/financial_statements.html" %}
```

Or write custom Jinja HTML for non-financial reports.

#### E. Register the report

No hooks.py change needed. Frappe auto-discovers reports by the JSON file in the module's `report/` directory. Just run:

```bash
bench --site phloc.localhost migrate
bench --site phloc.localhost clear-cache
```

The report appears under: **Accounting > Reports > Your Report Name**

---

## 3. Adding Client Scripts

Client scripts inject JavaScript into existing DocType forms. This is how phlocalization adds the Schedule field toggle to the Account form.

### File Location

```
bureau_of_internal_revenue/
  public/
    js/
      your_doctype.js
```

### Register in hooks.py

```python
doctype_js = {
    "Account": "public/js/account.js",
    "Sales Invoice": "public/js/sales_invoice.js",   # add more as needed
}
```

### Client Script Pattern

```javascript
frappe.ui.form.on("Sales Invoice", {
    // Runs on form load/refresh
    refresh(frm) {
        frm.trigger("setup_custom_fields");
    },

    // Runs when a specific field changes
    customer(frm) {
        if (frm.doc.customer) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Customer",
                    filters: { name: frm.doc.customer },
                    fieldname: "tax_id"
                },
                callback(r) {
                    if (r.message) {
                        frm.set_value("custom_tax_id", r.message.tax_id);
                    }
                }
            });
        }
    },

    // Custom event (triggered by frm.trigger)
    setup_custom_fields(frm) {
        frm.toggle_display("custom_tax_id", !!frm.doc.customer);
    }
});
```

**Key frm methods:**
- `frm.toggle_display(fieldname, show)` — show/hide field
- `frm.set_value(fieldname, value)` — set value
- `frm.trigger(event_name)` — fire custom event
- `frm.doc.fieldname` — read current document values
- `frm.add_custom_button(label, callback, group)` — add toolbar button
- `frm.set_query(fieldname, filters)` — set link field filters

### Apply changes

```bash
bench build --app bureau_of_internal_revenue
bench --site phloc.localhost clear-cache
```

---

## 4. Adding Custom Fields to Existing DocTypes

Two approaches, both valid. The phlocalization app currently uses **fixtures**; the recommended upgrade-safe pattern is **programmatic creation**.

### Approach A: Fixtures (current phlocalization pattern)

**1. Create the field via Frappe UI** (with developer mode on):
   - Go to Customize Form > select DocType > add field > save

**2. Register in hooks.py:**
```python
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["Custom Field", "module", "=", "Bureau of Internal Revenue"]
        ]
    }
]
```

**3. Export:**
```bash
bench --site phloc.localhost export-fixtures --app bureau_of_internal_revenue
```

This writes `fixtures/custom_field.json`. The JSON contains the full field definition including `dt` (target DocType), `fieldname`, `fieldtype`, `label`, `insert_after`, `options`, etc.

**4. Fields are re-imported on every `bench migrate`.**

### Approach B: Programmatic (recommended for production)

This is the pattern used by India Compliance, HRMS, and other official Frappe apps. It survives bench updates more reliably.

**1. Add hooks:**
```python
after_install = "bureau_of_internal_revenue.setup.after_install"
after_migrate = "bureau_of_internal_revenue.setup.after_migrate"
```

**2. Create `bureau_of_internal_revenue/setup.py`:**
```python
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    create_custom_fields(get_custom_fields())


def after_migrate():
    create_custom_fields(get_custom_fields())


def get_custom_fields():
    return {
        "Account": [
            {
                "fieldname": "schedule",
                "fieldtype": "Select",
                "label": "Schedule",
                "insert_after": "parent_account",
                "options": "\n".join([""] + [f"SCHED {i}" for i in range(1, 24)]),
                "translatable": 1,
            }
        ],
        "Sales Invoice": [
            {
                "fieldname": "bir_tax_category",
                "fieldtype": "Link",
                "label": "BIR Tax Category",
                "options": "Tax Category",
                "insert_after": "taxes_and_charges",
            }
        ],
    }
```

**Why `after_migrate` matters:** It runs on every `bench migrate` (which happens on every `bench update`), re-asserting your fields even if something reset them.

---

## 5. Adding Chart of Accounts Templates

ERPNext allows custom Chart of Accounts (COA) templates. For BIR compliance, you need a Philippine COA with schedule assignments.

### COA Template File Location

Place your template inside the app:

```
bureau_of_internal_revenue/
  bureau_of_internal_revenue/
    chart_of_accounts/
      __init__.py
      verified/
        __init__.py
        philippines_bir_standard.py
```

### Register via hooks.py

```python
regional_overrides = {
    "Philippines": {
        "erpnext.accounts.doctype.chart_of_accounts.chart_of_accounts.get_charts_for_country":
            "bureau_of_internal_revenue.bureau_of_internal_revenue.chart_of_accounts.get_charts_for_country"
    }
}
```

### COA Template Format (Python dict)

```python
# philippines_bir_standard.py

chart_data = {
    "name": "Philippines - BIR Standard",
    "country_code": "ph",
    "tree": {
        "Assets": {
            "account_type": "",
            "is_group": 1,
            "root_type": "Asset",
            "Current Assets": {
                "is_group": 1,
                "account_type": "",
                "Cash and Cash Equivalents": {
                    "is_group": 1,
                    "account_type": "",
                    "Cash on Hand": {
                        "account_type": "Cash",
                    },
                    "Cash in Bank": {
                        "account_type": "Bank",
                    },
                },
                "Trade and Other Receivables": {
                    "is_group": 1,
                    "Accounts Receivable": {
                        "account_type": "Receivable",
                    },
                },
            },
        },
        "Liabilities": {
            "is_group": 1,
            "root_type": "Liability",
            "Current Liabilities": {
                "is_group": 1,
                "Accounts Payable": {
                    "account_type": "Payable",
                },
                "BIR Withholding Tax Payable": {
                    "account_type": "Tax",
                },
            },
        },
        "Equity": {
            "is_group": 1,
            "root_type": "Equity",
            "Share Capital": {},
            "Retained Earnings": {
                "account_type": "Equity",
            },
        },
        "Income": {
            "is_group": 1,
            "root_type": "Income",
            "Sales Revenue": {
                "account_type": "Income Account",
            },
        },
        "Expenses": {
            "is_group": 1,
            "root_type": "Expense",
            "Cost of Goods Sold": {
                "account_type": "Cost of Goods Sold",
            },
            "Operating Expenses": {
                "is_group": 1,
                "Salaries and Wages": {
                    "account_type": "Expense Account",
                },
            },
        },
    },
}
```

### Alternative: JSON-based COA

Place a JSON file at:
```
bureau_of_internal_revenue/
  bureau_of_internal_revenue/
    chart_of_accounts/
      verified/
        ph_bir_standard.json
```

Same tree structure as above but in JSON format. Frappe discovers it automatically if the `get_charts_for_country` function is set up to scan this directory.

---

## 6. Adding Custom DocTypes

For app-specific data models (e.g., "BIR Tax Schedule", "E-Invoice Log").

### Create via Bench (Developer Mode)

```bash
# In the Frappe UI: DocType List > + New DocType
# OR via code:
bench --site phloc.localhost new-doctype "BIR Tax Schedule" \
    --module "Bureau of Internal Revenue"
```

### File structure created automatically

```
bureau_of_internal_revenue/
  bureau_of_internal_revenue/
    doctype/
      bir_tax_schedule/
        __init__.py
        bir_tax_schedule.json       # Schema definition
        bir_tax_schedule.py         # Controller (server logic)
        bir_tax_schedule.js         # Form script (client logic)
        test_bir_tax_schedule.py    # Tests
```

### Controller pattern

```python
# bir_tax_schedule.py
import frappe
from frappe.model.document import Document


class BIRTaxSchedule(Document):
    def validate(self):
        """Runs before save."""
        if not self.schedule_code:
            frappe.throw("Schedule code is required")

    def on_submit(self):
        """Runs when document is submitted."""
        pass

    def on_cancel(self):
        """Runs when document is cancelled."""
        pass
```

### No hooks.py change needed

Frappe auto-discovers DocTypes from the module's `doctype/` directory during `bench migrate`.

---

## 7. Adding Print Formats

### Standard Jinja Print Format (in-app, upgrade-safe)

```
bureau_of_internal_revenue/
  bureau_of_internal_revenue/
    print_format/
      bir_sales_invoice/
        bir_sales_invoice.json
        bir_sales_invoice.html
```

**bir_sales_invoice.json:**
```json
{
  "doctype": "Print Format",
  "name": "BIR Sales Invoice",
  "doc_type": "Sales Invoice",
  "module": "Bureau of Internal Revenue",
  "standard": "Yes",
  "print_format_type": "Jinja",
  "raw_printing": 0,
  "disabled": 0
}
```

**bir_sales_invoice.html:**
```html
<div class="page-break">
    <h2>{{ doc.company }}</h2>
    <p>TIN: {{ doc.tax_id }}</p>
    <table>
        <tr>
            <th>Item</th><th>Qty</th><th>Rate</th><th>Amount</th>
        </tr>
        {% for item in doc.items %}
        <tr>
            <td>{{ item.item_name }}</td>
            <td>{{ item.qty }}</td>
            <td>{{ frappe.format_value(item.rate, {"fieldtype": "Currency"}) }}</td>
            <td>{{ frappe.format_value(item.amount, {"fieldtype": "Currency"}) }}</td>
        </tr>
        {% endfor %}
    </table>
    <p><strong>Grand Total: {{ frappe.format_value(doc.grand_total, {"fieldtype": "Currency"}) }}</strong></p>
</div>
```

### Export via fixtures (alternative)

```python
# hooks.py
fixtures = [
    # ... existing fixtures ...
    {
        "doctype": "Print Format",
        "filters": [["Print Format", "module", "=", "Bureau of Internal Revenue"]]
    }
]
```

---

## 8. Adding Property Setters

Property Setters modify properties of existing DocType fields (e.g., making a field mandatory, changing its default, hiding it) without modifying the DocType source.

### Programmatic approach (in setup.py)

```python
import frappe


def after_migrate():
    create_custom_fields(get_custom_fields())
    create_property_setters()


def create_property_setters():
    property_setters = [
        {
            "doctype": "Sales Invoice",
            "fieldname": "tax_id",
            "property": "reqd",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doctype": "Sales Invoice",
            "fieldname": "tax_id",
            "property": "default",
            "value": "",
            "property_type": "Data",
        },
    ]
    for ps in property_setters:
        frappe.make_property_setter(ps, is_system_generated=False)
```

### Fixture approach

```python
# hooks.py
fixtures = [
    {
        "doctype": "Property Setter",
        "filters": [["Property Setter", "module", "=", "Bureau of Internal Revenue"]]
    }
]
```

---

## 9. Adding Server-Side Hooks

### Document Event Hooks

Trigger your code when documents are saved, submitted, or cancelled:

```python
# hooks.py
doc_events = {
    "Sales Invoice": {
        "validate": "bureau_of_internal_revenue.overrides.sales_invoice.validate",
        "on_submit": "bureau_of_internal_revenue.overrides.sales_invoice.on_submit",
    },
    "Purchase Invoice": {
        "validate": "bureau_of_internal_revenue.overrides.purchase_invoice.validate",
    },
}
```

```python
# bureau_of_internal_revenue/overrides/sales_invoice.py
import frappe


def validate(doc, method):
    """Called before every Sales Invoice save."""
    if doc.company_address:
        # Add BIR validation logic
        pass


def on_submit(doc, method):
    """Called when Sales Invoice is submitted."""
    pass
```

### Whitelisted API Methods

Expose Python functions as REST API endpoints:

```python
# hooks.py (uncomment and modify)
override_whitelisted_methods = {
    "erpnext.accounts.utils.get_balance_on":
        "bureau_of_internal_revenue.overrides.accounts.get_balance_on"
}
```

Or create standalone API endpoints:

```python
# bureau_of_internal_revenue/api.py
import frappe


@frappe.whitelist()
def get_bir_schedule(account):
    """Callable via /api/method/bureau_of_internal_revenue.api.get_bir_schedule"""
    return frappe.db.get_value("Account", account, "schedule")
```

### Scheduled Tasks

```python
# hooks.py
scheduler_events = {
    "daily": [
        "bureau_of_internal_revenue.tasks.daily_compliance_check"
    ],
    "monthly": [
        "bureau_of_internal_revenue.tasks.generate_monthly_bir_summary"
    ],
}
```

---

## 10. Testing

### Test file pattern

```python
# test_your_report_name.py
import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

from bureau_of_internal_revenue.bureau_of_internal_revenue.report.your_report_name.your_report_name import execute


class TestYourReportName(FrappeTestCase):

    def test_basic_execution(self):
        filters = frappe._dict(
            company="_Test Company",
            from_fiscal_year="2025",
            to_fiscal_year="2025",
            period_start_date="2025-01-01",
            period_end_date="2025-12-31",
            filter_based_on="Fiscal Year",
            periodicity="Yearly",
            accumulated_values=1,
        )
        columns, data, *_ = execute(filters)
        self.assertTrue(len(columns) > 0)

    @patch("bureau_of_internal_revenue.bureau_of_internal_revenue.report.your_report_name.your_report_name.get_data")
    def test_with_mocked_data(self, mock_get_data):
        mock_get_data.return_value = [
            frappe._dict(account="Cash - TC", account_name="Cash", indent=1, total=500),
        ]
        filters = frappe._dict(company="_Test Company")
        columns, data, *_ = execute(filters)
        self.assertEqual(data[0].total, 500)
```

### Run tests

```bash
# All tests for the app
bench --site phloc.localhost run-tests --app bureau_of_internal_revenue

# Specific test file
bench --site phloc.localhost run-tests \
    --module bureau_of_internal_revenue.bureau_of_internal_revenue.report.balance_sheet_bir.test_balance_sheet_bir

# With verbose output
bench --site phloc.localhost run-tests --app bureau_of_internal_revenue -v
```

---

## 11. Frappe Cloud Deployment ($25/instance)

### Frappe Cloud Pricing (as of 2026)

| Plan | Price | What you get |
|------|-------|-------------|
| **$25/mo** (Starter/Basic) | $25 USD/month | 1 site, shared bench, limited resources, custom apps supported |
| $50/mo (Standard) | $50 USD/month | More CPU/RAM, priority support |
| Dedicated | Custom | Dedicated server, full control |

The $25/mo plan is sufficient for testing and small deployments. It supports custom app installation.

### Step-by-Step: Deploy to Frappe Cloud

#### 1. Prepare your repository

Ensure your repo has:
- `pyproject.toml` with `[tool.bench.frappe-dependencies]`
- `app_name` in `hooks.py` matches the top-level directory name
- `__init__.py` in the app root
- Repo is public on GitHub (or you grant Frappe Cloud access to private repo)

**Fix the placeholder in pyproject.toml first:**
```toml
[project]
name = "bureau_of_internal_revenue"
authors = [
    { name = "Ambibuzz Technologies LLP", email = "buzz.us@ambibuzz.com" }
]
description = "Philippine BIR Localization for ERPNext"
requires-python = ">=3.10"
readme = "README.md"
dynamic = ["version"]
dependencies = [
    "frappe~=15.95.0"
]

[tool.bench.frappe-dependencies]
frappe = "~=15.95.0"
erpnext = "~=15.0.0"
```

#### 2. Sign up and create a bench on Frappe Cloud

1. Go to [frappecloud.com](https://frappecloud.com) and sign up
2. **Dashboard > Benches > New Bench**
3. Select Frappe version: **Version 15**
4. Add apps:
   - **ERPNext** (from Frappe's official list)
   - **Your custom app**: click "Add App" > paste GitHub URL `https://github.com/xunema/phlocalization` > select branch
5. Choose region (nearest to Philippines: Singapore)
6. Create the bench — Frappe Cloud builds it (takes 5-15 minutes)

#### 3. Create a site

1. **Dashboard > Sites > New Site**
2. Select your bench
3. Choose the $25/mo plan
4. Set subdomain: `phloc.frappe.cloud` (or custom domain)
5. Select apps to install: **ERPNext** + **Bureau of Internal Revenue**
6. Create site — Frappe Cloud provisions it and runs `bench migrate` (applies fixtures)

#### 4. Verify deployment

1. Log in at `https://phloc.frappe.cloud`
2. Go to **Search Bar > Balance Sheet BIR** — report should appear
3. Go to **Accounting > Chart of Accounts** — verify Schedule field on group accounts
4. Go to **Customize Form > Account** — verify Schedule custom field exists

#### 5. Update workflow

When you push changes to GitHub:

1. **Dashboard > Benches > your bench > Updates**
2. Click **"Deploy"** or enable auto-deploy
3. Frappe Cloud pulls latest code, runs `bench migrate`, restarts
4. Your fixtures, reports, and hooks are re-applied automatically

### Frappe Cloud CLI (alternative)

```bash
# Install FC CLI
pip install press-cli

# Login
fc login

# List your benches
fc bench list

# Deploy (trigger update)
fc bench deploy <bench-name>
```

---

## 12. Bench Command Reference

### Daily Development Workflow

```bash
# Start dev server (Frappe + Redis + workers)
bench start

# After editing Python files — apply DB changes
bench --site phloc.localhost migrate

# After editing JS/CSS files — rebuild assets
bench build --app bureau_of_internal_revenue

# Quick cache clear (when UI doesn't reflect changes)
bench --site phloc.localhost clear-cache

# Export fixtures after creating custom fields via UI
bench --site phloc.localhost export-fixtures --app bureau_of_internal_revenue
```

### Site Management

```bash
# Create new site
bench new-site <site-name> --mariadb-root-password <pw> --admin-password <pw>

# Install app on site
bench --site <site-name> install-app bureau_of_internal_revenue

# Uninstall app
bench --site <site-name> uninstall-app bureau_of_internal_revenue

# Drop site entirely
bench drop-site <site-name> --force

# Backup
bench --site <site-name> backup --with-files

# Restore
bench --site <site-name> restore <backup-file>

# Open console (Python shell with frappe context)
bench --site <site-name> console

# Open mariadb shell
bench --site <site-name> mariadb
```

### App Management

```bash
# Get app from GitHub
bench get-app <url> --branch <branch>

# Remove app from bench (not from site)
bench remove-app <app-name>

# Check installed apps on site
bench --site <site-name> list-apps

# Update all apps
bench update

# Update specific app only
bench update --apps bureau_of_internal_revenue
```

### Development Tools

```bash
# Enable developer mode
bench --site <site-name> set-config developer_mode 1

# Run tests
bench --site <site-name> run-tests --app bureau_of_internal_revenue

# Generate new report scaffold
# (easier to copy an existing report directory and rename)

# Watch for JS changes and auto-rebuild
bench watch

# Run a specific Python function
bench --site <site-name> execute bureau_of_internal_revenue.setup.after_migrate
```

---

## 13. Survival Checklist

**Will my changes survive `bench update` / `bench migrate`?**

| Customization | Method | Survives update? |
|---|---|---|
| Custom Field on Account | Fixture in `fixtures/custom_field.json` | Yes — re-imported on migrate |
| Custom Field on Sales Invoice | `create_custom_fields()` in `after_migrate` | Yes — re-asserted on every migrate |
| Script Report | Files in `report/` directory | Yes — part of app source code |
| Client script on Account form | `doctype_js` in hooks + `public/js/` | Yes — part of app source code |
| Custom DocType | Files in `doctype/` directory | Yes — part of app source code |
| Print Format | Files in `print_format/` directory | Yes — part of app source code |
| Property Setter | Fixture or `after_migrate` hook | Yes — if properly registered |
| Field added via UI only | Not in app code | **NO — will be lost** |
| Core DocType JSON edited directly | Modified ERPNext source | **NO — overwritten by git pull** |
| Server Script (UI only) | Server Script DocType record | **NO — unless exported as fixture** |

### Golden Rules

1. **Never modify files inside `frappe/` or `erpnext/` directories**
2. **Every customization must live inside your app's directory**
3. **Use `after_migrate` hooks for critical custom fields** — they re-assert on every update
4. **Test locally with `bench update && bench migrate`** — if it survives locally, it survives on Frappe Cloud
5. **Export fixtures after every UI change** — `bench export-fixtures --app bureau_of_internal_revenue`

---

## Quick Reference: Adding a New BIR Report (Checklist)

```
[ ] Create directory: bureau_of_internal_revenue/bureau_of_internal_revenue/report/<name>/
[ ] Create __init__.py (empty)
[ ] Create <name>.json (report metadata, module, roles, ref_doctype)
[ ] Create <name>.py (execute function returning columns + data tuple)
[ ] Create <name>.js (extend erpnext.financial_statements, add custom filters)
[ ] Create <name>.html (include financial_statements.html or custom template)
[ ] Create test_<name>.py (FrappeTestCase with mock or integration tests)
[ ] Run: bench --site <site> migrate && bench --site <site> clear-cache
[ ] Verify report appears in Frappe desk
[ ] Run: bench --site <site> run-tests --module <full.module.path>
[ ] Commit and push — Frappe Cloud auto-deploys on next bench update
```
