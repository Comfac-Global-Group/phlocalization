# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	if not filters:
		return [], []
	columns = get_columns()
	data = get_data(filters)
	if not data:
		return columns, []
	return columns, data


def get_columns():
	return [
		{"label": "Account",               "fieldname": "account",           "fieldtype": "Link",         "options": "Account",      "width": 250},
		{"label": "Cost Center",            "fieldname": "cost_center",       "fieldtype": "Link",         "options": "Cost Center",  "width": 160},
		{"label": "Doc Type",               "fieldname": "doc_type",          "fieldtype": "Data",                                    "width": 160},
		{"label": "Doc No",                 "fieldname": "doc_no",            "fieldtype": "Dynamic Link", "options": "doc_type",     "width": 150},
		{"label": "Pay Type",               "fieldname": "doc_type_label",    "fieldtype": "Data",                                    "width": 80},
		{"label": "Reference",              "fieldname": "reference_no",      "fieldtype": "Data",                                    "width": 140},
		{"label": "Tran Date",              "fieldname": "transaction_date",  "fieldtype": "Date",                                    "width": 100},
		{"label": "Payee/Received From",    "fieldname": "party",             "fieldtype": "Data",                                    "width": 220},
		{"label": "Particulars",            "fieldname": "particulars",       "fieldtype": "Data",                                    "width": 400},
		{"label": "Beginning Balance",      "fieldname": "beginning_balance", "fieldtype": "Currency",                                "width": 130},
		{"label": "Debit (Transaction)",    "fieldname": "debit",             "fieldtype": "Currency",                                "width": 130},
		{"label": "Credit (Transaction)",   "fieldname": "credit",            "fieldtype": "Currency",                                "width": 130},
		{"label": "Debit (Net Change)",     "fieldname": "net_debit",         "fieldtype": "Currency",                                "width": 130},
		{"label": "Credit (Net Change)",    "fieldname": "net_credit",        "fieldtype": "Currency",                                "width": 130},
		{"label": "Debit (Balance)",        "fieldname": "balance_debit",     "fieldtype": "Currency",                                "width": 130},
		{"label": "Credit (Balance)",       "fieldname": "balance_credit",    "fieldtype": "Currency",                                "width": 130},
	]


