# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 110},
		{"label": "Vendor Name", "fieldname": "vendor_name", "fieldtype": "Data", "width": 200},
		{"label": "Vendor Address", "fieldname": "vendor_address", "fieldtype": "Data", "width": 180},
		{"label": "Vendor TIN", "fieldname": "vendor_tin", "fieldtype": "Data", "width": 120},
		{"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 180},
		{"label": "Reference No", "fieldname": "reference_no", "fieldtype": "Link", "options": "Purchase Invoice", "width": 140},
		{"label": "Document No", "fieldname": "document_no", "fieldtype": "Data", "width": 130},
		{"label": "Discount", "fieldname": "discount", "fieldtype": "Currency", "width": 100},
		{"label": "Non-VAT Purchases", "fieldname": "non_vat_purchases", "fieldtype": "Currency", "width": 150},
		{"label": "VAT Purchases (Goods)", "fieldname": "vat_purchases_goods", "fieldtype": "Currency", "width": 150},
		{"label": "VAT Purchases (Services)", "fieldname": "vat_purchases_services", "fieldtype": "Currency", "width": 150},
		{"label": "Input VAT", "fieldname": "input_vat", "fieldtype": "Currency", "width": 110},
		{"label": "Withholding Tax", "fieldname": "withholding_tax", "fieldtype": "Currency", "width": 170},
		{"label": "Accounts Payable", "fieldname": "accounts_payable", "fieldtype": "Currency", "width": 150},
		{"label": "Net Purchase", "fieldname": "net_purchase", "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	sql ="""
		SELECT
			pi.posting_date AS transaction_date,
			pi.supplier_name AS vendor_name,
			pi.supplier_address AS vendor_address,
			pi.tax_id AS vendor_tin,
			pi.remarks AS description,
			pi.name AS reference_no,
			pi.remarks AS document_no,
			pi.discount_amount AS discount,
			CASE
				WHEN NOT EXISTS (
					SELECT 1 FROM `tabPurchase Taxes and Charges` ptc
					WHERE ptc.parent = pi.name
					  AND ptc.account_head LIKE '161%%'
				) THEN pi.net_total
				ELSE 0
			END AS non_vat_purchases,
			CASE
				WHEN EXISTS (
					SELECT 1 FROM `tabPurchase Taxes and Charges` ptc
					WHERE ptc.parent = pi.name
					  AND ptc.account_head LIKE '1611%%'
				) THEN pi.net_total
				ELSE 0
			END AS vat_purchases_goods,
			CASE
				WHEN EXISTS (
					SELECT 1 FROM `tabPurchase Taxes and Charges` ptc
					WHERE ptc.parent = pi.name
					  AND ptc.account_head LIKE '1615%%'
				) THEN pi.net_total
				ELSE 0
			END AS vat_purchases_services,
			IFNULL((
				SELECT SUM(ptc.tax_amount)
				FROM `tabPurchase Taxes and Charges` ptc
				WHERE ptc.parent = pi.name
				  AND ptc.account_head LIKE '161%%'
			), 0) AS input_vat,
			IFNULL((
				SELECT SUM(ptc.tax_amount)
				FROM `tabPurchase Taxes and Charges` ptc
				WHERE ptc.parent = pi.name
				  AND ptc.account_head LIKE '2505%%'
			), 0) AS withholding_tax,
			pi.grand_total AS accounts_payable,
			(
				CASE
					WHEN NOT EXISTS (
						SELECT 1 FROM `tabPurchase Taxes and Charges` ptc
						WHERE ptc.parent = pi.name
						  AND ptc.account_head LIKE '161%%'
					) THEN pi.net_total
					ELSE 0
				END
				+
				CASE
					WHEN EXISTS (
						SELECT 1 FROM `tabPurchase Taxes and Charges` ptc
						WHERE ptc.parent = pi.name
						  AND ptc.account_head LIKE '1611%%'
					) THEN pi.net_total
					ELSE 0
				END
				+
				CASE
					WHEN EXISTS (
						SELECT 1 FROM `tabPurchase Taxes and Charges` ptc
						WHERE ptc.parent = pi.name
						  AND ptc.account_head LIKE '1615%%'
					) THEN pi.net_total
					ELSE 0
				END
				- IFNULL(pi.discount_amount, 0)
			) AS net_purchase
		FROM `tabPurchase Invoice` pi
		WHERE
			pi.docstatus = 1
			AND pi.company = %(company)s
			AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND pi.supplier_name NOT IN (
				'INDIVIDUAL',
				'AMIE ELIZAGA - PAY TO CASH',
				'CHERRY ANN MAXIMIANO - PAY TO CA',
				'CITY TREASURER-MANDALUYONG',
				'CITY TREASURER - MAKATI'
			)
		ORDER BY
			pi.posting_date ASC,
			pi.name ASC
		"""

	return frappe.db.sql(sql, filters, as_dict=1)