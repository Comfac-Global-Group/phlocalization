# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	"""
	Entry point for the BIR Sales Book report.
	Returns column definitions and filtered sales order data.
	Called by the Frappe report builder with user-selected filters.
	"""
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""
	Define the column structure for the BIR Sales Book report.
	Each column maps to a field alias returned by the SQL query.
	Includes links to Sales Order, Project, and Item doctypes.
	"""
	return [
		{"label": "SO Number", "fieldname": "so_number", "fieldtype": "Link", "options": "Sales Order", "width": 130},
		{"label": "Tran Date", "fieldname": "tran_date", "fieldtype": "Date", "width": 100},
		{"label": "Salesman", "fieldname": "salesman", "fieldtype": "Data", "width": 160},
		{"label": "Customer Code", "fieldname": "customer_code", "fieldtype": "Data", "width": 90},
		{"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 220},
		{"label": "JO Number", "fieldname": "jo_number", "fieldtype": "Link", "options": "Project", "width": 120},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": "Item Description", "fieldname": "item_description", "fieldtype": "Data", "width": 200},
		{"label": "Particulars", "fieldname": "particulars", "fieldtype": "Data", "width": 200},
		{"label": "PO Number", "fieldname": "po_number", "fieldtype": "Data", "width": 130},
		{"label": "Terms", "fieldname": "terms", "fieldtype": "Data", "width": 90},
		{"label": "Unit", "fieldname": "unit", "fieldtype": "Data", "width": 80},
		{"label": "Quantity", "fieldname": "quantity", "fieldtype": "Float", "width": 80},
		{"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 120},
		{"label": "Discount", "fieldname": "discount", "fieldtype": "Float", "width": 80},
		{"label": "Net Amount", "fieldname": "net_amount", "fieldtype": "Currency", "width": 130},
		{"label": "Deposit", "fieldname": "deposit", "fieldtype": "Currency", "width": 110},
		{"label": "Ref Invoice", "fieldname": "ref_invoice", "fieldtype": "Data", "width": 130},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 130},
		{"label": "Indus Code", "fieldname": "indus_code", "fieldtype": "Data", "width": 90},
		{"label": "Contact", "fieldname": "contact", "fieldtype": "Data", "width": 180},
		{"label": "Title", "fieldname": "title", "fieldtype": "Data", "width": 120},
	]


def get_data(filters):
	"""
	Fetch sales order line items with related project, customer, and contact details.
	Filters by company and date range, excluding cancelled documents.
	Includes salesperson names and primary contact designation via subqueries.
	"""
	sql = """
		SELECT
			so.name AS so_number,
			so.transaction_date AS tran_date,
			(
				SELECT GROUP_CONCAT(st2.sales_person ORDER BY st2.idx SEPARATOR ', ')
				FROM `tabSales Team` st2
				WHERE st2.parent = so.name
				  AND st2.parenttype = 'Sales Order'
			) AS salesman,
			so.customer AS customer_code,
			so.customer_name AS customer_name,
			proj.name AS jo_number,
			soi.item_code AS item_code,
			soi.item_name AS item_description,
			soi.description AS particulars,
			so.po_no AS po_number,
			so.payment_terms_template AS terms,
			soi.uom AS unit,
			soi.qty AS quantity,
			soi.rate AS rate,
			soi.discount_percentage AS discount,
			soi.amount AS net_amount,
			'' AS deposit,
			soi.item_code AS ref_invoice,
			so.status AS status,
			cust.industry AS indus_code,
			so.contact_person AS contact,
			(
				SELECT con2.designation
				FROM `tabDynamic Link` dl2
				INNER JOIN `tabContact` con2 ON con2.name = dl2.parent
				WHERE dl2.link_doctype = 'Customer'
				  AND dl2.link_name = so.customer
				  AND dl2.parenttype = 'Contact'
				ORDER BY con2.name ASC
				LIMIT 1
			) AS title
		FROM `tabSales Order` so
		INNER JOIN `tabSales Order Item` soi ON soi.parent = so.name
		LEFT JOIN `tabProject` proj ON proj.sales_order = so.name
		LEFT JOIN `tabCustomer` cust ON cust.name = so.customer
		WHERE
			so.docstatus != 2
			AND so.company = %(company)s
			AND so.transaction_date BETWEEN %(from_date)s AND %(to_date)s
		ORDER BY
			so.transaction_date ASC,
			so.name ASC,
			soi.idx ASC
		"""

	return frappe.db.sql(sql, filters, as_dict=True)