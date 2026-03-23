# Project Requirements Document (PRD)
## Comfac Philippine Localization (CPL)

> **Built on the Frappe Framework | A BetterGov.ph Civic Tech Initiative**
>
> **Wiki:** [https://github.com/xunema/phlocalization/wiki](https://github.com/xunema/phlocalization/wiki)
> **Full Roadmap:** [https://github.com/xunema/phlocalization/wiki/Roadmap](https://github.com/xunema/phlocalization/wiki/Roadmap)

---

## 1. Project Overview

**Comfac Philippine Localization (CPL)** is a free, open-source Frappe/ERPNext application commissioned by Comfac and built in partnership with Ambibuzz Technologies LLP. It delivers statutory compliance, workforce management, retail operations, and sustainability tracking tailored specifically to Philippine legal, tax, and operational requirements.

CPL is a CSR initiative under the BetterGov.ph civic tech program. Generic, high-value industry modules commissioned by paying clients are open-sourced into CPL so every Filipino business and institution can benefit. Proprietary client workflows remain confidential.

---

## 2. Vision & Mission

| | |
|---|---|
| **Vision** | World-class ERP automation accessible to every Filipino business and institution, for free. |
| **Mission** | Build open-source, AI-documentation-ready, compliance-first localization on top of Frappe/ERPNext, structured so that industry-specific extensions can be toggled on/off without adding bloat. |
| **CSR Commitment** | Industry modules (Real Estate, LGU, Logistics, etc.) commissioned privately are generalized and merged back into CPL under open-source license once deliverables are cleared. |

---

## 3. Architectural Principles (Non-Negotiable)

All CPL development must conform to the following constraints. These are hard requirements, not guidelines.

### 3.1 Domain-Based Toggling
- Industry-specific features (e.g., LGU Management, Real Estate) **must** be implemented as Frappe Domains.
- When a domain is inactive, its Workspaces, DocTypes, Reports, and fixtures must be fully hidden and impose zero performance overhead.
- No feature may be hardcoded into the base layer if it serves only a specific industry vertical.

### 3.2 MSME-First Design
- Every screen, workflow, and report in the base (non-domain) layer must be understandable and operable by a non-technical Filipino business owner without assistance.
- CPL must ship with **Philippine defaults pre-configured**: Chart of Accounts, BIR document templates, SSS/PhilHealth/Pag-IBIG contribution tables, and EOPT-ready invoicing. A new MSME install must be legally operational without any manual setup.
- Statutory rates and contribution tables must be admin-updatable through the UI — no developer or code deployment required to keep CPL compliant when laws change.
- Domain-based toggling (see 3.1) is the primary mechanism for keeping the base experience simple. A sari-sari store must never see LGU management or carbon footprint screens unless they explicitly enable those domains.

### 3.3 No Core Modifications
- ERPNext and Frappe core source files must remain untouched.
- All customizations must be delivered via Frappe's override/extend mechanisms: custom fields (fixtures), hooks, monkey-patching via `override_whitelisted_methods`, custom report modules, and DocType controllers.
- The application must be safe for ERPNext v15+ upgrades.

### 3.3 AI-Friendly Documentation
- All documentation must be written in structured Markdown (`.md`) stored within this repository under `docs/`.
- No PDF manuals. No screenshot-heavy guides.
- Files must be structured for RAG (Retrieval-Augmented Generation) compatibility: clear headings, consistent terminology, factual prose.

### 3.4 EOPT Act as Billing Baseline
- All invoicing, tax computation, and billing logic must reflect the **Ease of Paying Taxes Act (RA 11976)**.
- The **Sales Invoice** is the primary document. The Official Receipt is supplementary.
- Legacy OR-first workflows must not be introduced as defaults.

---

## 4. Scope & Phase Requirements

The CPL delivery is organized into five phases. Each phase's requirements are listed below with acceptance criteria.

---

### Phase 1 — Core Compliance Foundation

**Goal:** Minimum viable compliance to legally operate under BIR and EOPT Act.

#### 4.1.1 BIR-Compliant Chart of Accounts
- [ ] Localize ERPNext's default Chart of Accounts to match Philippine BIR standards.
- [ ] All account names, account types, and hierarchy must align with BIR-prescribed groupings.

#### 4.1.2 Standard Financial Statements
- [ ] Generate all 4 BIR-required financial statements:
  - Balance Sheet
  - Income Statement (Profit & Loss)
  - Statement of Cash Flows
  - Statement of Changes in Equity
- [ ] Reports must produce output suitable for direct submission without post-processing.

#### 4.1.3 Books of Accounts (CAS / Acknowledgment Certificate Ready)
- [ ] Generate the following Books in BIR-prescribed format:
  - General Ledger
  - General Journal
  - Sales Book
  - Purchase Book
  - Cash Receipts Book
  - Cash Disbursements Book
- [ ] Formats must be adjustable per RDO evaluator requirements (configurable field labels, column order, and groupings) without code changes.
- [ ] Support for the BIR Acknowledgment Certificate (AC) evaluation process; post-evaluation RDO formatting adjustments must be accommodatable via configuration.

#### 4.1.4 PenPlotter Transition Services *(Service Integration)*
- [ ] System must be able to export historical Books of Accounts in a format consumable by electronic PenPlotter devices for physical handwriting onto official manual books.
- [ ] Export format specification to be defined with Comfac's transition services team.

#### 4.1.5 Standard Schedules
- [ ] Schedule of Accounts Receivable
- [ ] Schedule of Accounts Payable
- [ ] Inventory Schedule

#### 4.1.6 EOPT-Compliant Document Templates
All templates default to **standard letter size, electronic print format**.

**Sales Side:**
- [ ] Sales Invoice (Primary document under EOPT)
- [ ] Official Receipt (Supplementary)
- [ ] Statement of Account
- [ ] Delivery Receipt

**Purchase Side:**
- [ ] Purchase Order
- [ ] Purchase Receipt
- [ ] Purchase Invoice

> Template variants for non-standard paper sizes are added to the open-source pool as clients commission them.

---

### Phase 2 — HRIS & Basic Philippine Payroll

**Goal:** Automate workforce management under Philippine labor law with mobile-first field support.

#### 4.2.1 Mobile-First Daily Time Record (DTR)
- [ ] Deploy a Progressive Web App (PWA) for check-in/check-out accessible on smartphones with no dedicated app installation required.
- [ ] Physical biometric devices must **not** be a prerequisite.
- [ ] Offline-capable: records must queue locally and sync when connectivity is restored.
- [ ] Verification: capture selfie with EXIF metadata (GPS coordinates + timestamp) as the audit trail for field/remote workers.

#### 4.2.2 Statutory Contribution Computation
- [ ] Built-in, table-driven (admin-maintainable) computation for:
  - SSS (Social Security System)
  - PhilHealth
  - Pag-IBIG (HDMF)
- [ ] Contribution tables must be updatable by a system administrator without a code deployment.

#### 4.2.3 Tax Annualization Engine
- [ ] Compute monthly withholding tax based on projected annual income.
- [ ] Perform year-end tax adjustment: calculate exact balance of tax owed vs. over-withheld and produce reimbursement/additional deduction entries.
- [ ] Generate BIR Form 2316 per employee per year.

---

### Phase 3 — MSME Retail & Payment Gateway Expansion

**Goal:** BIR-compliant POS and digital payment integration for the retail market.

#### 4.3.1 BIR-Ready POS
- [ ] **Device Locking:** A POS instance must be lockable to a specific physical device to comply with BIR Machine Identification Number (MIN) and Permit to Use (PTU) regulations. Unlocking requires administrator authorization.
- [ ] Peripheral integration (receipt printers, barcode scanners) starting with the most common local brands used in Philippine MSMEs.
- [ ] **Z-Reading** (end-of-day sales total reset report) and **X-Reading** (interim sales summary) generation per BIR and cooperating LGU/RDO requirements.

#### 4.3.2 E-Wallet Integration
- [ ] Native integration with aggregator APIs (PayMongo, Xendit) supporting:
  - GCash (Merchant/QR flow)
  - Maya (Merchant/QR flow)
- [ ] Integration must route through certified aggregators; CPL must not store raw card data.

#### 4.3.3 Credit Card Processing
- [ ] Offload credit card processing to ISO 27001 / PCI-DSS certified partners via API.
- [ ] CPL must not assume direct PCI-DSS scope. This constraint is in place until Comfac achieves ISO 27001 certification (target: 2027).

---

### Phase 4 — Advanced Industry & LGU Capabilities *(Domain-Toggled)*

**Goal:** Serve larger organizations and Philippine LGUs via toggleable domain extensions.

#### 4.4.1 LGU Statutory Reporting
- [ ] Automated data extraction formatted for **annual Business Permit renewal** (Gross Sales declarations per LGU-specific format).
- [ ] Template system to support varying LGU format requirements without custom code per LGU.

#### 4.4.2 Advanced Payroll Rules
- [ ] Piece-rate worker payroll computation.
- [ ] Hazard pay rules.
- [ ] Shifting schedule support (BPO and 24/7 operations).
- [ ] LGU-specific employment structure support (as defined with cooperating LGUs).

---

### Phase 5 — Sustainability & Carbon Footprint Tracking *(Domain-Toggled)*

**Goal:** Enable environmental accountability for organizations entering eco-conscious supply chains.

#### 4.5.1 Carbon Footprint Tracker (CFT) Module
- [ ] Toggleable domain module for tracking:
  - Carbon footprint of material inputs
  - Operational activity emissions
  - Energy consumption
- [ ] Total organizational carbon output calculation.
- [ ] Underlying CF database maintained by Comfac, originally built on Bureau Veritas recommendations.
- [ ] Module is freely available to all users.

#### 4.5.2 Prerequisites & Audit Readiness *(Documentation Requirement)*
- [ ] In-system guidance must clearly communicate that reliable CFT output requires proper internal data systems.
- [ ] Documentation must recommend ISO 14001 (Environmental Management Systems) implementation before using CFT output for formal ISO 14064 Greenhouse Gas audits.

---

## 5. External Integrations & Ecosystem

| Integration | Type | Phase |
|---|---|---|
| **Secada** (Paperless-ngx PH localization) | Document Management / OCR | Cross-phase |
| **Synx-Scheduler** | Operations & workforce scheduling | Phase 2+ |
| **PayMongo / Xendit** | Payment aggregator APIs | Phase 3 |
| **BIR eServices** | Statutory form submission | Phase 1+ |
| **PenPlotter devices** | Historical books export | Phase 1 |

### 5.1 Secada Integration Requirements
- [ ] Every digital ledger entry in CPL must be linkable to a scanned physical document stored in Secada.
- [ ] Secada must auto-ingest, OCR, and index scanned documents to be searchable from CPL.

### 5.2 Synx-Scheduler Integration Requirements
- [ ] Synx-Scheduler must be able to read employee and job data from CPL's HRIS module.
- [ ] Scheduling outputs (shifts, hours) must flow back into CPL payroll computation.

---

## 6. Non-Functional Requirements

| Requirement | Specification |
|---|---|
| **Framework** | Frappe v15 / ERPNext v15 |
| **Python** | >= 3.10 |
| **Upgrade Safety** | All customizations must survive Frappe/ERPNext minor and patch upgrades without manual intervention |
| **Documentation** | All modules documented in Markdown under `docs/`; structured for AI/RAG indexing |
| **Security** | No raw card data stored; PCI-DSS scope avoided until ISO 27001 achieved (2027) |
| **Offline Support** | DTR PWA must function without internet connectivity |
| **Performance** | Inactive domains impose zero database or UI overhead |
| **Localization** | Default currency: PHP; default timezone: Asia/Manila; default language: English (PH) |

---

## 7. Out of Scope

- Proprietary client workflows explicitly commissioned as private (these are not merged into CPL).
- Direct BIR EFPS (Electronic Filing and Payment System) e-filing API integration (dependent on BIR API availability; tracked separately).
- PCI-DSS Level 1/2 direct card acquiring (deferred post-ISO 27001).

---

## 8. References & Footnotes

- [^1]: Comfac provides specialized processing and consulting services to assist businesses in navigating the RDO post-evaluation process and securing full BIR acceptance of their computerized accounting systems.
- [^2]: Comfac provides comprehensive training and connects businesses with skilled former Comfac interns. For businesses requiring dedicated expertise, Comfac also offers premium professional consulting and implementation services.
- **EOPT Act:** Republic Act No. 11976 — Ease of Paying Taxes Act
- **Full Roadmap:** [https://github.com/xunema/phlocalization/wiki/Roadmap](https://github.com/xunema/phlocalization/wiki/Roadmap)

---

*This document is maintained in the repository at `docs/Project Requirements Document.md` and mirrored on the [project Wiki](https://github.com/xunema/phlocalization/wiki). The repository file is the developer source of truth; the Wiki is the published human-readable version. Keep both in sync on every PRD update.*
