# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	"""
	Entry point for the BIR Subsidiary Sales Journal script report.
	Returns the column definitions and query result data
	based on the provided filters.
	"""
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""
	Return the column definitions for the report.
	Each column maps to a field returned by the SQL query
	with its label, fieldtype, and display width.
	"""
	return [
		{"label": "Transaction Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": "Customer ID", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 100},
		{"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
		{"label": "Customer TIN", "fieldname": "tax_id", "fieldtype": "Data", "width": 120},
		{"label": "Description", "fieldname": "remarks", "fieldtype": "Data", "width": 180},
		{"label": "S/I BI No", "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 130},
		{"label": "Reference No", "fieldname": "po_no", "fieldtype": "Data", "width": 130},
		{"label": "Accounts Receivable", "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
		{"label": "Discount", "fieldname": "discount_amount", "fieldtype": "Currency", "width": 100},
		{"label": "Output VAT", "fieldname": "output_vat", "fieldtype": "Currency", "width": 110},
		{"label": "Vatable Sales", "fieldname": "vatable_sales", "fieldtype": "Currency", "width": 110},
		{"label": "Sales to Government", "fieldname": "sales_to_government", "fieldtype": "Currency", "width": 130},
		{"label": "VAT Exempt Sales", "fieldname": "vat_exempt_sales", "fieldtype": "Currency", "width": 130},
		{"label": "Zero-Rated Sales", "fieldname": "zero_rated_sales", "fieldtype": "Currency", "width": 120},
		{"label": "Net Sales", "fieldname": "net_sales", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	"""
	Fetch sales invoice data classified by BIR tax category.
	Uses the customer's tax_category to determine VAT treatment
	and computes Output VAT, Vatable, Exempt, Zero-Rated, and Net Sales.
	"""
	query = """
		SELECT
			si.posting_date,
			si.customer,
			si.customer_name,
			si.tax_id,
			si.remarks,
			si.name,
			si.po_no,
			si.grand_total,
			si.discount_amount,
			CASE
				WHEN c.tax_category IN ('VATABLE', 'SALES TO GOVERNMENT')
				THEN IFNULL((
					SELECT SUM(stc.tax_amount)
					FROM `tabSales Taxes and Charges` stc
					INNER JOIN `tabAccount` a
						ON a.name = stc.account_head
					WHERE stc.parent = si.name
					  AND a.parent_account LIKE '2200 - VAT Output Tax%%'
				), 0)
				ELSE 0
			END AS output_vat,
			CASE
				WHEN c.tax_category = 'VATABLE'
				 AND EXISTS (
					SELECT 1
					FROM `tabSales Taxes and Charges` stc
					INNER JOIN `tabAccount` a
						ON a.name = stc.account_head
					WHERE stc.parent = si.name
					  AND a.parent_account LIKE '2200 - VAT Output Tax%%'
				 )
				THEN si.net_total
				ELSE 0
			END AS vatable_sales,
			CASE
				WHEN c.tax_category = 'SALES TO GOVERNMENT'
				THEN si.net_total
				ELSE 0
			END AS sales_to_government,
			CASE
				WHEN c.tax_category = 'VAT EXEMPT'
				THEN si.net_total
				ELSE 0
			END AS vat_exempt_sales,
			CASE
				WHEN c.tax_category = 'ZERO RATED'
				THEN si.net_total
				ELSE 0
			END AS zero_rated_sales,
			(
				CASE
					WHEN c.tax_category = 'VATABLE'
					 AND EXISTS (
						SELECT 1
						FROM `tabSales Taxes and Charges` stc
						INNER JOIN `tabAccount` a
							ON a.name = stc.account_head
						WHERE stc.parent = si.name
						  AND a.parent_account LIKE '2200 - VAT Output Tax%%'
					 )
					THEN si.net_total
					ELSE 0
				END
				+
				CASE WHEN c.tax_category = 'SALES TO GOVERNMENT' THEN si.net_total ELSE 0 END
				+
				CASE WHEN c.tax_category = 'VAT EXEMPT' THEN si.net_total ELSE 0 END
				+
				CASE WHEN c.tax_category = 'ZERO RATED' THEN si.net_total ELSE 0 END
				- IFNULL(si.discount_amount, 0)
			) AS net_sales
		FROM `tabSales Invoice` si
		LEFT JOIN `tabCustomer` c ON c.name = si.customer
		WHERE
			si.docstatus = 1
			AND si.company = %(company)s
			AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
		ORDER BY
			si.posting_date ASC,
			si.name ASC
	"""

	return frappe.db.sql(query, filters, as_dict=True)