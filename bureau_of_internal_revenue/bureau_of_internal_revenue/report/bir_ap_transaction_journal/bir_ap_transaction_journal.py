# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	"""
	Main entry point for the report.
	Validates filters, defines columns, and fetches report data.
	"""
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def validate_filters(filters):
	"""
	Validates mandatory filters like company and date range.
	Ensures logical date order and sets default doc_type if missing.
	"""
	if not filters.get("company"):
		frappe.throw(_("Company is mandatory"))

	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are mandatory"))

	from frappe.utils import getdate
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	if from_date > to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	if not filters.get("doc_type"):
		filters["doc_type"] = ""


def get_columns():
	"""
	Defines report column structure including field types,
	labels, widths, and link options for the report output.
	"""
	return [
		{"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": "Doc Type", "fieldname": "doc_type", "fieldtype": "Data", "width": 120},
		{"label": "Doc No", "fieldname": "doc_no_html", "fieldtype": "HTML", "width": 140},
		{"label": "Supplier Name", "fieldname": "supplier_name", "fieldtype": "Link", "options": "Supplier", "width": 220},
		{"label": "Reference", "fieldname": "reference_html", "fieldtype": "HTML", "width": 120},
		{"label": "Account", "fieldname": "account", "fieldtype": "Data", "width": 280},
		{"label": "Cost Center", "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 150},
		{"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 300},
		{"label": "Debit", "fieldname": "debit", "fieldtype": "Currency","options": "currency", "width": 120},
		{"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
		{"label": "TIN Number", "fieldname": "tin_number", "fieldtype": "Data", "width": 150},
	]

def get_data(filters):
	"""
	Fetches GL-based transaction data using raw SQL.
	Returns detail, subtotal, and separator rows based on filters.
	"""

	parent = frappe.db.get_value(
		"Account",
		{
			"account_number": "2100",
			"company": filters.company
		},
		["lft", "rgt"],
		as_dict=True
	)

	if not parent:
		frappe.throw("Parent account 2100 not found")

	filters["parent_lft"] = parent.lft
	filters["parent_rgt"] = parent.rgt

	sql="""
	SELECT
		transaction_date ,
		doc_type ,
		doc_no_html ,
		supplier_name ,
		reference_html ,
		account ,
		cost_center ,
		description ,
		debit ,
		credit ,
		project ,
		tin_number ,
		currency
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
			
			gle.party AS supplier_name,
			
			CASE 
				WHEN gle.voucher_type = 'Purchase Invoice' THEN (
					SELECT COALESCE(pi.remarks, '') 
					FROM `tabPurchase Invoice` pi 
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
				WHEN gle.voucher_type = 'Purchase Invoice' THEN (
					SELECT pi.posting_date 
					FROM `tabPurchase Invoice` pi 
					WHERE pi.name = gle.voucher_no
				)
				ELSE gle.posting_date
			END AS transaction_date,
			
			CONCAT(a.account_number, ' - ', a.account_name) AS account,
			COALESCE(gle.cost_center, '') AS cost_center,
			
			CASE 
				WHEN gle.voucher_type = 'Purchase Invoice' THEN (
					SELECT GROUP_CONCAT(DISTINCT pii.description SEPARATOR '; ')
					FROM `tabPurchase Invoice Item` pii
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
			
			COALESCE(gle.debit, 0) AS debit,
			COALESCE(gle.credit, 0) AS credit,
			COALESCE(gle.project, '') AS project,
			
			CASE 
				WHEN gle.party_type = 'Supplier' THEN (
					SELECT s.tax_id 
					FROM `tabSupplier` s 
					WHERE s.name = gle.party
				)
				ELSE ''
			END AS tin_number,
			
			gle.account_currency AS currency,
			
			CONCAT(
				gle.posting_date, '-', 
				gle.voucher_no, '-1-',
				CASE 
					WHEN gle.debit > 0 THEN '1'
					WHEN gle.credit > 0 
						AND a.lft BETWEEN %(parent_lft)s AND %(parent_rgt)s 
					THEN '3'
					WHEN gle.credit > 0 THEN '2'
					ELSE '9'
				END,
				'-', LPAD(gle.idx, 5, '0')
			) AS sort_order

		FROM `tabGL Entry` gle
		JOIN `tabAccount` a ON a.name = gle.account

		WHERE gle.is_cancelled = 0
			AND gle.company = %(company)s
			AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND IF(%(doc_type)s != '', gle.voucher_type = %(doc_type)s, 1=1)
			AND EXISTS (
				SELECT 1 
				FROM `tabGL Entry` gle2
				JOIN `tabAccount` a2 ON a2.name = gle2.account
				WHERE gle2.voucher_no = gle.voucher_no
					AND gle2.is_cancelled = 0
					AND a2.lft BETWEEN %(parent_lft)s AND %(parent_rgt)s
					AND gle2.credit > 0
			)

		UNION ALL

		-- Subtotal rows
		SELECT
			gle.posting_date,
			'' AS doc_type,
			'' AS doc_no_html,
			'' AS supplier_name,
			'' AS reference_html,
			NULL AS transaction_date,
			'' AS account,
			'' AS cost_center,
			'<b>SUBTOTAL</b>' AS description,
			SUM(COALESCE(gle.debit, 0)) AS debit,
			SUM(COALESCE(gle.credit, 0)) AS credit,
			'' AS project,
			'' AS tin_number,
			MAX(gle.account_currency) AS currency,
			
			CONCAT(gle.posting_date, '-', gle.voucher_no, '-2-0-00000') AS sort_order

		FROM `tabGL Entry` gle
		JOIN `tabAccount` a ON a.name = gle.account

		WHERE gle.is_cancelled = 0
			AND gle.company = %(company)s
			AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND IF(%(doc_type)s != '', gle.voucher_type = %(doc_type)s, 1=1)
			AND EXISTS (
				SELECT 1 
				FROM `tabGL Entry` gle2
				JOIN `tabAccount` a2 ON a2.name = gle2.account
				WHERE gle2.voucher_no = gle.voucher_no
					AND gle2.is_cancelled = 0
					AND a2.lft BETWEEN %(parent_lft)s AND %(parent_rgt)s
					AND gle2.credit > 0
			)
		GROUP BY gle.posting_date, gle.voucher_no

		UNION ALL

		-- Empty rows
		SELECT
			gle.posting_date,
			'' AS doc_type,
			'' AS doc_no_html,
			'' AS supplier_name,
			'' AS reference_html,
			NULL AS transaction_date,
			'' AS account,
			'' AS cost_center,
			'' AS description,
			NULL AS debit,
			NULL AS credit,
			'' AS project,
			'' AS tin_number,
			'' AS currency,
			
			CONCAT(gle.posting_date, '-', gle.voucher_no, '-3-0-00000') AS sort_order

		FROM `tabGL Entry` gle

		WHERE gle.is_cancelled = 0
			AND gle.company = %(company)s
			AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND IF(%(doc_type)s != '', gle.voucher_type = %(doc_type)s, 1=1)
			AND EXISTS (
				SELECT 1 
				FROM `tabGL Entry` gle2
				JOIN `tabAccount` a2 ON a2.name = gle2.account
				WHERE gle2.voucher_no = gle.voucher_no
					AND gle2.is_cancelled = 0
					AND a2.lft BETWEEN %(parent_lft)s AND %(parent_rgt)s
					AND gle2.credit > 0
			)
		GROUP BY gle.posting_date, gle.voucher_no

	) combined_results

	ORDER BY sort_order;
	"""

	result = frappe.db.sql(sql, filters, as_dict=True)

	return result