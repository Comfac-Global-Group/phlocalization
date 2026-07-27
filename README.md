# Bureau of Internal Revenue (BIR)

A custom **Frappe application** developed by **Ambibuzz Technologies LLP** that replicates and extends standard ERPNext financial reports to support **Bureau of Internal Revenue (BIR)**– Philippines(PHP) style statutory reporting and presentation requirements.

The application focuses on compliance-friendly reporting while keeping ERPNext core code untouched and upgrade-safe.


---

## Purpose

ERPNext’s standard financial reports are functionally correct but often require:
- Simplified hierarchical views for statutory submissions
- Presentation-specific formatting
- Compliance-aligned terminology

This app **replicates standard ERPNext reports** (starting with the Balance Sheet) and applies controlled, non-destructive customizations tailored for BIR-style reporting.

---

## Included Reports

### BIR Balance Sheet

A replicated version of ERPNext’s standard **Balance Sheet** report with additional presentation and filtering capabilities.

#### Key Features

- Replicated from ERPNext Balance Sheet (no core overrides)
- Built using `erpnext.accounts.report.financial_statements`
- Level-based account hierarchy filtering
- Presentation-only hiding of zero or parent-level amounts: display details only up to Level 3, roll up deeper levels into Level 3, hide lower-level accounts and Level 1 totals at the bottom.
- Custom label renaming to match BIR terminology
- Safe for ERPNext and Frappe upgrades

---

## Design Principles

- **No Core Modifications** – ERPNext source code remains untouched  
- **Presentation Focused** – formatting does not affect ledger data  
- **Upgrade Safe** – compatible with future upgrades  
- **Extensible** – easy to add more BIR-aligned reports  

---

## Supported Versions

- **Frappe Framework**: v15  
- **ERPNext**: v15  

---

## Installation

### 1. Get the App

From your bench directory:

```bash
bench get-app bureau_of_internal_revenue https://github.com/Ambibuzz/bureau_of_internal_revenue.git
```

---

## Guide: Creating a Dynamic BIR CAS Letterhead in ERPNext v15

This guide explains how to set up a custom Letterhead that dynamically fetches tax compliance details from the **BIR CAS Settings** Single DocType and user session data, ensuring standardized footers and headers across financial reports and document prints.

### Prerequisites

- **Role required:** System Manager or Print Designer
- **Target Version:** ERPNext / Frappe v15+
- **Dependency:** Custom or Core DocType named `BIR CAS Settings`

### Step-by-Step Configuration

#### 1. Navigate to Letterhead List

Search for **Letterhead** in the Awesome Bar (`Ctrl + K` / `Cmd + K`) or navigate to **Home > Printing > Letterhead**, then click **Add Letterhead**.

#### 2. Configure Basic Fields

- **Letterhead Name:** Enter `BIR CAS Letterhead` (or your preferred identifier).
- **Is Default:** Check if this should be automatically applied to all document prints.
- **Disabled:** Unchecked.

#### 3. Header Setup

In the Header section, enable HTML mode (or select the HTML tab) and insert the following Jinja snippet to dynamically fetch company name, address, and VAT TIN details:

```html
{% set bir = frappe.db.get_value('BIR CAS Settings', 'BIR CAS Settings',
['company_name', 'registered_address', 'tin_branch_code', 'branch_code',
'software_name', 'version_number'], as_dict=True) %}
<div style="width: 100%; font-family: Arial, sans-serif; text-align: center;
padding-bottom: 8px; margin-bottom: 10px;">
  <div style="font-size: 16px; font-weight: bold; text-transform: uppercase;
  letter-spacing: 1px;">
    {{ bir.company_name or '' }}
  </div>
  <div style="font-size: 11px; margin-top: 4px; color: #333;">
    {{ bir.registered_address or '' }}
  </div>
  <div style="font-size: 11px; margin-top: 4px; font-weight: bold;">
    VAT REG TIN: {{ bir.tin_branch_code or '' }}-{{ bir.branch_code or '' }}
  </div>
</div>
```

#### 4. Footer Setup

In the Footer section, switch to the Footer HTML area and insert the following Jinja code to automatically log the software version, active user identity, and real-time generation timestamp:

```html
{% set bir = frappe.db.get_value('BIR CAS Settings', 'BIR CAS Settings',
['company_name', 'registered_address', 'tin_branch_code', 'software_name',
'version_number'], as_dict=True) %}
{% set user_full_name = frappe.db.get_value('User', frappe.session.user, 'full_name') %}
{% set username = frappe.db.get_value('User', frappe.session.user, 'username') %}
{% set generated_at = frappe.utils.now_datetime().strftime('%B %d, %Y %I:%M:%S %p') %}
<div style="width: 100%; font-family: Arial, sans-serif; padding-top: 6px;
margin-top: 10px; font-size: 10px; color: #444;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tbody>
      <tr>
        <td style="padding-bottom: 2px;">
          <b>Software Name &amp; Version :</b> {{ bir.software_name or '' }} &nbsp;
          {{ bir.version_number or '' }}
        </td>
      </tr>
      <tr>
        <td style="vertical-align: top;">
          <b>Generated By :</b> {{ user_full_name or '' }} &nbsp; (User ID: {{
          username or '' }}) &nbsp;
          <b>Date &amp; Time Generated :</b> {{ generated_at }}
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

#### 5. Save & Test

1. **Save Record** – Click **Save** in the upper-right corner of the Letterhead form.
2. **Attach to Print Format** – Open any standard document (e.g., Sales Invoice or a Print Format builder for reports).
3. **Preview Output** – Select **Print**, choose `BIR CAS Letterhead` from the Letterhead dropdown, and verify that all dynamic parameters evaluate correctly without blank Jinja tags.

> **Consultant's Note:** Since `BIR CAS Settings` is treated as a Single DocType, passing `'BIR CAS Settings'` twice in `frappe.db.get_value('BIR CAS Settings', 'BIR CAS Settings', ...)` accurately retrieves the single instance record without incurring extra query overhead in WKHTMLTOPDF/PDF render runs.