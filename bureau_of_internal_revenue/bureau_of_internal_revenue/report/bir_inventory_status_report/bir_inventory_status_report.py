# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

from frappe import _
import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 250},
		{"label": _("Beginning Balance"), "fieldname": "beginning_balance", "fieldtype": "Float", "width": 120},
		{"label": _("Issuances"), "fieldname": "issuances", "fieldtype": "Float", "width": 120},
		{"label": _("Receipts"), "fieldname": "receipts", "fieldtype": "Float", "width": 120},
		{"label": _("Adjustments"), "fieldname": "adjustments", "fieldtype": "Float", "width": 120},
		{"label": _("Current Balance"), "fieldname": "current_balance", "fieldtype": "Float", "width": 120},
		{"label": _("Unit Cost"), "fieldname": "unit_cost", "fieldtype": "Currency", "width": 120},
		{"label": _("Unit"), "fieldname": "uom", "fieldtype": "Data", "width": 80},
		{"label": _("Total Valuation"), "fieldname": "total_valuation", "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	sql = """
		SELECT
			item_code,
			description,
			beginning_balance,
			issuances,
			receipts,
			adjustments,
			current_balance,
			unit_cost,
			uom,
			total_valuation
		FROM (
			SELECT
				i.item_code,
				i.item_name AS description,
				COALESCE((
					SELECT SUM(sle.actual_qty)
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date < %(from_date)s
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
				), 0) AS beginning_balance,
				COALESCE((
					SELECT SUM(ABS(sle.actual_qty))
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
						AND sle.voucher_type = 'Stock Entry'
						AND sle.voucher_no LIKE 'ESC2-SET-%%'
						AND sle.actual_qty < 0
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
				), 0) AS issuances,
				COALESCE((
					SELECT SUM(sle.actual_qty)
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
						AND sle.voucher_type = 'Purchase Receipt'
						AND sle.actual_qty > 0
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
				), 0) AS receipts,
				COALESCE((
					SELECT SUM(sle.actual_qty)
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
						AND sle.voucher_type = 'Stock Reconciliation'
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
				), 0) AS adjustments,
				COALESCE((
					SELECT SUM(sle.actual_qty)
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date <= %(to_date)s
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
				), 0) AS current_balance,
				COALESCE((
					SELECT sle.valuation_rate
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date <= %(to_date)s
						AND sle.valuation_rate > 0
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
					ORDER BY sle.posting_date DESC, sle.posting_time DESC
					LIMIT 1
				), 0) AS unit_cost,
				i.stock_uom AS uom,
				COALESCE((
					SELECT SUM(sle.actual_qty)
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date <= %(to_date)s
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
				), 0) * COALESCE((
					SELECT sle.valuation_rate
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date <= %(to_date)s
						AND sle.valuation_rate > 0
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
					ORDER BY sle.posting_date DESC, sle.posting_time DESC
					LIMIT 1
				), 0) AS total_valuation
			FROM `tabItem` i
			WHERE
				i.disabled = 0
				AND EXISTS (
					SELECT 1
					FROM `tabStock Ledger Entry` sle
					WHERE sle.item_code = i.item_code
						AND sle.warehouse = %(warehouse)s
						AND sle.posting_date <= %(to_date)s
						AND sle.is_cancelled = 0
						AND sle.docstatus < 2
				)
		) inventory_data
		WHERE
			beginning_balance != 0
			OR issuances != 0
			OR receipts != 0
			OR adjustments != 0
			OR current_balance != 0
		ORDER BY item_code
		"""

	return frappe.db.sql(sql, filters, as_dict=True)