def get_data(filters):
	sql = """
WITH
accounts_with_txn AS (
  SELECT DISTINCT g.account
  FROM `tabGL Entry` g
  WHERE g.docstatus = 1
    AND IFNULL(g.is_cancelled, 0) = 0
    AND g.company = %(company)s
    AND g.posting_date BETWEEN %(from_date)s AND %(to_date)s
),
accounts_with_bb AS (
  SELECT gle.account
  FROM `tabGL Entry` gle
  WHERE gle.docstatus = 1
    AND IFNULL(gle.is_cancelled, 0) = 0
    AND gle.company = %(company)s
    AND gle.posting_date < %(from_date)s
  GROUP BY gle.account
  HAVING ROUND(SUM(gle.debit - gle.credit), 2) <> 0
),
accounts_in_scope_raw AS (
  SELECT account FROM accounts_with_txn
  UNION
  SELECT account FROM accounts_with_bb
),
accounts_in_scope AS (
  SELECT air.account
  FROM accounts_in_scope_raw air
  JOIN `tabAccount` a
    ON a.name = air.account AND a.company = %(company)s
  WHERE
    %(account)s = 'All Accounts'
    OR (
      %(account)s = 'Cost of Sales Accounts'
      AND a.account_type = 'Cost of Goods Sold'
    )
)

SELECT
    account,
    cost_center,
    doc_type,
    doc_no,
    doc_type_label,
    reference_no,
    transaction_date,
    party,
    particulars,
    beginning_balance,
    debit,
    credit,
    net_debit,
    net_credit,
    balance_debit,
    balance_credit
FROM (

    /* ======== BEGINNING BALANCE ROW ======== */
    SELECT
        gle.account AS account,
        NULL AS cost_center,
        NULL AS transaction_date,
        NULL AS doc_type,
        NULL AS doc_type_label,
        NULL AS doc_no,
        NULL AS reference_no,
        NULL AS party,
        '<b>BEGINNING BALANCE </b>' AS particulars,
        SUM(gle.debit - gle.credit) AS beginning_balance,
        NULL AS debit,
        NULL AS credit,
        NULL AS net_debit,
        NULL AS net_credit,
        NULL AS balance_debit,
        NULL AS balance_credit,
        CONCAT(gle.account, '-1') AS sort_order,
        NULL AS dept_code
    FROM `tabGL Entry` gle
    WHERE gle.docstatus = 1
      AND IFNULL(gle.is_cancelled, 0) = 0
      AND gle.company = %(company)s
      AND gle.posting_date < %(from_date)s
      AND gle.account IN (SELECT account FROM accounts_in_scope)
    GROUP BY gle.account

    UNION ALL

    /* ======== TRANSACTION DETAIL ROWS ======== */
    SELECT
        g.account AS account,
        g.cost_center AS cost_center,
        g.posting_date AS transaction_date,
        g.voucher_type AS doc_type,
        CASE
          WHEN g.voucher_type = 'Payment Entry' THEN
            CASE
              WHEN COALESCE(g.voucher_subtype, pe.payment_type) = 'Pay'               THEN 'Pay'
              WHEN COALESCE(g.voucher_subtype, pe.payment_type) = 'Receive'           THEN 'Receive'
              WHEN COALESCE(g.voucher_subtype, pe.payment_type) = 'Internal Transfer' THEN 'Int. Transfer'
              ELSE COALESCE(g.voucher_subtype, pe.payment_type, '')
            END
          ELSE NULL
        END AS doc_type_label,
        g.voucher_no AS doc_no,
        COALESCE(
          pe.reference_no,
          je.cheque_no,
          si.remarks,
          pi.remarks,
          sr.name,
          g.against_voucher
        ) AS reference_no,
        CASE
          WHEN g.voucher_type = 'Journal Entry'
            THEN COALESCE(cust_je.customer_name, supp_je.supplier_name, emp_je.employee_name, g.party, jea.party)
          WHEN g.voucher_type = 'Payment Entry'
            THEN COALESCE(NULLIF(TRIM(pe.party_name), ''), pe.party, g.party)
          WHEN g.voucher_type = 'Sales Invoice'
            THEN si.customer_name
          WHEN g.voucher_type = 'Purchase Invoice'
            THEN pi.supplier
          WHEN g.voucher_type = 'Purchase Receipt'
            THEN COALESCE(pr.supplier, pr.supplier_name)
          ELSE g.party
        END AS party,
        CASE
            WHEN g.voucher_type = 'Journal Entry'
                THEN COALESCE(
                       NULLIF(TRIM(jea.user_remark), ''),
                       NULLIF(TRIM(SUBSTRING_INDEX(COALESCE(g.remarks,''), 'Note:', 1)), ''),
                       g.against
                     )
            WHEN g.voucher_subtype = 'Depreciation Entry'
                THEN TRIM(SUBSTRING_INDEX(COALESCE(g.remarks,''), 'Note:', 1))
            WHEN g.account = 1521 AND g.against LIKE '1521 - PROJECTS IN PROGRESS - ESCO%%'
                THEN TRIM(
                    SUBSTRING(
                        SUBSTRING_INDEX(COALESCE(g.remarks,''), 'Note:', 1),
                        LOCATE(' ', COALESCE(g.remarks,'')) + LENGTH(SUBSTRING_INDEX(COALESCE(g.remarks,''),' ','1')) + 1
                    )
                )
            WHEN g.account = 1521
                THEN TRIM(SUBSTRING(SUBSTRING_INDEX(COALESCE(g.remarks,''), 'Note:', 1), LOCATE(' ', COALESCE(g.remarks,'')) + 1))
            WHEN g.account IN (1291, 1293)
                THEN TRIM(SUBSTRING_INDEX(COALESCE(g.remarks,''), 'Note:', 1))
            WHEN g.account IN (2201, 1301)
                THEN g.party
            /* --- Payment Entry: Pay or Receive → pull item descriptions from linked invoice --- */
            WHEN g.voucher_type = 'Payment Entry'
                 AND COALESCE(g.voucher_subtype, pe.payment_type) IN ('Pay', 'Receive')
                 AND pe_ref_items.item_descriptions IS NOT NULL
                THEN pe_ref_items.item_descriptions
            /* --- Payment Entry: fallback to remarks/against --- */
            WHEN g.voucher_type = 'Payment Entry'
                THEN COALESCE(NULLIF(TRIM(per.remarks), ''), g.against)
            WHEN g.remarks LIKE '%%received from%%'
                THEN TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(COALESCE(g.remarks,''), 'Transaction reference no', 1), 'received from ', -1))
            WHEN g.remarks LIKE '%%PAY PRD%%'
                THEN 'PAYROLL'
            ELSE g.against
        END AS particulars,
        NULL AS beginning_balance,
        g.debit AS debit,
        g.credit AS credit,
        SUM(g.debit)  OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx) AS net_debit,
        SUM(g.credit) OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx) AS net_credit,
        CASE
            WHEN (
                COALESCE((
                    SELECT SUM(gle_bb.debit - gle_bb.credit)
                    FROM `tabGL Entry` gle_bb
                    WHERE gle_bb.docstatus = 1
                      AND IFNULL(gle_bb.is_cancelled, 0) = 0
                      AND gle_bb.company = %(company)s
                      AND gle_bb.posting_date < %(from_date)s
                      AND gle_bb.account = g.account
                ), 0)
                + SUM(g.debit)  OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx)
                - SUM(g.credit) OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx)
            ) > 0
            THEN (
                COALESCE((
                    SELECT SUM(gle_bb.debit - gle_bb.credit)
                    FROM `tabGL Entry` gle_bb
                    WHERE gle_bb.docstatus = 1
                      AND IFNULL(gle_bb.is_cancelled, 0) = 0
                      AND gle_bb.company = %(company)s
                      AND gle_bb.posting_date < %(from_date)s
                      AND gle_bb.account = g.account
                ), 0)
                + SUM(g.debit)  OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx)
                - SUM(g.credit) OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx)
            )
            ELSE 0
        END AS balance_debit,
        CASE
            WHEN (
                COALESCE((
                    SELECT SUM(gle_bb.debit - gle_bb.credit)
                    FROM `tabGL Entry` gle_bb
                    WHERE gle_bb.docstatus = 1
                      AND IFNULL(gle_bb.is_cancelled, 0) = 0
                      AND gle_bb.company = %(company)s
                      AND gle_bb.posting_date < %(from_date)s
                      AND gle_bb.account = g.account
                ), 0)
                + SUM(g.debit)  OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx)
                - SUM(g.credit) OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx)
            ) < 0
            THEN ABS(
                COALESCE((
                    SELECT SUM(gle_bb.debit - gle_bb.credit)
                    FROM `tabGL Entry` gle_bb
                    WHERE gle_bb.docstatus = 1
                      AND IFNULL(gle_bb.is_cancelled, 0) = 0
                      AND gle_bb.company = %(company)s
                      AND gle_bb.posting_date < %(from_date)s
                      AND gle_bb.account = g.account
                ), 0)
                + SUM(g.debit)  OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx)
                - SUM(g.credit) OVER (PARTITION BY g.account ORDER BY g.posting_date, g.voucher_no, g.idx)
            )
            ELSE 0
        END AS balance_credit,
        CONCAT(
            g.account,
            '-2-',
            COALESCE(SUBSTRING_INDEX(g.cost_center, ' - ', 1), LEFT(g.remarks, 2), 'ZZ'),
            '-',
            DATE_FORMAT(g.posting_date, '%%Y%%m%%d'),
            '-',
            LPAD(g.idx, 5, '0')
        ) AS sort_order,
        COALESCE(SUBSTRING_INDEX(g.cost_center, ' - ', 1), LEFT(g.remarks, 2)) AS dept_code
    FROM `tabGL Entry` g
    LEFT JOIN `tabJournal Entry Account` jea
           ON jea.parent = g.voucher_no
          AND jea.name   = g.voucher_detail_no
    LEFT JOIN `tabCustomer` cust_je
           ON cust_je.name = COALESCE(g.party, jea.party)
          AND COALESCE(g.party_type, jea.party_type) = 'Customer'
          AND g.voucher_type = 'Journal Entry'
    LEFT JOIN `tabSupplier` supp_je
           ON supp_je.name = COALESCE(g.party, jea.party)
          AND COALESCE(g.party_type, jea.party_type) = 'Supplier'
          AND g.voucher_type = 'Journal Entry'
    LEFT JOIN `tabEmployee` emp_je
           ON emp_je.name = COALESCE(g.party, jea.party)
          AND COALESCE(g.party_type, jea.party_type) = 'Employee'
          AND g.voucher_type = 'Journal Entry'
    LEFT JOIN `tabPayment Entry` pe ON pe.name = g.voucher_no AND g.voucher_type = 'Payment Entry'
    LEFT JOIN (
        SELECT name AS parent, remarks
        FROM `tabPayment Entry`
        WHERE IFNULL(remarks, '') <> ''
    ) per ON per.parent = g.voucher_no AND g.voucher_type = 'Payment Entry'
    LEFT JOIN `tabJournal Entry`    je ON je.name = g.voucher_no AND g.voucher_type = 'Journal Entry'
    LEFT JOIN `tabSales Invoice`    si ON si.name = g.voucher_no AND g.voucher_type = 'Sales Invoice'
    LEFT JOIN `tabPurchase Invoice` pi ON pi.name = g.voucher_no AND g.voucher_type = 'Purchase Invoice'
    LEFT JOIN `tabPurchase Receipt` pr ON pr.name = g.voucher_no AND g.voucher_type = 'Purchase Receipt'
    LEFT JOIN `tabStock Reconciliation` sr
           ON sr.name = g.voucher_no AND g.voucher_type = 'Stock Reconciliation'
    /* --- Item descriptions from linked invoices via Payment Entry Reference --- */
    /* Single consolidated join: resolves to Purchase Invoice items for Pay,    */
    /* Sales Invoice items for Receive, keyed by (parent, payment_type) so     */
    /* a Payment Entry that somehow references both doctype categories will     */
    /* only match the row corresponding to its actual payment_type.            */
    LEFT JOIN (
        SELECT
            per_ref.parent,
            pe_inner.payment_type,
            GROUP_CONCAT(
                DISTINCT item_desc.description
                ORDER BY item_desc.idx
                SEPARATOR ', '
            ) AS item_descriptions
        FROM `tabPayment Entry Reference` per_ref
        JOIN `tabPayment Entry` pe_inner
            ON pe_inner.name = per_ref.parent
        JOIN (
            /* Purchase Invoice items (for Pay) */
            SELECT pii.parent, pii.description, pii.idx, 'Purchase Invoice' AS ref_doctype
            FROM `tabPurchase Invoice Item` pii
            UNION ALL
            /* Sales Invoice items (for Receive) */
            SELECT sii.parent, sii.description, sii.idx, 'Sales Invoice' AS ref_doctype
            FROM `tabSales Invoice Item` sii
        ) item_desc
            ON item_desc.parent = per_ref.reference_name
           AND item_desc.ref_doctype = per_ref.reference_doctype
        WHERE (
            (per_ref.reference_doctype = 'Purchase Invoice' AND pe_inner.payment_type = 'Pay')
            OR
            (per_ref.reference_doctype = 'Sales Invoice'    AND pe_inner.payment_type = 'Receive')
        )
        GROUP BY per_ref.parent, pe_inner.payment_type
    ) pe_ref_items ON pe_ref_items.parent = g.voucher_no
        AND pe_ref_items.payment_type = COALESCE(g.voucher_subtype, pe.payment_type)
        AND g.voucher_type = 'Payment Entry'
    WHERE g.docstatus = 1
      AND IFNULL(g.is_cancelled, 0) = 0
      AND g.company = %(company)s
      AND g.posting_date BETWEEN %(from_date)s AND %(to_date)s
      AND g.account IN (SELECT account FROM accounts_in_scope)

    UNION ALL

    /* ======== DEPARTMENT SUBTOTAL ROWS (COGS only) ======== */
    SELECT
        NULL AS account,
        NULL AS cost_center,
        NULL AS transaction_date,
        NULL AS doc_type,
        NULL AS doc_type_label,
        NULL AS doc_no,
        NULL AS reference_no,
        NULL AS party,
        CONCAT(
            '<b>',
            TRIM(TRAILING CONCAT(' - ', SUBSTRING_INDEX(g.cost_center, ' - ', -1)) FROM g.cost_center),
            ' SUBTOTAL</b>'
        ) AS particulars,
        NULL AS beginning_balance,
        SUM(g.debit) AS debit,
        SUM(g.credit) AS credit,
        CASE WHEN SUM(g.debit) - SUM(g.credit) > 0 THEN SUM(g.debit) - SUM(g.credit) ELSE 0 END AS net_debit,
        CASE WHEN SUM(g.credit) - SUM(g.debit) > 0 THEN SUM(g.credit) - SUM(g.debit) ELSE 0 END AS net_credit,
        NULL AS balance_debit,
        NULL AS balance_credit,
        CONCAT(
            g.account,
            '-2-',
            COALESCE(SUBSTRING_INDEX(g.cost_center, ' - ', 1), LEFT(g.remarks, 2)),
            '-99999999-99999'
        ) AS sort_order,
        COALESCE(SUBSTRING_INDEX(g.cost_center, ' - ', 1), LEFT(g.remarks, 2)) AS dept_code
    FROM `tabGL Entry` g
    WHERE g.docstatus = 1
      AND IFNULL(g.is_cancelled, 0) = 0
      AND g.company = %(company)s
      AND g.posting_date BETWEEN %(from_date)s AND %(to_date)s
      AND %(account)s = 'Cost of Sales Accounts'
      AND EXISTS (
        SELECT 1 FROM `tabAccount` a
        WHERE a.name = g.account
          AND a.company = %(company)s
          AND a.account_type = 'Cost of Goods Sold'
      )
    GROUP BY
        g.account,
        TRIM(TRAILING CONCAT(' - ', SUBSTRING_INDEX(g.cost_center, ' - ', -1)) FROM g.cost_center)

    UNION ALL

    /* ======== ACCOUNT TOTAL ROW ======== */
    SELECT
        NULL AS account,
        NULL AS cost_center,
        NULL AS transaction_date,
        NULL AS doc_type,
        NULL AS doc_type_label,
        NULL AS doc_no,
        NULL AS reference_no,
        NULL AS party,
        '<b>ACCOUNT TOTAL:</b>' AS particulars,
        NULL AS beginning_balance,
        COALESCE(SUM(gle.debit), 0) AS debit,
        COALESCE(SUM(gle.credit), 0) AS credit,
        CASE WHEN COALESCE(SUM(gle.debit) - SUM(gle.credit), 0) > 0
             THEN COALESCE(SUM(gle.debit) - SUM(gle.credit), 0) ELSE 0 END AS net_debit,
        CASE WHEN COALESCE(SUM(gle.credit) - SUM(gle.debit), 0) > 0
             THEN COALESCE(SUM(gle.credit) - SUM(gle.debit), 0) ELSE 0 END AS net_credit,
        CASE
          WHEN (
            COALESCE((
              SELECT SUM(gle_bb.debit - gle_bb.credit)
              FROM `tabGL Entry` gle_bb
              WHERE gle_bb.docstatus = 1
                AND IFNULL(gle_bb.is_cancelled, 0) = 0
                AND gle_bb.company = %(company)s
                AND gle_bb.posting_date < %(from_date)s
                AND gle_bb.account = ais.account
            ), 0)
            + COALESCE(SUM(gle.debit), 0) - COALESCE(SUM(gle.credit), 0)
          ) > 0
          THEN (
            COALESCE((
              SELECT SUM(gle_bb.debit - gle_bb.credit)
              FROM `tabGL Entry` gle_bb
              WHERE gle_bb.docstatus = 1
                AND IFNULL(gle_bb.is_cancelled, 0) = 0
                AND gle_bb.company = %(company)s
                AND gle_bb.posting_date < %(from_date)s
                AND gle_bb.account = ais.account
            ), 0)
            + COALESCE(SUM(gle.debit), 0) - COALESCE(SUM(gle.credit), 0)
          )
          ELSE 0
        END AS balance_debit,
        CASE
          WHEN (
            COALESCE((
              SELECT SUM(gle_bb.debit - gle_bb.credit)
              FROM `tabGL Entry` gle_bb
              WHERE gle_bb.docstatus = 1
                AND IFNULL(gle_bb.is_cancelled, 0) = 0
                AND gle_bb.company = %(company)s
                AND gle_bb.posting_date < %(from_date)s
                AND gle_bb.account = ais.account
            ), 0)
            + COALESCE(SUM(gle.debit), 0) - COALESCE(SUM(gle.credit), 0)
          ) < 0
          THEN ABS(
            COALESCE((
              SELECT SUM(gle_bb.debit - gle_bb.credit)
              FROM `tabGL Entry` gle_bb
              WHERE gle_bb.docstatus = 1
                AND IFNULL(gle_bb.is_cancelled, 0) = 0
                AND gle_bb.company = %(company)s
                AND gle_bb.posting_date < %(from_date)s
                AND gle_bb.account = ais.account
            ), 0)
            + COALESCE(SUM(gle.debit), 0) - COALESCE(SUM(gle.credit), 0)
          )
          ELSE 0
        END AS balance_credit,
        CONCAT(ais.account, '-3') AS sort_order,
        NULL AS dept_code
    FROM accounts_in_scope ais
    LEFT JOIN `tabGL Entry` gle
      ON gle.account = ais.account
     AND gle.docstatus = 1
     AND IFNULL(gle.is_cancelled, 0) = 0
     AND gle.company = %(company)s
     AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
    GROUP BY ais.account

    UNION ALL

    /* ======== BLANK SEPARATOR ROW ======== */
    SELECT
        NULL AS account,
        NULL AS cost_center,
        NULL AS transaction_date,
        NULL AS doc_type,
        NULL AS doc_type_label,
        NULL AS doc_no,
        NULL AS reference_no,
        NULL AS party,
        '' AS particulars,
        NULL AS beginning_balance,
        NULL AS debit,
        NULL AS credit,
        NULL AS net_debit,
        NULL AS net_credit,
        NULL AS balance_debit,
        NULL AS balance_credit,
        CONCAT(ais.account, '-4') AS sort_order,
        NULL AS dept_code
    FROM accounts_in_scope ais

) combined
ORDER BY sort_order, transaction_date
"""

	return frappe.db.sql(sql, filters, as_dict=True)