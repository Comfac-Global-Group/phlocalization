# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": "Date", "fieldname": "date_col", "fieldtype": "Date", "width": 110},
		{"label": "Doc No", "fieldname": "doc_no", "fieldtype": "Link", "options": "Journal Entry", "width": 200},
		{"label": "Account", "fieldname": "account", "fieldtype": "Data", "width": 200},
		{"label": "Reference", "fieldname": "reference", "fieldtype": "Data", "width": 160},
		{"label": "Brief Description/Explanation", "fieldname": "description", "fieldtype": "Data", "width": 250},
		{"label": "Debits", "fieldname": "debits", "fieldtype": "Currency", "width": 130},
		{"label": "Credits", "fieldname": "credits", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	return frappe.db.sql(
		"""
		SELECT
			date_col        AS "date_col",
			doc_no          AS "doc_no",
			account         AS "account",
			reference       AS "reference",
			description     AS "description",
			debits          AS "debits",
			credits         AS "credits"
		FROM (
			/* DETAIL ROWS */
			SELECT
				CONCAT(je.posting_date, '|', je.name, '|1|', LPAD(jea.idx, 5, '0')) AS sort_key,
				CASE WHEN jea.idx = (
					SELECT MIN(j2.idx) FROM `tabJournal Entry Account` j2 WHERE j2.parent = je.name
				) THEN je.posting_date ELSE NULL END AS date_col,
				CASE WHEN jea.idx = (
					SELECT MIN(j2.idx) FROM `tabJournal Entry Account` j2 WHERE j2.parent = je.name
				) THEN je.name ELSE '' END AS doc_no,
				jea.account AS account,
				CASE WHEN jea.idx = (
					SELECT MIN(j2.idx) FROM `tabJournal Entry Account` j2 WHERE j2.parent = je.name
				) THEN IFNULL(je.cheque_no, '') ELSE '' END AS reference,
				IFNULL(jea.user_remark, IFNULL(je.user_remark, '')) AS description,
				IFNULL(jea.debit_in_account_currency,  0) AS debits,
				IFNULL(jea.credit_in_account_currency, 0) AS credits
			FROM `tabJournal Entry` je
			INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			WHERE
				je.docstatus = 1
				AND je.voucher_type IN ('Journal Entry', 'Depreciation Entry')
				AND je.company = %(company)s
				AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s

			UNION ALL

			/* SUBTOTAL ROW per JV */
			SELECT
				CONCAT(je.posting_date, '|', je.name, '|2|SUBTOTAL') AS sort_key,
				NULL AS date_col,
				'' AS doc_no,
				'<b>SUBTOTAL</b>' AS account,
				'' AS reference,
				'' AS description,
				SUM(IFNULL(jea.debit_in_account_currency,  0)) AS debits,
				SUM(IFNULL(jea.credit_in_account_currency, 0)) AS credits
			FROM `tabJournal Entry` je
			INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			WHERE
				je.docstatus = 1
				AND je.voucher_type IN ('Journal Entry', 'Depreciation Entry')
				AND je.company = %(company)s
				AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
			GROUP BY je.posting_date, je.name

			UNION ALL

			/* BLANK SEPARATOR ROW per JV */
			SELECT
				CONCAT(je.posting_date, '|', je.name, '|3|BLANK') AS sort_key,
				NULL AS date_col,
				'' AS doc_no,
				'' AS account,
				'' AS reference,
				'' AS description,
				NULL AS debits,
				NULL AS credits
			FROM `tabJournal Entry` je
			WHERE
				je.docstatus = 1
				AND je.voucher_type IN ('Journal Entry', 'Depreciation Entry')
				AND je.company = %(company)s
				AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
		) AS combined
		ORDER BY sort_key
		""",
		filters,
		as_dict=True,
	)
