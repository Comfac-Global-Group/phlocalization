# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	"""
	Main entry point for the Purchase VAT Report.

	This report fetches Purchase Invoices within a given date range
	and calculates VAT amounts based on accounts under the selected
	VAT root account (default: 1610 - VAT Input Tax).

	Filters:
	- company (required)
	- from_date (required)
	- to_date (required)
	- vat_account (optional)

	Returns:
		tuple: (columns, data)
	"""

	filters = filters or {}

	if not filters.get("company"):
		frappe.throw("Company filter is required.")

	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw("From Date and To Date filters are required.")

	filters["vat_account"] = filters.get("vat_account") or "1610 - VAT Input Tax"

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	"""
	Defines the column structure of the report.
	"""

	return [
		{"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": "Purchase Invoice ID", "fieldname": "name", "fieldtype": "Link", "options": "Purchase Invoice", "width": 150},
		{"label": "Supplier Tax ID", "fieldname": "tax_id", "fieldtype": "Data", "width": 150},
		{"label": "Supplier", "fieldname": "supplier", "fieldtype": "Data", "width": 200},

		{"label": "Invoice Total", "fieldname": "total", "fieldtype": "Currency", "options": "currency", "width": 150},
		{"label": "Net Payable Amount", "fieldname": "grand_total", "fieldtype": "Currency", "options": "currency", "width": 150},
		{"label": "Amount (VAT Account)", "fieldname": "vat_amount", "fieldtype": "Currency", "options": "currency", "width": 170},
		{"label": "Grand Total (Invoice Total + Purchase Tax Charges)", "fieldname": "grand_total_tax", "fieldtype": "Currency", "options": "currency", "width": 200},

		{"label": "Purchase Orders ID", "fieldname": "purchase_orders", "fieldtype": "Data", "width": 220},
		{"label": "Payment ID", "fieldname": "payment_id", "fieldtype": "Link", "options": "Payment Entry", "width": 200},
		{"label": "VAT Account", "fieldname": "vat_account", "fieldtype": "Data", "width": 260},
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
		{"label": "Tax Description", "fieldname": "tax_description", "fieldtype": "Data", "width": 250},
		{"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data", "width": 250},
	]


def get_data(filters):
	"""
	Fetches Purchase Invoices and calculates VAT based on taxes
	from accounts under the selected VAT root account.
	"""

	query = """
	SELECT
		pi.posting_date,
		pi.name,
		pi.currency,
		sup.tax_id,
		pi.supplier,
		pi.total,
		pi.grand_total,

		COALESCE(agg_taxes.total_tax_amount, 0) AS vat_amount,

		pi.total + COALESCE(agg_taxes.total_tax_amount, 0) AS grand_total_tax,

		(
			SELECT GROUP_CONCAT(DISTINCT pii.purchase_order SEPARATOR ', ')
			FROM `tabPurchase Invoice Item` pii
			WHERE pii.parent = pi.name AND pii.purchase_order IS NOT NULL
		) AS purchase_orders,

		(
			SELECT GROUP_CONCAT(DISTINCT pe.parent SEPARATOR ', ')
			FROM `tabPayment Entry Reference` pe
			WHERE pe.reference_doctype = 'Purchase Invoice'
			AND pe.reference_name = pi.name
		) AS payment_id,

		TRIM(CONCAT_WS(', ',
			IF(agg_taxes.parent IS NOT NULL, agg_taxes.account_heads, NULL)
		)) AS vat_account,

		(
			SELECT pii2.project
			FROM `tabPurchase Invoice Item` pii2
			WHERE pii2.parent = pi.name
			AND IFNULL(pii2.project, '') != ''
			LIMIT 1
		) AS project,

		TRIM(
			IF(LOCATE('VAT', agg_taxes.description) > 0,
			LEFT(agg_taxes.description, LOCATE('VAT', agg_taxes.description) - 1),
			agg_taxes.description)
		) AS tax_description,

		pi.remarks

	FROM `tabPurchase Invoice` pi
	LEFT JOIN `tabSupplier` sup ON sup.name = pi.supplier

	LEFT JOIN (
		SELECT
			ptc.parent,
			SUM(ptc.tax_amount_after_discount_amount) AS total_tax_amount,
			MIN(ptc.description) AS description,
			GROUP_CONCAT(DISTINCT ptc.account_head SEPARATOR ', ') AS account_heads
		FROM `tabPurchase Taxes and Charges` ptc
		LEFT JOIN `tabAccount` acc ON acc.name = ptc.account_head
		LEFT JOIN `tabAccount` vat_root
		ON vat_root.name = %(vat_account)s
		WHERE acc.lft >= vat_root.lft
		AND acc.rgt <= vat_root.rgt
		GROUP BY ptc.parent
	) agg_taxes ON agg_taxes.parent = pi.name

	WHERE
		pi.docstatus = 1
		AND pi.company = %(company)s
		AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
		AND agg_taxes.parent IS NOT NULL

	ORDER BY pi.posting_date, pi.name
	"""

	return frappe.db.sql(query, filters, as_dict=True)