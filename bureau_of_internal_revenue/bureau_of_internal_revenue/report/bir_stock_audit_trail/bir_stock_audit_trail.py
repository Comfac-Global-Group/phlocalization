# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	"""
	Validate filters and return columns and data for BIR Stock Audit Trail.
	Combines Stock Entry, Stock Reconciliation, and Purchase Receipt
	with subtotals per JO Number and a grand total row.
	"""
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
	"""
	Return column definitions for the report grid.
	Includes entry type, document link, JO number, item details,
	quantity difference, costs, and record audit metadata
	(creation date, modified by, modified time, owner).
	"""
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
		{"label": _("Created On"), "fieldname": "creation", "fieldtype": "Datetime", "width": 150},
		{"label": _("Modified By"), "fieldname": "modified_by", "fieldtype": "Data", "width": 150},
		{"label": _("Modified On"), "fieldname": "modified", "fieldtype": "Datetime", "width": 150},
		{"label": _("Owner"), "fieldname": "owner", "fieldtype": "Data", "width": 150},
	]


def get_data(filters):
	"""
	Build and execute the audit trail SQL query.
	JO Number uses line-level project first: COALESCE(sed.project, se.project) and COALESCE(pri.project, pr.project). Stock Reconciliation has no project field so its jo_number is blank.
	creation, modified_by, modified, and owner are taken from the parent transaction
	document (Stock Entry / Stock Reconciliation / Purchase Receipt) so they reflect
	when/by whom the transaction itself was created and last modified.
	"""
	params = {
		"warehouse": filters.get("warehouse"),
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"entry_type": filters.get("entry_type") or "",
		"project": filters.get("project") or "",
	}

	sql = """
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
			creation,
			modified_by,
			modified,
			owner
		FROM (

			/* ================================================
			DETAIL ROWS
			================================================ */
			SELECT
				1 AS sort_order,
				audit_data.jo_number AS sort_jo,
				audit_data.entry_type,
				audit_data.id,
				audit_data.doctype,
				audit_data.jo_number,
				audit_data.posting_date,
				audit_data.supp_cust_code,
				audit_data.supplier,
				audit_data.item_code,
				audit_data.item_name,
				audit_data.warehouse,
				audit_data.unit,
				audit_data.uom,
				audit_data.qty_diff AS qty,
				audit_data.unit_cost,
				audit_data.total_cost,
				audit_data.creation,
				audit_data.modified_by,
				audit_data.modified,
				audit_data.owner
			FROM (
				/* 1) Stock Entry - Materials Requirement / Returns */
				SELECT
					CASE
						WHEN sed.s_warehouse = %(warehouse)s THEN 'Materials Requirement'
						WHEN sed.t_warehouse = %(warehouse)s THEN 'Materials Requirement - Returns'
						ELSE 'Materials Requirement'
					END AS entry_type,
					se.name AS id,
					'Stock Entry' AS doctype,
					COALESCE(sed.project, se.project, '') AS jo_number,
					se.posting_date,
					COALESCE(p.customer, '') AS supp_cust_code,
					COALESCE(c.customer_name, '') AS supplier,
					sed.item_code,
					sed.item_name,
					%(warehouse)s AS warehouse,
					sed.stock_uom AS unit,
					COALESCE(sed.uom, sed.stock_uom) AS uom,
					sed.qty,
					CASE
						WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
						WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
						ELSE sed.qty
					END AS qty_diff,
					COALESCE(sed.valuation_rate, 0) AS unit_cost,
					COALESCE(sed.transfer_qty * sed.valuation_rate, 0) AS total_cost,
					se.creation,
					se.modified_by,
					se.modified,
					se.owner
				FROM `tabStock Entry` se
				JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
				LEFT JOIN `tabProject` p ON p.name = COALESCE(sed.project, se.project)
				LEFT JOIN `tabCustomer` c ON c.name = p.customer
				WHERE
					se.stock_entry_type = 'Material Transfer'
					AND (
						sed.s_warehouse = %(warehouse)s
						OR sed.t_warehouse = %(warehouse)s
					)
					AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND se.docstatus IN (0, 1, 2)
					AND (%(project)s = '' OR COALESCE(sed.project, se.project) = %(project)s)

				UNION ALL

				/* 2) Stock Reconciliation - Adjustments on Inventory */
				SELECT
					'Adjustments on Inventory' AS entry_type,
					sr.name AS id,
					'Stock Reconciliation' AS doctype,
					'' AS jo_number,
					sr.posting_date,
					'' AS supp_cust_code,
					'' AS supplier,
					sri.item_code,
					COALESCE(sri.item_name, i.item_name) AS item_name,
					sri.warehouse,
					i.stock_uom AS unit,
					i.stock_uom AS uom,
					sri.qty,
					COALESCE(sri.quantity_difference, 0) AS qty_diff,
					COALESCE(sri.valuation_rate, 0) AS unit_cost,
					COALESCE(sri.quantity_difference * sri.valuation_rate, 0) AS total_cost,
					sr.creation,
					sr.modified_by,
					sr.modified,
					sr.owner
				FROM `tabStock Reconciliation` sr
				JOIN `tabStock Reconciliation Item` sri ON sri.parent = sr.name
				LEFT JOIN `tabItem` i ON i.name = sri.item_code
				WHERE
					sr.purpose = 'Stock Reconciliation'
					AND sri.warehouse = %(warehouse)s
					AND sr.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND sr.docstatus IN (0, 1, 2)
					AND %(project)s = ''

				UNION ALL

				/* 3) Purchase Receipt - Receiving Reports */
				SELECT
					'Receiving Reports' AS entry_type,
					pr.name AS id,
					'Purchase Receipt' AS doctype,
					COALESCE(pri.project, pr.project, '') AS jo_number,
					pr.posting_date,
					COALESCE(pr.supplier_name, '') AS supp_cust_code,
					COALESCE(pr.supplier_name, '') AS supplier,
					pri.item_code,
					pri.item_name,
					pri.warehouse,
					pri.stock_uom AS unit,
					COALESCE(pri.uom, pri.stock_uom) AS uom,
					pri.qty,
					pri.qty AS qty_diff,
					COALESCE(pri.valuation_rate, 0) AS unit_cost,
					COALESCE(pri.stock_qty * pri.valuation_rate, 0) AS total_cost,
					pr.creation,
					pr.modified_by,
					pr.modified,
					pr.owner
				FROM `tabPurchase Receipt` pr
				JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
				WHERE
					pri.warehouse = %(warehouse)s
					AND pr.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND pr.docstatus IN (0, 1, 2)
					AND (%(project)s = '' OR COALESCE(pri.project, pr.project) = %(project)s)
			) audit_data
			WHERE
				(%(entry_type)s IS NULL
				OR %(entry_type)s = ''
				OR audit_data.entry_type = %(entry_type)s)

			UNION ALL

			/* ================================================
			SUBTOTAL PER JO NUMBER
			================================================ */
			SELECT
				2 AS sort_order,
				audit_data.jo_number AS sort_jo,
				NULL AS entry_type,
				NULL AS id,
				NULL AS doctype,
				NULL AS jo_number,
				NULL AS posting_date,
				NULL AS supp_cust_code,
				CONCAT('<b>SUBTOTAL - ', audit_data.jo_number, '</b>') AS supplier,
				NULL AS item_code,
				NULL AS item_name,
				NULL AS warehouse,
				NULL AS unit,
				NULL AS uom,
				SUM(audit_data.qty_diff) AS qty,
				CASE
					WHEN SUM(ABS(audit_data.qty_diff)) > 0
					THEN SUM(audit_data.total_cost) / SUM(ABS(audit_data.qty_diff))
					ELSE NULL
				END AS unit_cost,
				SUM(audit_data.total_cost) AS total_cost,
				NULL AS creation,
				NULL AS modified_by,
				NULL AS modified,
				NULL AS owner
			FROM (
				SELECT
					CASE
						WHEN sed.s_warehouse = %(warehouse)s THEN 'Materials Requirement'
						WHEN sed.t_warehouse = %(warehouse)s THEN 'Materials Requirement - Returns'
						ELSE 'Materials Requirement'
					END AS entry_type,
					COALESCE(sed.project, se.project, '') AS jo_number,
					CASE
						WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
						WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
						ELSE sed.qty
					END AS qty_diff,
					COALESCE(sed.transfer_qty * sed.valuation_rate, 0) AS total_cost
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
					AND (%(project)s = '' OR COALESCE(sed.project, se.project) = %(project)s)

				UNION ALL

				SELECT
					'Adjustments on Inventory' AS entry_type,
					'' AS jo_number,
					COALESCE(sri.quantity_difference, 0) AS qty_diff,
					COALESCE(sri.quantity_difference * sri.valuation_rate, 0) AS total_cost
				FROM `tabStock Reconciliation` sr
				JOIN `tabStock Reconciliation Item` sri ON sri.parent = sr.name
				WHERE
					sr.purpose = 'Stock Reconciliation'
					AND sri.warehouse = %(warehouse)s
					AND sr.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND sr.docstatus IN (0, 1, 2)
					AND %(project)s = ''

				UNION ALL

				SELECT
					'Receiving Reports' AS entry_type,
					COALESCE(pri.project, pr.project, '') AS jo_number,
					pri.qty AS qty_diff,
					COALESCE(pri.stock_qty * pri.valuation_rate, 0) AS total_cost
				FROM `tabPurchase Receipt` pr
				JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
				WHERE
					pri.warehouse = %(warehouse)s
					AND pr.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND pr.docstatus IN (0, 1, 2)
					AND (%(project)s = '' OR COALESCE(pri.project, pr.project) = %(project)s)
			) audit_data
			WHERE
				(%(entry_type)s IS NULL
				OR %(entry_type)s = ''
				OR audit_data.entry_type = %(entry_type)s)
				AND audit_data.jo_number != ''
			GROUP BY audit_data.jo_number

			UNION ALL

			/* ================================================
			BLANK ROW AFTER SUBTOTAL - ONE PER JO
			================================================ */
			SELECT
				3 AS sort_order,
				jo_number AS sort_jo,
				NULL AS entry_type,
				NULL AS id,
				NULL AS doctype,
				NULL AS jo_number,
				NULL AS posting_date,
				NULL AS supp_cust_code,
				NULL AS supplier,
				NULL AS item_code,
				NULL AS item_name,
				NULL AS warehouse,
				NULL AS unit,
				NULL AS uom,
				NULL AS qty,
				NULL AS unit_cost,
				NULL AS total_cost,
				NULL AS creation,
				NULL AS modified_by,
				NULL AS modified,
				NULL AS owner
			FROM (
				SELECT DISTINCT jo_number
				FROM (
					SELECT
						CASE
							WHEN sed.s_warehouse = %(warehouse)s THEN 'Materials Requirement'
							WHEN sed.t_warehouse = %(warehouse)s THEN 'Materials Requirement - Returns'
							ELSE 'Materials Requirement'
						END AS entry_type,
						COALESCE(sed.project, se.project, '') AS jo_number
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
						AND (%(project)s = '' OR COALESCE(sed.project, se.project) = %(project)s)

					UNION ALL

					SELECT
						'Adjustments on Inventory' AS entry_type,
						'' AS jo_number
					FROM `tabStock Reconciliation` sr
					JOIN `tabStock Reconciliation Item` sri ON sri.parent = sr.name
					WHERE
						sr.purpose = 'Stock Reconciliation'
						AND sri.warehouse = %(warehouse)s
						AND sr.posting_date BETWEEN %(from_date)s AND %(to_date)s
						AND sr.docstatus IN (0, 1, 2)
						AND %(project)s = ''

					UNION ALL

					SELECT
						'Receiving Reports' AS entry_type,
						COALESCE(pri.project, pr.project, '') AS jo_number
					FROM `tabPurchase Receipt` pr
					JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
					WHERE
						pri.warehouse = %(warehouse)s
						AND pr.posting_date BETWEEN %(from_date)s AND %(to_date)s
						AND pr.docstatus IN (0, 1, 2)
						AND (%(project)s = '' OR COALESCE(pri.project, pr.project) = %(project)s)
				) all_jos
				WHERE
					jo_number != ''
					AND (%(entry_type)s IS NULL
						OR %(entry_type)s = ''
						OR all_jos.entry_type = %(entry_type)s)
			) jo_list

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
				'<b> GRAND TOTAL </b>' AS supplier,
				NULL AS item_code,
				NULL AS item_name,
				NULL AS warehouse,
				NULL AS unit,
				NULL AS uom,
				SUM(audit_data.qty_diff) AS qty,
				CASE
					WHEN SUM(ABS(audit_data.qty_diff)) > 0
					THEN SUM(audit_data.total_cost) / SUM(ABS(audit_data.qty_diff))
					ELSE NULL
				END AS unit_cost,
				SUM(audit_data.total_cost) AS total_cost,
				NULL AS creation,
				NULL AS modified_by,
				NULL AS modified,
				NULL AS owner
			FROM (
				SELECT
					CASE
						WHEN sed.s_warehouse = %(warehouse)s THEN 'Materials Requirement'
						WHEN sed.t_warehouse = %(warehouse)s THEN 'Materials Requirement - Returns'
						ELSE 'Materials Requirement'
					END AS entry_type,
					CASE
						WHEN sed.s_warehouse = %(warehouse)s THEN sed.qty
						WHEN sed.t_warehouse = %(warehouse)s THEN -sed.qty
						ELSE sed.qty
					END AS qty_diff,
					COALESCE(sed.transfer_qty * sed.valuation_rate, 0) AS total_cost
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
					AND (%(project)s = '' OR COALESCE(sed.project, se.project) = %(project)s)

				UNION ALL

				SELECT
					'Adjustments on Inventory' AS entry_type,
					COALESCE(sri.quantity_difference, 0) AS qty_diff,
					COALESCE(sri.quantity_difference * sri.valuation_rate, 0) AS total_cost
				FROM `tabStock Reconciliation` sr
				JOIN `tabStock Reconciliation Item` sri ON sri.parent = sr.name
				WHERE
					sr.purpose = 'Stock Reconciliation'
					AND sri.warehouse = %(warehouse)s
					AND sr.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND sr.docstatus IN (0, 1, 2)
					AND %(project)s = ''

				UNION ALL

				SELECT
					'Receiving Reports' AS entry_type,
					pri.qty AS qty_diff,
					COALESCE(pri.stock_qty * pri.valuation_rate, 0) AS total_cost
				FROM `tabPurchase Receipt` pr
				JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
				WHERE
					pri.warehouse = %(warehouse)s
					AND pr.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND pr.docstatus IN (0, 1, 2)
					AND (%(project)s = '' OR COALESCE(pri.project, pr.project) = %(project)s)
			) audit_data
			WHERE
				(%(entry_type)s IS NULL
				OR %(entry_type)s = ''
				OR audit_data.entry_type = %(entry_type)s)

		) final_result
		ORDER BY
			sort_jo,
			sort_order,
			posting_date,
			entry_type,
			item_code
	"""

	return frappe.db.sql(sql, params, as_dict=True)