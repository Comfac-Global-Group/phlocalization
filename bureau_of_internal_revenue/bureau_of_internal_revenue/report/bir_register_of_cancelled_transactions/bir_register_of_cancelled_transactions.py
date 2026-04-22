# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": "Doc Type", "fieldname": "doc_type", "fieldtype": "Data", "width": 120},
		{"label": "Doc No", "fieldname": "doc_no_html", "fieldtype": "HTML", "width": 140},
		{"label": "Customer Name", "fieldname": "Customer_name", "fieldtype": "Link", "options": "Customer", "width": 220},
		{"label": "Reference", "fieldname": "reference_html", "fieldtype": "HTML", "width": 120},
		{"label": "Account", "fieldname": "account", "fieldtype": "Data", "width": 280},
		{"label": "Cost Center", "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 150},
		{"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 300},
		{"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
		{"label": "TIN Number", "fieldname": "tin_number", "fieldtype": "Data", "width": 150},
	]


def get_data(filters):
	return frappe.db.sql("""
	SELECT
		transaction_date,
		doc_type,
		doc_no_html,
		Customer_name,
		reference_html,
		account,
		cost_center,
		description,
		debit,
		credit,
		project,
		currency,
		tin_number
	FROM (

		-- =========================
		-- Detail rows
		-- =========================
		SELECT
			CASE 
				WHEN gle.voucher_type = 'Journal Entry' THEN (
					SELECT je.cheque_date 
					FROM `tabJournal Entry` je 
					WHERE je.name = gle.voucher_no
				)
				WHEN gle.voucher_type = 'Payment Entry' THEN (
					SELECT pe.reference_date 
					FROM `tabPayment Entry` pe 
					WHERE pe.name = gle.voucher_no
				)
				WHEN gle.voucher_type = 'Sales Invoice' THEN (
					SELECT pi.posting_date 
					FROM `tabSales Invoice` pi 
					WHERE pi.name = gle.voucher_no
				)
				ELSE gle.posting_date
			END AS transaction_date,

			gle.voucher_type AS doc_type,

			CONCAT(
				'<a href="/app/', 
				LOWER(REPLACE(gle.voucher_type, ' ', '-')), 
				'/', 
				gle.voucher_no, 
				'">', 
				gle.voucher_no, 
				'</a>'
			) AS doc_no_html,

			gle.party AS Customer_name,

			CASE 
				WHEN gle.voucher_type = 'Sales Invoice' THEN (
					SELECT COALESCE(pi.remarks, '') 
					FROM `tabSales Invoice` pi 
					WHERE pi.name = gle.voucher_no
				)
				WHEN gle.voucher_type = 'Journal Entry' THEN (
					SELECT COALESCE(je.cheque_no, '') 
					FROM `tabJournal Entry` je 
					WHERE je.name = gle.voucher_no
				)
				WHEN gle.voucher_type = 'Payment Entry' THEN (
					SELECT COALESCE(pe.reference_no, '') 
					FROM `tabPayment Entry` pe 
					WHERE pe.name = gle.voucher_no
				)
				ELSE COALESCE(gle.against_voucher, '')
			END AS reference_html,

			CONCAT(a.account_number, ' - ', a.account_name) AS account,
			COALESCE(gle.cost_center, '') AS cost_center,

			CASE 
				WHEN gle.voucher_type = 'Sales Invoice' THEN (
					SELECT GROUP_CONCAT(DISTINCT pii.description SEPARATOR '; ')
					FROM `tabSales Invoice Item` pii
					WHERE pii.parent = gle.voucher_no
				)
				WHEN gle.voucher_type = 'Journal Entry' THEN (
					SELECT COALESCE(jea.user_remark, '')
					FROM `tabJournal Entry Account` jea
					WHERE jea.parent = gle.voucher_no
						AND jea.account = gle.account
						AND COALESCE(jea.debit, 0) = COALESCE(gle.debit, 0)
						AND COALESCE(jea.credit, 0) = COALESCE(gle.credit, 0)
					LIMIT 1
				)
				ELSE COALESCE(gle.remarks, '')
			END AS description,

			-- FIX: Use account currency amounts for foreign currency transactions
			COALESCE(gle.debit_in_account_currency, gle.debit, 0) AS debit,
			COALESCE(gle.credit_in_account_currency, gle.credit, 0) AS credit,

			COALESCE(gle.project, '') AS project,

			-- FIX: Use account_currency from GLE, fallback to company default via JOIN
			COALESCE(gle.account_currency, co.default_currency) AS currency,

			CASE 
				WHEN gle.party_type = 'Customer' THEN (
					SELECT s.tax_id 
					FROM `tabCustomer` s 
					WHERE s.name = gle.party
				)
				ELSE ''
			END AS tin_number,

			CONCAT(
				gle.posting_date, '-', 
				gle.voucher_no, '-1-',
				CASE 
					WHEN gle.credit > 0 THEN '1'
					WHEN gle.debit > 0 THEN '2'
					ELSE '9'
				END,
				'-', LPAD(gle.idx, 5, '0')
			) AS sort_order

		FROM `tabGL Entry` gle
		JOIN `tabAccount` a ON a.name = gle.account
		JOIN `tabCompany` co ON co.name = gle.company  -- FIX: JOIN instead of correlated subquery

		WHERE gle.is_cancelled = 1
			AND gle.company = %(company)s
			AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND COALESCE(gle.remarks, '') NOT LIKE 'On cancellation of%%'


		UNION ALL

		-- =========================
		-- Subtotal rows
		-- =========================
		SELECT
			NULL AS transaction_date,
			'' AS doc_type,
			'' AS doc_no_html,
			'' AS Customer_name,
			'' AS reference_html,
			'' AS account,
			'' AS cost_center,
			'<b>SUBTOTAL</b>' AS description,

			-- FIX: Sum account currency amounts to match detail rows
			SUM(COALESCE(gle.debit_in_account_currency, gle.debit, 0)) AS debit,
			SUM(COALESCE(gle.credit_in_account_currency, gle.credit, 0)) AS credit,

			'' AS project,

			-- FIX: JOIN to get currency reliably in GROUP BY context
			co.default_currency AS currency,

			'' AS tin_number,

			CONCAT(gle.posting_date, '-', gle.voucher_no, '-2-0-00000') AS sort_order

		FROM `tabGL Entry` gle
		JOIN `tabCompany` co ON co.name = gle.company  -- FIX: JOIN instead of correlated subquery

		WHERE gle.is_cancelled = 1
			AND gle.company = %(company)s
			AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND COALESCE(gle.remarks, '') NOT LIKE 'On cancellation of%%'
		GROUP BY gle.posting_date, gle.voucher_no, co.default_currency


		UNION ALL

		-- =========================
		-- Empty rows
		-- =========================
		SELECT
			NULL AS transaction_date,
			'' AS doc_type,
			'' AS doc_no_html,
			'' AS Customer_name,
			'' AS reference_html,
			'' AS account,
			'' AS cost_center,
			'' AS description,
			NULL AS debit,
			NULL AS credit,
			'' AS project,

			-- FIX: JOIN to get currency reliably in GROUP BY context
			co.default_currency AS currency,

			'' AS tin_number,

			CONCAT(gle.posting_date, '-', gle.voucher_no, '-3-0-00000') AS sort_order

		FROM `tabGL Entry` gle
		JOIN `tabCompany` co ON co.name = gle.company  -- FIX: JOIN instead of correlated subquery

		WHERE gle.is_cancelled = 1
			AND gle.company = %(company)s
			AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND COALESCE(gle.remarks, '') NOT LIKE 'On cancellation of%%'
		GROUP BY gle.posting_date, gle.voucher_no, co.default_currency

	) combined_results

	ORDER BY sort_order;
	""", filters, as_dict=True)