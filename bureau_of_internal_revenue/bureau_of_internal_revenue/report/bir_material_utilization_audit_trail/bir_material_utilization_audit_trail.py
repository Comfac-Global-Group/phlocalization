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
		{"label": _("ID"), "fieldname": "id", "fieldtype": "Dynamic Link", "options": "doctype", "width": 220},
		{"label": _("DocType"), "fieldname": "doctype", "fieldtype": "Link", "options": "DocType", "width": 150},
		{"label": _("JO Number"), "fieldname": "jo_number", "fieldtype": "Data", "width": 170},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Supp/Cust Code"), "fieldname": "supp_cust_code", "fieldtype": "Data", "width": 140},
		{"label": _("Supplier/Customer"), "fieldname": "supplier", "fieldtype": "Data", "width": 300},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 170},
		{"label": _("Item Description"), "fieldname": "item_name", "fieldtype": "Data", "width": 250},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"label": _("Unit"), "fieldname": "unit", "fieldtype": "Data", "width": 70},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 70},
		{"label": _("Quantity Difference"), "fieldname": "qty", "fieldtype": "Data", "width": 120},
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
			jo_number,
			posting_date,
			supp_cust_code,
			supplier,
			item_code,
			item_name,
			warehouse,
			unit,
			uom,
			CASE
				WHEN qty IS NOT NULL AND sort_order IN (2, 4)
				THEN CONCAT('<b>', FORMAT(qty, 2), '</b>')
				ELSE CAST(qty AS CHAR)
			END AS qty,
			CASE
				WHEN unit_cost IS NOT NULL AND sort_order IN (2, 4)
				THEN CONCAT('<b>', FORMAT(unit_cost, 2), '</b>')
				ELSE FORMAT(unit_cost, 2)
			END AS unit_cost,
			CASE
				WHEN total_cost IS NOT NULL AND sort_order IN (2, 4)
				THEN CONCAT('<b>', FORMAT(total_cost, 2), '</b>')
				ELSE FORMAT(total_cost, 2)
			END AS total_cost,
			status
		FROM (

			/* ================================================
			   DETAIL ROWS - MATERIALS REQUIREMENT
			   ================================================ */
			SELECT
				1 AS sort_order,
				COALESCE(se.project, '') AS sort_jo,
				CASE
					WHEN sed.s_warehouse = %(warehouse)s THEN 'Materials Requirement'
					WHEN sed.t_warehouse = %(warehouse)s THEN 'Materials Requirement - Returns'
					ELSE 'Materials Requirement'
				END AS entry_type,
				se.name AS id,
				'Stock Entry' AS doctype,
				COALESCE(se.project, '') AS jo_number,
				se.posting_date AS posting_date,
				COALESCE(p.customer, '') AS supp_cust_code,
				COALESCE(c.customer_name, '') AS supplier,
				sed.item_code AS item_code,
				sed.item_name AS item_name,
				%(warehouse)s AS warehouse,
				sed.stock_uom AS unit,
				COALESCE(sed.uom, sed.stock_uom) AS uom,
				CASE
					WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
					WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
					ELSE sed.qty
				END AS qty,
				COALESCE(sed.valuation_rate, 0) AS unit_cost,
				COALESCE(sed.transfer_qty * sed.valuation_rate, 0) AS total_cost,
				CASE
					WHEN se.docstatus = 0 THEN 'Draft'
					WHEN se.docstatus = 1 THEN 'Submitted'
					WHEN se.docstatus = 2 THEN 'Cancelled'
					ELSE 'Unknown'
				END AS status
			FROM `tabStock Entry` se
			JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
			LEFT JOIN `tabProject` p ON p.name = se.project
			LEFT JOIN `tabCustomer` c ON c.name = p.customer
			WHERE
				se.stock_entry_type = 'Material Transfer'
				AND (
					sed.s_warehouse = %(warehouse)s
					OR sed.t_warehouse = %(warehouse)s
				)
				AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND se.docstatus IN (0, 1, 2)

			UNION ALL

			/* ================================================
			   SUBTOTAL PER JO NUMBER
			   ================================================ */
			SELECT
				2 AS sort_order,
				COALESCE(se.project, '') AS sort_jo,
				NULL AS entry_type,
				NULL AS id,
				NULL AS doctype,
				NULL AS jo_number,
				NULL AS posting_date,
				NULL AS supp_cust_code,
				CONCAT('<b>SUBTOTAL - ', COALESCE(se.project, ''), '</b>') AS supplier,
				NULL AS item_code,
				NULL AS item_name,
				NULL AS warehouse,
				NULL AS unit,
				NULL AS uom,
				SUM(
					CASE
						WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
						WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
						ELSE sed.qty
					END
				) AS qty,
				CASE
					WHEN SUM(ABS(
						CASE
							WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
							WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
							ELSE sed.qty
						END
					)) > 0
					THEN SUM(COALESCE(sed.transfer_qty * sed.valuation_rate, 0)) / SUM(ABS(
						CASE
							WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
							WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
							ELSE sed.qty
						END
					))
					ELSE NULL
				END AS unit_cost,
				SUM(COALESCE(sed.transfer_qty * sed.valuation_rate, 0)) AS total_cost,
				NULL AS status
			FROM `tabStock Entry` se
			JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
			WHERE
				se.stock_entry_type = 'Material Transfer'
				AND (
					sed.s_warehouse = %(warehouse)s
					OR sed.t_warehouse = %(warehouse)s
				)
				AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND se.docstatus IN (0, 1, 2)
				AND COALESCE(se.project, '') != ''
			GROUP BY se.project

			UNION ALL

			/* ================================================
			   BLANK ROW AFTER SUBTOTAL
			   ================================================ */
			SELECT
				3 AS sort_order,
				COALESCE(se.project, '') AS sort_jo,
				NULL, NULL, NULL, NULL, NULL, NULL, NULL,
				NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
			FROM `tabStock Entry` se
			JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
			WHERE
				se.stock_entry_type = 'Material Transfer'
				AND (
					sed.s_warehouse = %(warehouse)s
					OR sed.t_warehouse = %(warehouse)s
				)
				AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND se.docstatus IN (0, 1, 2)
				AND COALESCE(se.project, '') != ''
			GROUP BY se.project

			UNION ALL

			/* ================================================
			   GRAND TOTAL
			   ================================================ */
			SELECT
				4 AS sort_order,
				'ZZZZZ' AS sort_jo,
				NULL AS entry_type,
				NULL AS id,
				NULL AS doctype,
				NULL AS jo_number,
				NULL AS posting_date,
				NULL AS supp_cust_code,
				'<b>GRAND TOTAL</b>' AS supplier,
				NULL AS item_code,
				NULL AS item_name,
				NULL AS warehouse,
				NULL AS unit,
				NULL AS uom,
				SUM(
					CASE
						WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
						WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
						ELSE sed.qty
					END
				) AS qty,
				CASE
					WHEN SUM(ABS(
						CASE
							WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
							WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
							ELSE sed.qty
						END
					)) > 0
					THEN SUM(COALESCE(sed.transfer_qty * sed.valuation_rate, 0)) / SUM(ABS(
						CASE
							WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
							WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
							ELSE sed.qty
						END
					))
					ELSE NULL
				END AS unit_cost,
				SUM(COALESCE(sed.transfer_qty * sed.valuation_rate, 0)) AS total_cost,
				NULL AS status
			FROM `tabStock Entry` se
			JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
			WHERE
				se.stock_entry_type = 'Material Transfer'
				AND (
					sed.s_warehouse = %(warehouse)s
					OR sed.t_warehouse = %(warehouse)s
				)
				AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND se.docstatus IN (0, 1, 2)

		) final_result
		ORDER BY
			sort_jo,
			sort_order,
			posting_date,
			entry_type,
			item_code
	"""

	return frappe.db.sql(query, filters, as_dict=True)