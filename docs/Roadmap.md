# Comfac Philippine Localization (CPL) — Roadmap

> **Built on the Frappe Framework | A BetterGov.ph Civic Tech Initiative**
>
> This file is maintained in the repository at `docs/Roadmap.md` and mirrored on the [project Wiki](https://github.com/xunema/phlocalization/wiki/Roadmap). Keep both in sync.

---

## The Comfac Open Source Commitment

> "At Comfac, we believe that world-class automation should be accessible to every Filipino business and institution. As a proud participant and supporter of BetterGov.ph, our Corporate Social Responsibility (CSR) mission is to build free, open-source technology that improves the way we live and do business in the Philippines.
>
> Through the Comfac Philippine Localization (CPL) project, we commit to open-sourcing generic, high-value industry modules commissioned by our clients—whether for real estate, logistics, or local government—so the entire country can benefit. These features are built directly into CPL and can be easily toggled on or off based on a user's specific needs. (Note: We strictly respect our clients' data privacy and proprietary workflows; customized logic explicitly commissioned as private will remain confidential)." [^2]

---

## The MSME Promise

**CPL is built so that any Filipino sari-sari store owner, small contractor, or growing enterprise can get up and running — without hiring an IT team, without a consultant on day one, and without touching a single configuration screen they don't understand.**

This is not a side goal. It is a core design constraint that governs every phase of the roadmap.

Concretely, this means:

- **Philippine defaults, out of the box.** CPL ships with a pre-configured Chart of Accounts, BIR-compliant document templates, SSS/PhilHealth/Pag-IBIG contribution tables, and EOPT-ready invoicing. A new MSME installs CPL and is already legally operational — no manual setup required to meet baseline compliance.
- **Plain-language guidance everywhere.** Every form, report, and workflow is labeled in terms a Filipino business owner recognizes — not ERP jargon. Where a process is legally complex (e.g., RDO submission, CAS approval), the system guides the user through it step by step.
- **No IT department required.** Contribution tables, document templates, and statutory rates are admin-configurable through the UI. Keeping CPL compliant as laws change does not require a developer.
- **Works on what MSMEs already have.** The DTR PWA runs on the smartphones workers already carry. The POS supports the receipt printers and barcode scanners already common in Philippine tiangge and retail setups. No mandatory hardware upgrades.
- **Complexity is opt-in, not forced.** Domain-based toggling ensures that a small sari-sari store never sees LGU management screens, carbon footprint dashboards, or advanced payroll rules unless they choose to turn them on. The system stays simple until the business grows into needing more.

---

## Architectural & Strategic Guidelines (For Development Team)

To ensure CPL remains lightweight, scalable, and future-proof, all development must adhere to the following principles:

**Domain-Based Toggling:** Avoid feature bloat. Industry-specific commissions (e.g., Real Estate, LGU Management) must be built as custom Frappe "Domains." When a user checks a specific domain during setup, the system dynamically unhides the relevant Workspaces, DocTypes, and Reports. If the domain is off, the system remains perfectly lightweight for basic MSMEs.

**MSME-First UX:** Every screen, workflow, and report in the base (non-domain) layer must be reviewable against one question: *"Can a non-technical Filipino business owner understand and use this without assistance?"* If the answer is no, the design is not complete.

**AI-Friendly Documentation:** Move away from PDF manuals filled with screenshots. All documentation must be written in clean, structured Markdown (.md) files stored within the repository. This ensures readiness for RAG (Retrieval-Augmented Generation) so future users can simply ask an AI chatbot how to navigate the system.

**EOPT Act Compliance as Baseline:** All invoicing, tax computation, and billing logic must reflect the Ease of Paying Taxes (EOPT) Act (Republic Act No. 11976), prioritizing the unified Sales Invoice over the legacy Official Receipt system.

---

## The Comfac FOSS Ecosystem & Integrations

While CPL serves as the core ERP, Comfac also maintains and integrates with other crucial Free and Open-Source Software (FOSS) tools to complete the digital transformation landscape:

**Secada (Document Management System):** Built on the robust architecture of Paperless-ngx, Secada is our FOSS Philippine localization for massive document archiving. Even with digital ERPs, Philippine accounting and legal standards require rigorous physical document management. Secada automatically ingests, OCRs (reads text), and indexes scanned physical records, integrating seamlessly with CPL so every digital ledger entry can be linked to its original scanned physical document.

**Synx-Scheduler (Operations Scheduling):** Our FOSS operations scheduler built for complex resource management. Synx-Scheduler allows organizations to forecast, adapt, and schedule workers across various jobs, locations, or classes dynamically. It is designed to integrate easily with CPL's HRIS and payroll modules.

---

## The "Continuous" Go-To-Market Roadmap

Our engagement with Ambibuzz is structured into five logical phases, prioritizing statutory compliance first, followed by workforce management, retail operations, advanced industry extensions, and finally, sustainability tracking.

---

### Phase 1 — The Core Compliance Foundation

**Focus:** Ensuring the system meets the bare minimum legal and accounting requirements to operate in the Philippines under the EOPT Act.

**MSME Goal:** Install CPL and be BIR-ready on day one — no accountant or consultant needed to get the baseline working.

**BIR-Compliant Accounting Standard:**

