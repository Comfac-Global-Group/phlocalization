# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.get("warehouse"):
		frappe.throw(_("Warehouse is required"))

	if not filters.get("from_date"):
		frappe.throw(_("From Date is required"))

	if not filters.get("to_date"):
		frappe.throw(_("To Date is required"))

	if filters.get("from_date") > filters.get("to_date"):
		frappe.throw(_("From Date cannot be after To Date"))

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Entry Type"), "fieldname": "entry_type", "fieldtype": "Data", "width": 200},
		{"label": _("ID"), "fieldname": "id", "fieldtype": "Dynamic Link", "options": "doctype", "width": 200},
		{"label": _("DocType"), "fieldname": "doctype", "fieldtype": "Link", "options": "DocType", "width": 150},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 170},
		{"label": _("Item Description"), "fieldname": "item_name", "fieldtype": "Data", "width": 250},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 120},
		{"label": _("Unit"), "fieldname": "unit", "fieldtype": "Data", "width": 80},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 80},
		{"label": _("Quantity Difference"), "fieldname": "qty", "fieldtype": "Data", "width": 100},
		{"label": _("Unit Cost"), "fieldname": "unit_cost", "fieldtype": "Data", "width": 110},
		{"label": _("Total Cost"), "fieldname": "total_cost", "fieldtype": "Data", "width": 140},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	query = """
		SELECT
			entry_type,
			id,
			doctype,
			posting_date,
			item_code,
			item_name,
			warehouse,
			unit,
			uom,
			CASE
				WHEN qty IS NOT NULL AND sort_order = 2
				THEN CONCAT('<b>', FORMAT(qty, 2), '</b>')
				ELSE CAST(qty AS CHAR)
			END AS qty,
			CASE
				WHEN unit_cost IS NOT NULL AND sort_order = 2
				THEN CONCAT('<b>', FORMAT(unit_cost, 2), '</b>')
				ELSE FORMAT(unit_cost, 2)
			END AS unit_cost,
			CASE
				WHEN total_cost IS NOT NULL AND sort_order = 2
				THEN CONCAT('<b>', FORMAT(total_cost, 2), '</b>')
				ELSE FORMAT(total_cost, 2)
			END AS total_cost,
			status
		FROM (

			/* ================================================
			   DETAIL ROWS
			   ================================================ */
			SELECT
				1 AS sort_order,
				'Adjustments on Inventory' AS entry_type,
				sr.name AS id,
				'Stock Reconciliation' AS doctype,
				sr.posting_date AS posting_date,
				sri.item_code AS item_code,
				COALESCE(sri.item_name, i.item_name) AS item_name,
				sri.warehouse AS warehouse,
				i.stock_uom AS unit,
				i.stock_uom AS uom,
				COALESCE(sri.quantity_difference, 0) AS qty,
				COALESCE(sri.valuation_rate, 0) AS unit_cost,
				COALESCE(sri.quantity_difference * sri.valuation_rate, 0) AS total_cost,
				CASE
					WHEN sr.docstatus = 0 THEN 'Draft'
					WHEN sr.docstatus = 1 THEN 'Submitted'
					WHEN sr.docstatus = 2 THEN 'Cancelled'
					ELSE 'Unknown'
				END AS status
			FROM `tabStock Reconciliation` sr
			JOIN `tabStock Reconciliation Item` sri ON sri.parent = sr.name
			LEFT JOIN `tabItem` i ON i.name = sri.item_code
			WHERE
				sr.purpose = 'Stock Reconciliation'
				AND sri.warehouse = %(warehouse)s
				AND sr.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND sr.docstatus IN (0, 1, 2)

			UNION ALL

			/* ================================================
			   BLANK ROW
			   ================================================ */
			SELECT
				2 AS sort_order,
				NULL, NULL, NULL, NULL, NULL, NULL, NULL,
				NULL, NULL, NULL, NULL, NULL, NULL
			FROM (SELECT 1) blank_row
			WHERE EXISTS (
				SELECT 1
				FROM `tabStock Reconciliation` sr
				JOIN `tabStock Reconciliation Item` sri ON sri.parent = sr.name
				WHERE
					sr.purpose = 'Stock Reconciliation'
					AND sri.warehouse = %(warehouse)s
					AND sr.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND sr.docstatus IN (0, 1, 2)
			)

			UNION ALL

			/* ================================================
			   GRAND TOTAL
			   ================================================ */
			SELECT
				3 AS sort_order,
				NULL AS entry_type,
				NULL AS id,
				NULL AS doctype,
				NULL AS posting_date,
				NULL AS item_code,
				'<b>GRAND TOTAL</b>' AS item_name,
				NULL AS warehouse,
				NULL AS unit,
				NULL AS uom,
				SUM(COALESCE(sri.quantity_difference, 0)) AS qty,
				CASE
					WHEN SUM(ABS(COALESCE(sri.quantity_difference, 0))) > 0
					THEN SUM(COALESCE(sri.quantity_difference * sri.valuation_rate, 0)) / SUM(ABS(COALESCE(sri.quantity_difference, 0)))
					ELSE NULL
				END AS unit_cost,
				SUM(COALESCE(sri.quantity_difference * sri.valuation_rate, 0)) AS total_cost,
				NULL AS status
			FROM `tabStock Reconciliation` sr
			JOIN `tabStock Reconciliation Item` sri ON sri.parent = sr.name
			WHERE
				sr.purpose = 'Stock Reconciliation'
				AND sri.warehouse = %(warehouse)s
				AND sr.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND sr.docstatus IN (0, 1, 2)

		) final_result
		ORDER BY sort_order, posting_date ASC, item_code ASC
	"""

	return frappe.db.sql(query, filters, as_dict=True)