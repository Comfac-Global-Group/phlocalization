# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	filters = validate_filters(filters or {})
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("Company is required"))

	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required"))

	if filters.get("from_date") > filters.get("to_date"):
		frappe.throw(_("From Date cannot be greater than To Date"))

	return filters


def get_columns():
	return [
		{"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": "Doc Type", "fieldname": "doc_type", "fieldtype": "Data", "width": 120},
		{"label": "Doc No", "fieldname": "doc_no_html", "fieldtype": "HTML", "width": 140},
		{"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Link", "options": "Customer", "width": 220},
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
	query = """
		SELECT
			transaction_date,
			doc_type,
			doc_no_html,
			customer_name,
			reference_html,
			account,
			cost_center,
			description,
			debit,
			credit,
			project,
			tin_number,
			currency,
			row_type
		FROM (
			-- Detail rows
			SELECT
				gle.posting_date,
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

				CASE 
					WHEN gle.party_type = 'Customer' THEN COALESCE(
						(SELECT c.customer_name FROM `tabCustomer` c WHERE c.name = gle.party),
						gle.party
					)
					ELSE gle.party
				END AS customer_name,

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
						LIMIT 1
					)
					ELSE COALESCE(gle.remarks, '')
				END AS description,

				COALESCE(gle.debit, 0) AS debit,
				COALESCE(gle.credit, 0) AS credit,
				COALESCE(gle.project, '') AS project,

				comp.default_currency AS currency,

				CASE 
					WHEN gle.party_type = 'Customer' THEN (
						SELECT s.tax_id 
						FROM `tabCustomer` s 
						WHERE s.name = gle.party
					)
					ELSE ''
				END AS tin_number,

				'detail' AS row_type,

				CONCAT(
					gle.posting_date, '-', 
					gle.voucher_no, '-1-',
					CASE 
						WHEN gle.credit > 0 THEN '3'
						WHEN gle.debit > 0 AND a.account_number LIKE '1301%%' THEN '1'
						WHEN gle.debit > 0 THEN '2'
						ELSE '9'
					END,
					'-', LPAD(gle.idx, 5, '0')
				) AS sort_order

			FROM `tabGL Entry` gle
			JOIN `tabAccount` a ON a.name = gle.account
			JOIN `tabCompany` comp ON comp.name = gle.company

			WHERE gle.is_cancelled = 0
			  AND gle.company = %(company)s
			  AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			  AND EXISTS (
				  SELECT 1 
				  FROM `tabGL Entry` gle2
				  JOIN `tabAccount` a2 ON a2.name = gle2.account
				  WHERE gle2.voucher_no = gle.voucher_no
					AND gle2.is_cancelled = 0
					AND a2.account_number LIKE '1301%%'
					AND gle2.debit > 0
			  )

			UNION ALL

			-- Subtotal rows
			SELECT
				gle.posting_date,
				'' AS doc_type,
				'' AS doc_no_html,
				'' AS customer_name,
				'' AS reference_html,
				NULL AS transaction_date,
				'' AS account,
				'' AS cost_center,
				'<b>SUBTOTAL</b>' AS description,
				SUM(COALESCE(gle.debit, 0)) AS debit,
				SUM(COALESCE(gle.credit, 0)) AS credit,
				'' AS project,

				comp.default_currency AS currency,

				'' AS tin_number,

				'subtotal' AS row_type,

				CONCAT(gle.posting_date, '-', gle.voucher_no, '-2-0-00000') AS sort_order

			FROM `tabGL Entry` gle
			JOIN `tabAccount` a ON a.name = gle.account
			JOIN `tabCompany` comp ON comp.name = gle.company

			WHERE gle.is_cancelled = 0
			  AND gle.company = %(company)s
			  AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			  AND EXISTS (
				  SELECT 1 
				  FROM `tabGL Entry` gle2
				  JOIN `tabAccount` a2 ON a2.name = gle2.account
				  WHERE gle2.voucher_no = gle.voucher_no
					AND gle2.is_cancelled = 0
					AND a2.account_number LIKE '1301%%'
					AND gle2.debit > 0
			  )
			GROUP BY gle.posting_date, gle.voucher_no

		) combined_results

		ORDER BY sort_order
	"""

	raw_data = frappe.db.sql(query, filters, as_dict=True)
	
	# Process data to add blank rows after each transaction (after subtotal)
	processed_data = []
	grand_total_debit = 0
	grand_total_credit = 0
	
	for row in raw_data:
		processed_data.append(row)
		
		# Track subtotals for grand total
		if row.get("row_type") == "subtotal":
			grand_total_debit += row.get("debit", 0) or 0
			grand_total_credit += row.get("credit", 0) or 0
			
			# Add blank row after subtotal
			processed_data.append({
				"transaction_date": None,
				"doc_type": "",
				"doc_no_html": "",
				"customer_name": "",
				"reference_html": "",
				"account": "",
				"cost_center": "",
				"description": "",
				"debit": None,
				"credit": None,
				"project": "",
				"tin_number": "",
				"currency": row.get("currency", "")
			})
	
	# Add grand total row at the end
	if processed_data:
		currency = raw_data[0].get("currency", "") if raw_data else ""
		processed_data.append({
			"transaction_date": None,
			"doc_type": "",
			"doc_no_html": "",
			"customer_name": "",
			"reference_html": "",
			"account": "",
			"cost_center": "",
			"description": "<b>GRAND TOTAL</b>",
			"debit": grand_total_debit,
			"credit": grand_total_credit,
			"project": "",
			"tin_number": "",
			"currency": currency
		})
	
	return processed_data