- Localization of the Chart of Accounts to match Philippine standards.
- Generation of the 4 standard Financial Statements (Balance Sheet, Income Statement, Cash Flow, Statement of Changes in Equity).
- Acknowledgment Certificate (AC) / Certificate of Acceptance Ready Books of Accounts (formerly CAS): Formats specifically aligned for the BIR's evaluation process (General Ledger, General Journal, Sales/Purchase Books, Cash Receipts/Disbursements).
- **PenPlotter Transition Services:** Prior to full computerized system approval, the BIR legally requires historical Books of Accounts to be physically handwritten. To aid this migration, Comfac provides transition services utilizing electronic PenPlotters — robotic devices that physically write out digital ledger history onto official manual books using real ink, saving companies thousands of man-hours.

> **Crucial Context:** Under current BIR rules, while an Acknowledgment Certificate (AC) is issued quickly, the local Revenue District Office (RDO) conducts a post-evaluation audit and ultimately determines if a computerized system is fully accepted. The system must be flexible enough to accommodate formatting adjustments requested by specific RDO evaluators prior to final acceptance. [^1]

- Standard Charts and Schedules (e.g., Schedule of Accounts Receivable/Payable, Inventory Schedules).

**EOPT-Compliant Document Templates:**

A default Philippine-ready set of templates starting with standard letter size (electronic print format). Pre-built and ready to use — no template design skills required.

- *Sales Side:* Sales Invoice (Primary), Official Receipt (Supplementary), Statement of Account, Delivery Receipt.
- *Purchase Side:* Purchase Order, Purchase Receipt, Purchase Invoice.

> Note: Variants for different paper shapes/sizes will be added to the open-source pool as paying customers commission them.

---

### Phase 2 — HRIS & Basic Philippine Payroll

**Focus:** Automating workforce management tailored to Philippine labor laws and remote work realities.

**MSME Goal:** A small business owner can manage time records and run a fully statutory-compliant payroll from their phone — no HR software background required.

**Mobile-First Daily Time Record (DTR):**

- Rollout of a Progressive Web App (PWA) check-in/check-out system accessible via smartphones.
- Eliminates the mandatory need for physical biometric devices, catering specifically to remote locations, field workers, and construction sites. Utilizes EXIF data (GPS and timestamps) from selfies for offline verifiable tracking, syncing automatically when internet is restored.

**Basic Statutory Payroll:**

- Built-in, maintainable logic for national general laws: SSS, PhilHealth, and Pag-IBIG contributions.
- Contribution rates are admin-updatable through the UI — no developer needed when rates change.
- **Tax Annualization Engine:** Logic that calculates withholding tax based on projected annual income and performs the crucial year-end tax adjustment (calculating exact deductions or reimbursements/refunds after the final year-end balancing).
- Generation of basic statutory forms (e.g., BIR Form 2316).

---

### Phase 3 — MSME Retail & Payment Gateway Expansion

**Focus:** Capturing the retail market with compliant POS and seamless digital payments.

**MSME Goal:** A small retailer — tiangge, convenience store, or market stall — can be BIR-compliant and accept GCash/Maya payments with hardware they already own, set up in under a day.

**BIR-Ready POS for MSMEs:**

- **Device Locking Architecture:** Crucial functionality to lock a POS instance to a specific physical device/hardware to comply with BIR Machine Identification Number (MIN) and Permit to Use (PTU) regulations.
- Agnostic peripheral integration (receipt printers, barcode scanners) starting with heavily utilized local brands.
- End-of-day Z-reading and X-reading report generation tailored to cooperating Local Government Units (LGUs) and Revenue District Offices (RDOs).

**E-Wallet & Streamlined Credit Card Integration:**

- Integration with aggregator APIs (e.g., PayMongo, Xendit) to handle GCash and Maya (Merchant/QR flow) natively.
- Offloading Credit Card processing to certified partners to streamline payments while protecting Comfac's timeline for ISO 27001 certification (target 2027) by avoiding direct PCI-DSS liabilities.

---

### Phase 4 — Advanced Industry & LGU Capabilities

**Focus:** Scaling up to larger clients and specific civic/government needs. *(Toggleable via Domains — invisible to MSMEs who do not need it.)*

**LGU & Statutory Reporting Templates:**

- Automated data extraction formatted for local Business Permit renewals (Gross Sales declarations per LGU format).
- Templates for specific government requirements as requested by cooperating LGUs.

**Advanced Payroll:**

- Industry-specific rules (e.g., piece-rate workers, hazard pay, shifting schedules in BPOs).
- Integrations specific to LGU employment structures.

---

### Phase 5 — Sustainability & Carbon Footprint Tracking

**Focus:** Enabling environmental accountability for companies entering eco-conscious global supply chains. *(Toggleable via Domains — invisible to MSMEs who do not need it.)*

**Carbon Footprint Tracker (CFT) Module:**

- A toggleable module that allows businesses to track the carbon footprint of specific material inputs, operational activities, and energy consumption to calculate their total organizational output.
- The underlying CF database is maintained by Comfac, originally built based on Bureau Veritas recommendations for Cornersteel.
- Comfac is making this feature openly available to anyone who wants to calculate and know their Carbon Footprint.

**Prerequisites & Auditing:** While the tool is provided freely, a system is only as good as the data entered. To use the CFT features correctly and verify the results, a company must have proper internal systems and training. It is strongly recommended that organizations have ISO 14001 (Environmental Management Systems) implemented before relying on this tool to prepare for formal ISO 14064 Greenhouse Gas audits.

---

[^1]: Comfac provides specialized processing and consulting services to assist businesses in navigating the RDO post-evaluation process and securing full acceptance of their systems.

[^2]: Comfac provides comprehensive training and can connect businesses with highly skilled former Comfac Interns who have undergone our free, extensive Internship Program for these applications. For businesses requiring immediate, dedicated expertise, Comfac also caters to those who can afford our premium professional consulting and implementation services.
