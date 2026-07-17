# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	"""
	Main entry point for the BIR General Ledger Transaction Listing report.
	"""
	if not filters:
		filters = frappe._dict()

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""
	Return column definitions for the BIR General Ledger Transaction Listing.
	"""
	return [
		{"fieldname": "transaction_date", "label": "Transaction Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "doc_no", "label": "Doc No", "fieldtype": "Link", "options": "Journal Entry", "width": 150},
		{"fieldname": "doc_type", "label": "Doc Type", "fieldtype": "Data", "width": 120},
		{"fieldname": "invoice_no", "label": "Reference", "fieldtype": "Data", "width": 160},
		{"fieldname": "account", "label": "Account", "fieldtype": "Link", "options": "Account", "width": 200},
		{"fieldname": "cost_center", "label": "Dept Code", "fieldtype": "Link", "options": "Cost Center", "width": 150},
		{"fieldname": "description", "label": "Description", "fieldtype": "Data", "width": 250},
		{"fieldname": "debit", "label": "Debit", "fieldtype": "Currency", "width": 120},
		{"fieldname": "credit", "label": "Credit", "fieldtype": "Currency", "width": 120},
		{"fieldname": "project", "label": "Project", "fieldtype": "Link", "options": "Project", "width": 160},
		{"fieldname": "party", "label": "Customer/Supplier", "fieldtype": "Data", "width": 200},
	]


def get_data(filters):
	"""
	Fetch Journal Entry transaction data with subtotal and blank separator rows.
	"""

	sql = """
		SELECT
			transaction_date AS transaction_date,
			doc_no           AS doc_no,
			doc_type         AS doc_type,
			invoice_no       AS invoice_no,
			account          AS account,
			cost_center      AS cost_center,
			description      AS description,
			debit            AS debit,
			credit           AS credit,
			project          AS project,
			party            AS party
		FROM (
			/* ======================= DETAIL ROWS ======================= */
			SELECT
				je.posting_date                                       AS transaction_date,
				je.name                                               AS doc_no,
				je.voucher_type                                       AS doc_type,
				jea.account                                           AS account,
				jea.cost_center                                       AS cost_center,
				jea.user_remark                                       AS description,
				jea.debit                                             AS debit,
				jea.credit                                            AS credit,
				je.user_remark                                        AS invoice_no,
				jea.project                                           AS project,
				jea.party                                             AS party,
				CONCAT(je.posting_date, '-', je.name, '-1-', LPAD(jea.idx, 5, '0')) AS sort_order
			FROM `tabJournal Entry` je
			JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			WHERE
				je.docstatus = 1
				AND je.company = %(company)s
				AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND je.voucher_type IN ('Journal Entry', 'Depreciation Entry')

			UNION ALL

			/* ======================= SUBTOTAL ROWS ======================= */
			SELECT
				NULL                                                  AS transaction_date,
				''                                                    AS doc_no,
				''                                                    AS doc_type,
				''                                                    AS account,
				''                                                    AS cost_center,
				'<b>SUBTOTAL</b>'                                     AS description,
				SUM(jea.debit)                                        AS debit,
				SUM(jea.credit)                                       AS credit,
				''                                                    AS invoice_no,
				''                                                    AS project,
				''                                                    AS party,
				CONCAT(je.posting_date, '-', je.name, '-2-00000')     AS sort_order
			FROM `tabJournal Entry` je
			JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			WHERE
				je.docstatus = 1
				AND je.company = %(company)s
				AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND je.voucher_type IN ('Journal Entry', 'Depreciation Entry')
			GROUP BY je.posting_date, je.name

			UNION ALL

			/* ======================= BLANK ROWS ======================= */
			SELECT
				NULL                                                  AS transaction_date,
				''                                                    AS doc_no,
				''                                                    AS doc_type,
				''                                                    AS account,
				''                                                    AS cost_center,
				''                                                    AS description,
				NULL                                                  AS debit,
				NULL                                                  AS credit,
				''                                                    AS invoice_no,
				''                                                    AS project,
				''                                                    AS party,
				CONCAT(je.posting_date, '-', je.name, '-3-00000')     AS sort_order
			FROM `tabJournal Entry` je
			WHERE
				je.docstatus = 1
				AND je.company = %(company)s
				AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND je.voucher_type IN ('Journal Entry', 'Depreciation Entry')

		) AS combined
		ORDER BY combined.sort_order
	"""

	return frappe.db.sql(sql, filters, as_dict=True)