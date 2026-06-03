# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	"""
	Main entry point for the BIR Cash Receipts Transaction Prooflist report.
	"""
	if not filters:
		filters = frappe._dict()

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""
	Return column definitions for the BIR Cash Receipts Transaction Prooflist.
	"""
	return [
		{"fieldname": "transaction_date", "label": "Transaction Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "doc_type", "label": "Doc Type", "fieldtype": "Data", "width": 120},
		{"fieldname": "doc_no_html", "label": "Doc No", "fieldtype": "HTML", "width": 140},
		{"fieldname": "bank_account", "label": "Bank Account", "fieldtype": "Data", "width": 260},
		{"fieldname": "customer_name", "label": "Customer Name", "fieldtype": "Link", "options": "Customer", "width": 220},
		{"fieldname": "reference_html", "label": "Reference", "fieldtype": "HTML", "width": 120},
		{"fieldname": "account", "label": "Account", "fieldtype": "Data", "width": 280},
		{"fieldname": "cost_center", "label": "Cost Center", "fieldtype": "Link", "options": "Cost Center", "width": 150},
		{"fieldname": "paid_amount", "label": "Paid Amount", "fieldtype": "Currency", "width": 120},
		{"fieldname": "description", "label": "Description", "fieldtype": "Data", "width": 300},
		{"fieldname": "reference_invoice", "label": "Reference Invoice", "fieldtype": "Data", "width": 200},
		{"fieldname": "reference_date", "label": "Reference Date", "fieldtype": "Date", "width": 120},
		{"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 120},
		{"fieldname": "applied", "label": "Applied", "fieldtype": "Currency", "width": 120},
		{"fieldname": "project", "label": "Project", "fieldtype": "Link", "options": "Project", "width": 140},
		{"fieldname": "tin_number", "label": "TIN Number", "fieldtype": "Data", "width": 150},
	]


def get_data(filters):
	"""
	Fetch cash receipts transaction data from GL Entry with subtotals and grand total.
	"""
	if not all([filters.get("company"), filters.get("from_date"), filters.get("to_date"), filters.get("status")]):
		return []

	sql = """
		SELECT
			transaction_date,
			doc_type,
			doc_no_html,
			bank_account,
			customer_name,
			reference_html,
			account,
			cost_center,
			paid_amount,
			description,
			reference_invoice,
			reference_date,
			amount,
			applied,
			project,
			tin_number
		FROM (
			/* ======================= DETAIL ROWS ======================= */
			SELECT
				CASE
					WHEN gle.voucher_type = 'Journal Entry' THEN (
						SELECT je.cheque_date
						FROM `tabJournal Entry` je
						WHERE je.name = gle.voucher_no
					)
					WHEN gle.voucher_type = 'Sales Invoice' THEN (
						SELECT si.posting_date
						FROM `tabSales Invoice` si
						WHERE si.name = gle.voucher_no
					)
					ELSE gle.posting_date
				END AS transaction_date,

				CASE
					WHEN gle.voucher_type = 'Payment Entry' THEN (
						SELECT CONCAT(gle.voucher_type, ' - ', pe.payment_type)
						FROM `tabPayment Entry` pe
						WHERE pe.name = gle.voucher_no
					)
					ELSE gle.voucher_type
				END AS doc_type,

				CONCAT(
					'<a href="/app/',
					LOWER(REPLACE(gle.voucher_type, ' ', '-')),
					'/', gle.voucher_no, '">',
					gle.voucher_no, '</a>'
				) AS doc_no_html,

				CASE
					WHEN gle.voucher_type = 'Journal Entry' THEN (
						SELECT CONCAT(a2.account_number, ' - ', a2.account_name)
						FROM `tabGL Entry` gle2
						JOIN `tabAccount` a2 ON a2.name = gle2.account
						WHERE gle2.voucher_no = gle.voucher_no
							AND a2.account_number LIKE '12%%'
							AND gle2.is_cancelled = gle.is_cancelled
						LIMIT 1
					)
					ELSE (
						SELECT CONCAT(a2.account_number, ' - ', a2.account_name)
						FROM `tabPayment Entry` pe2
						JOIN `tabAccount` a2 ON a2.name = pe2.paid_to
						WHERE pe2.name = gle.voucher_no
					)
				END AS bank_account,

				COALESCE(c.customer_name, gle.party) AS customer_name,

				CASE
					WHEN gle.voucher_type = 'Sales Invoice' THEN (
						SELECT COALESCE(si.remarks, '')
						FROM `tabSales Invoice` si
						WHERE si.name = gle.voucher_no
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
					WHEN gle.voucher_type = 'Journal Entry' THEN (
						SELECT COALESCE(gle2.debit, 0)
						FROM `tabGL Entry` gle2
						JOIN `tabAccount` a2 ON a2.name = gle2.account
						WHERE gle2.voucher_no = gle.voucher_no
							AND a2.account_number LIKE '12%%'
							AND gle2.is_cancelled = gle.is_cancelled
						LIMIT 1
					)
					ELSE (
						SELECT COALESCE(pe.paid_amount, 0)
						FROM `tabPayment Entry` pe
						WHERE pe.name = gle.voucher_no
					)
				END AS paid_amount,

				CASE
					WHEN a.account_number LIKE '1203%%' OR a.account_number LIKE '1205%%' THEN (
						SELECT COALESCE(pe.reference_no, '')
						FROM `tabPayment Entry` pe
						WHERE pe.name = gle.voucher_no
					)
					WHEN a.account_number LIKE '1301%%' THEN (
						SELECT GROUP_CONCAT(DISTINCT per.reference_name SEPARATOR '; ')
						FROM `tabPayment Entry Reference` per
						WHERE per.parent = gle.voucher_no
							AND per.reference_name IS NOT NULL
							AND per.reference_name != ''
					)
					WHEN a.account_number LIKE '1604%%' THEN COALESCE(ped.description, '')
					WHEN gle.voucher_type = 'Sales Invoice' THEN (
						SELECT GROUP_CONCAT(DISTINCT sii.description SEPARATOR '; ')
						FROM `tabSales Invoice Item` sii
						WHERE sii.parent = gle.voucher_no
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

				(
					SELECT per.reference_name
					FROM `tabPayment Entry Reference` per
					WHERE per.parent = gle.voucher_no
						AND per.reference_name = gle.against_voucher
					LIMIT 1
				) AS reference_invoice,

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
						SELECT si.posting_date
						FROM `tabSales Invoice` si
						WHERE si.name = gle.voucher_no
					)
					ELSE gle.posting_date
				END AS reference_date,

				CASE
					WHEN gle.voucher_type = 'Journal Entry'
						THEN COALESCE(gle.credit, 0) - COALESCE(gle.debit, 0)
					WHEN a.account_number LIKE '1604%%' THEN (
						SELECT p2.allocated_amount
						FROM `tabPayment Entry Reference` p2
						WHERE p2.parent = gle.voucher_no
							AND p2.reference_name = gle.against_voucher
						LIMIT 1
					)
					ELSE (
						SELECT per.allocated_amount
						FROM `tabPayment Entry Reference` per
						WHERE per.parent = gle.voucher_no
							AND per.reference_name = gle.against_voucher
						LIMIT 1
					)
				END AS amount,

				CASE
					WHEN a.account_number LIKE '1301%%' THEN (
						SELECT per.allocated_amount
						FROM `tabPayment Entry Reference` per
						WHERE per.parent = gle.voucher_no
							AND per.reference_name = gle.against_voucher
						LIMIT 1
					)
					WHEN a.account_number LIKE '1203%%' OR a.account_number LIKE '1205%%' THEN (
						SELECT COALESCE(SUM(per.allocated_amount), 0)
						FROM `tabPayment Entry Reference` per
						WHERE per.parent = gle.voucher_no
					)
					WHEN a.account_number LIKE '1604%%' THEN COALESCE(ped.amount, 0) * -1
					WHEN gle.voucher_type = 'Journal Entry'
						THEN COALESCE(gle.credit, 0) - COALESCE(gle.debit, 0)
					ELSE COALESCE(gle.debit, 0) - COALESCE(gle.credit, 0)
				END AS applied,

				COALESCE(gle.project, '') AS project,

				CASE
					WHEN gle.party_type = 'Customer' THEN COALESCE(c.tax_id, '')
					ELSE ''
				END AS tin_number,

				CASE
					WHEN a.account_number LIKE '1604%%' THEN (
						SELECT p2.reference_name
						FROM `tabPayment Entry Reference` p2
						WHERE p2.parent = gle.voucher_no
							AND p2.reference_name = gle.against_voucher
						LIMIT 1
					)
					ELSE gle.against_voucher
				END AS ref_sort_key,

				CONCAT(
					gle.posting_date, '-', gle.voucher_no, '-1-',
					LPAD(
						COALESCE(
							CASE
								WHEN a.account_number LIKE '1604%%' THEN (
									SELECT p2.idx
									FROM `tabPayment Entry Reference` p2
									WHERE p2.parent = gle.voucher_no
										AND p2.reference_name = gle.against_voucher
									LIMIT 1
								)
								ELSE (
									SELECT per.idx
									FROM `tabPayment Entry Reference` per
									WHERE per.parent = gle.voucher_no
										AND per.reference_name = gle.against_voucher
									LIMIT 1
								)
							END
						, 99999), 5, '0'
					),
					'-',
					CASE
						WHEN a.account_number LIKE '1301%%' THEN '01'
						WHEN a.account_number LIKE '1604%%' THEN '02'
						ELSE '99'
					END,
					'-', LPAD(gle.idx, 5, '0')
				) AS sort_order

			FROM `tabGL Entry` gle
			JOIN `tabAccount` a ON a.name = gle.account
			LEFT JOIN `tabPayment Entry Deduction` ped
				ON ped.parent = gle.voucher_no
				AND ped.account = gle.account
			LEFT JOIN `tabCustomer` c
				ON c.name = gle.party
				AND gle.party_type = 'Customer'
			WHERE
				(
					%(status)s = 'All'
					OR (%(status)s = 'Cancelled Only' AND gle.is_cancelled = 1)
					OR (%(status)s = 'Posted Only' AND gle.is_cancelled = 0)
				)
				AND gle.company = %(company)s
				AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND (
					(
						gle.voucher_type = 'Payment Entry'
						AND EXISTS (
							SELECT 1 FROM `tabPayment Entry` pe
							WHERE pe.name = gle.voucher_no AND pe.payment_type = 'Receive'
						)
					)
					OR (
						gle.voucher_type = 'Journal Entry'
						AND (
							gle.voucher_no LIKE 'ACC-JVC-%%'
							OR (
								gle.voucher_no LIKE 'ACC-JVC%%'
								AND (
									SELECT je.user_remark
									FROM `tabJournal Entry` je
									WHERE je.name = gle.voucher_no
								) LIKE '%%VP#%%'
							)
						)
					)
				)
				AND a.account_number NOT LIKE '12%%'

			UNION ALL

			/* ======================= SUBTOTAL ROWS ======================= */
			SELECT
				'' AS transaction_date,
				'' AS doc_type,
				'' AS doc_no_html,
				'' AS bank_account,
				'' AS customer_name,
				'' AS reference_html,
				'' AS account,
				'' AS cost_center,
				NULL AS paid_amount,
				'<b>SUBTOTAL</b>' AS description,
				'' AS reference_invoice,
				NULL AS reference_date,
				SUM(
					CASE
						WHEN a.account_number LIKE '1301%%' THEN (
							SELECT COALESCE(SUM(per.allocated_amount), 0)
							FROM `tabPayment Entry Reference` per
							WHERE per.parent = gle.voucher_no
								AND per.reference_name = gle.against_voucher
						)
						WHEN gle.voucher_type = 'Journal Entry'
							AND a.account_number NOT LIKE '12%%'
							THEN COALESCE(gle.credit, 0) - COALESCE(gle.debit, 0)
						ELSE 0
					END
				) AS amount,
				SUM(
					CASE
						WHEN a.account_number LIKE '1301%%' THEN (
							SELECT COALESCE(SUM(per.allocated_amount), 0)
							FROM `tabPayment Entry Reference` per
							WHERE per.parent = gle.voucher_no
								AND per.reference_name = gle.against_voucher
						)
						WHEN a.account_number LIKE '1604%%' THEN (
							SELECT COALESCE(SUM(ped.amount), 0) * -1
							FROM `tabPayment Entry Deduction` ped
							WHERE ped.parent = gle.voucher_no
								AND ped.account = gle.account
						)
						WHEN a.account_number LIKE '12%%' THEN 0
						ELSE COALESCE(gle.credit, 0) - COALESCE(gle.debit, 0)
					END
				) AS applied,
				'' AS project,
				'' AS tin_number,
				NULL AS ref_sort_key,
				CONCAT(gle.posting_date, '-', gle.voucher_no, '-2-0-00000') AS sort_order

			FROM `tabGL Entry` gle
			JOIN `tabAccount` a ON a.name = gle.account
			WHERE
				(
					%(status)s = 'All'
					OR (%(status)s = 'Cancelled Only' AND gle.is_cancelled = 1)
					OR (%(status)s = 'Posted Only' AND gle.is_cancelled = 0)
				)
				AND gle.company = %(company)s
				AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND (
					(
						gle.voucher_type = 'Payment Entry'
						AND EXISTS (
							SELECT 1 FROM `tabPayment Entry` pe
							WHERE pe.name = gle.voucher_no AND pe.payment_type = 'Receive'
						)
					)
					OR (
						gle.voucher_type = 'Journal Entry'
						AND (
							gle.voucher_no LIKE 'ACC-JVC-%%'
							OR (
								gle.voucher_no LIKE 'ACC-JVC%%'
								AND (
									SELECT je.user_remark
									FROM `tabJournal Entry` je
									WHERE je.name = gle.voucher_no
								) LIKE '%%VP#%%'
							)
						)
					)
				)
			GROUP BY gle.posting_date, gle.voucher_no

			UNION ALL

			/* ======================= EMPTY SPACER ROWS ======================= */
			SELECT
				'' AS transaction_date,
				'' AS doc_type,
				'' AS doc_no_html,
				'' AS bank_account,
				'' AS customer_name,
				'' AS reference_html,
				'' AS account,
				'' AS cost_center,
				NULL AS paid_amount,
				'' AS description,
				'' AS reference_invoice,
				NULL AS reference_date,
				NULL AS amount,
				NULL AS applied,
				'' AS project,
				'' AS tin_number,
				NULL AS ref_sort_key,
				CONCAT(gle.posting_date, '-', gle.voucher_no, '-3-0-00000') AS sort_order

			FROM `tabGL Entry` gle
			WHERE
				(
					%(status)s = 'All'
					OR (%(status)s = 'Cancelled Only' AND gle.is_cancelled = 1)
					OR (%(status)s = 'Posted Only' AND gle.is_cancelled = 0)
				)
				AND gle.company = %(company)s
				AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND (
					(
						gle.voucher_type = 'Payment Entry'
						AND EXISTS (
							SELECT 1 FROM `tabPayment Entry` pe
							WHERE pe.name = gle.voucher_no AND pe.payment_type = 'Receive'
						)
					)
					OR (
						gle.voucher_type = 'Journal Entry'
						AND (
							gle.voucher_no LIKE 'ACC-JVC-%%'
							OR (
								gle.voucher_no LIKE 'ACC-JVC%%'
								AND (
									SELECT je.user_remark
									FROM `tabJournal Entry` je
									WHERE je.name = gle.voucher_no
								) LIKE '%%VP#%%'
							)
						)
					)
				)
			GROUP BY gle.posting_date, gle.voucher_no

			UNION ALL

			/* ======================= GRAND TOTAL ROW ======================= */
			SELECT
				'' AS transaction_date,
				'' AS doc_type,
				'' AS doc_no_html,
				'' AS bank_account,
				'' AS customer_name,
				'' AS reference_html,
				'' AS account,
				'' AS cost_center,
				NULL AS paid_amount,
				'<b>GRAND TOTAL</b>' AS description,
				'' AS reference_invoice,
				NULL AS reference_date,
				SUM(amount) AS amount,
				SUM(applied) AS applied,
				'' AS project,
				'' AS tin_number,
				NULL AS ref_sort_key,
				'ZZZZZZZZZZ' AS sort_order

			FROM (
				SELECT
					SUM(
						CASE
							WHEN a.account_number LIKE '1301%%' THEN (
								SELECT COALESCE(SUM(per.allocated_amount), 0)
								FROM `tabPayment Entry Reference` per
								WHERE per.parent = gle.voucher_no
									AND per.reference_name = gle.against_voucher
							)
							WHEN gle.voucher_type = 'Journal Entry'
								AND a.account_number NOT LIKE '12%%'
								THEN COALESCE(gle.credit, 0) - COALESCE(gle.debit, 0)
							ELSE 0
						END
					) AS amount,
					SUM(
						CASE
							WHEN a.account_number LIKE '1301%%' THEN (
								SELECT COALESCE(SUM(per.allocated_amount), 0)
								FROM `tabPayment Entry Reference` per
								WHERE per.parent = gle.voucher_no
									AND per.reference_name = gle.against_voucher
							)
							WHEN a.account_number LIKE '1604%%' THEN (
								SELECT COALESCE(SUM(ped.amount), 0) * -1
								FROM `tabPayment Entry Deduction` ped
								WHERE ped.parent = gle.voucher_no
									AND ped.account = gle.account
							)
							WHEN a.account_number LIKE '12%%' THEN 0
							ELSE COALESCE(gle.credit, 0) - COALESCE(gle.debit, 0)
						END
					) AS applied

				FROM `tabGL Entry` gle
				JOIN `tabAccount` a ON a.name = gle.account
				WHERE
					(
						%(status)s = 'All'
						OR (%(status)s = 'Cancelled Only' AND gle.is_cancelled = 1)
						OR (%(status)s = 'Posted Only' AND gle.is_cancelled = 0)
					)
					AND gle.company = %(company)s
					AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND (
						(
							gle.voucher_type = 'Payment Entry'
							AND EXISTS (
								SELECT 1 FROM `tabPayment Entry` pe
								WHERE pe.name = gle.voucher_no AND pe.payment_type = 'Receive'
							)
						)
						OR (
							gle.voucher_type = 'Journal Entry'
							AND (
								gle.voucher_no LIKE 'ACC-JVC-%%'
								OR (
									gle.voucher_no LIKE 'ACC-JVC%%'
									AND (
										SELECT je.user_remark
										FROM `tabJournal Entry` je
										WHERE je.name = gle.voucher_no
									) LIKE '%%VP#%%'
								)
							)
						)
					)
				GROUP BY gle.posting_date, gle.voucher_no
			) subtotal_rows

		) combined_results

		ORDER BY sort_order
	"""

	return frappe.db.sql(sql, filters, as_dict=True)