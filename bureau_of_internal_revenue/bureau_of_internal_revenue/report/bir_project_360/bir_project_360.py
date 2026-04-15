# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	"""
	Validates filters and prepares optional project filtering.
	Fetches report columns and data for the Project 360 report.
	Returns columns and data as a tuple.
	"""
	filters = filters or {}

	if not filters.get("company"):
		frappe.throw("Company is required")

	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw("From Date and To Date are required")

	if filters.get("from_date") > filters.get("to_date"):
		frappe.throw("From Date cannot be greater than To Date")

	project = filters.get("project_like", "")
	if not project:
		return get_columns(), []

	filters["project_like"] = f"%{project}%"

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	"""
	Defines the column structure for the report.
	Includes project details, financial metrics, remarks, and computed fields.
	Returns a list of column definitions.
	"""
	return [
		{"label": "Project ID", "fieldname": "project_id", "fieldtype": "Link", "options": "Project", "width": 140},
		{"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": "Earliest SO", "fieldname": "earliest_so", "fieldtype": "Link", "options": "Sales Order", "width": 160},
		{"label": "Estimated Start Date", "fieldname": "expected_start_date", "fieldtype": "Date", "width": 110},

		{"label": "Total SI Items (Base)", "fieldname": "si_total", "fieldtype": "Currency", "options": "currency", "width": 180},
		{"label": "Total Purchase Invoices", "fieldname": "pi_total", "fieldtype": "Currency", "options": "currency", "width": 170},
		{"label": "Project MR (from Stores)", "fieldname": "mr_amount", "fieldtype": "Currency", "options": "currency", "width": 160},
		{"label": "Project MRS (to Stores)", "fieldname": "mrs_amount", "fieldtype": "Currency", "options": "currency", "width": 160},
		{"label": "Timesheets Costing", "fieldname": "ts_amount", "fieldtype": "Currency", "options": "currency", "width": 180},
		{"label": "Expense Claims", "fieldname": "ec_amount", "fieldtype": "Currency", "options": "currency", "width": 160},

		{"label": "Purchase Invoice Remarks", "fieldname": "pi_remarks", "fieldtype": "HTML", "width": 300},
		{"label": "Journal Entry Remarks", "fieldname": "je_remarks", "fieldtype": "HTML", "width": 300},

		{"label": "JO Total", "fieldname": "jo_total", "fieldtype": "Currency", "options": "currency", "width": 170},
		{"label": "Remainder", "fieldname": "remainder", "fieldtype": "Currency", "options": "currency", "width": 160},

		{"label": "Sales Order Items", "fieldname": "so_items", "fieldtype": "Data", "width": 300},
	]


def get_data(filters):
	"""
	Runs a SQL query to fetch aggregated project-level data.
	Combines multiple doctypes like invoices, timesheets, stock, and expenses.
	Returns the result as a list of dictionaries.
	"""

	query = """
SELECT
	p.name AS project_id,
	p.department AS department,
	p.customer AS customer,
	cust.customer_name AS customer_name,
	e.so_name AS earliest_so,
	p.expected_start_date AS expected_start_date,

	comp.default_currency AS currency,

	COALESCE(si.si_items_total_base, 0) AS si_total,
	COALESCE(pt.pi_total, 0) AS pi_total,
	COALESCE(mr.mr_amount, 0) AS mr_amount,
	COALESCE(mrs.mrs_amount, 0) AS mrs_amount,
	COALESCE(ts.ts_costing_amount, 0) AS ts_amount,
	COALESCE(ec.ec_amount, 0) AS ec_amount,

	COALESCE(pir.pi_remarks_html, '') AS pi_remarks,
	COALESCE(jeur.je_user_remarks_html,'') AS je_remarks,

	(
		COALESCE(pt.pi_total, 0)
	  + COALESCE(mr.mr_amount, 0)
	  - COALESCE(mrs.mrs_amount, 0)
	  + COALESCE(ts.ts_costing_amount, 0)
	) AS jo_total,

	(
		COALESCE(si.si_items_total_base, 0)
	  - (COALESCE(pt.pi_total, 0) + COALESCE(mr.mr_amount, 0) + COALESCE(ts.ts_costing_amount, 0))
	) AS remainder,

	(
		SELECT IFNULL(GROUP_CONCAT(IFNULL(soi.item_name, soi.item_code) ORDER BY soi.idx SEPARATOR ', '), '')
		FROM `tabSales Order Item` soi
		WHERE soi.parent = e.so_name
	) AS so_items

	FROM `tabProject` p

	LEFT JOIN `tabCustomer` cust ON cust.name = p.customer
	LEFT JOIN `tabCompany` comp ON comp.name = p.company

	/* Earliest SO per project - header-level project link only (soi.project does not exist) */
	LEFT JOIN (
	SELECT
		p2.name AS project,
		(
			SELECT so2.name
			FROM `tabSales Order` so2
			WHERE so2.company = p2.company
			  AND so2.project = p2.name
			  AND so2.transaction_date BETWEEN %(from_date)s AND %(to_date)s
			ORDER BY so2.transaction_date ASC, so2.name ASC
			LIMIT 1
		) AS so_name,
		(
			SELECT MIN(so3.transaction_date)
			FROM `tabSales Order` so3
			WHERE so3.company = p2.company
			  AND so3.project = p2.name
			  AND so3.transaction_date BETWEEN %(from_date)s AND %(to_date)s
		) AS so_date
	FROM `tabProject` p2
	WHERE p2.company = %(company)s
	  AND p2.name LIKE %(project_like)s
	) e ON e.project = p.name

	/* Purchase Invoices grouped by project on PI item (amounts) */
	LEFT JOIN (
		SELECT t.project, SUM(t.grand_total) AS pi_total
		FROM (
			SELECT DISTINCT pi.name, pii.project, pi.grand_total
			FROM `tabPurchase Invoice` pi
			JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
			WHERE pi.docstatus = 1
			  AND pi.company = %(company)s
			  AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
			  AND pii.project IS NOT NULL AND pii.project != ''
			  AND pii.project LIKE %(project_like)s
		) t
		GROUP BY t.project
	) pt ON pt.project = p.name

	/* Sales Invoice Items grouped by item.project */
	LEFT JOIN (
		SELECT
			COALESCE(NULLIF(sii.project, ''), '<<NO PROJECT>>') AS project,
			SUM(sii.base_net_amount) AS si_items_total_base,
			SUM(sii.net_amount)      AS si_items_total_txn
		FROM `tabSales Invoice` si
		JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND si.company = %(company)s
		  AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
		  AND sii.project LIKE %(project_like)s
		GROUP BY COALESCE(NULLIF(sii.project, ''), '<<NO PROJECT>>')
	) si ON si.project = p.name

	/* Timesheets grouped by tsd.project */
	LEFT JOIN (
		SELECT
			COALESCE(NULLIF(tsd.project, ''), '<<NO PROJECT>>') AS project,
			SUM(tsd.costing_amount) AS ts_costing_amount
		FROM `tabTimesheet Detail` tsd
		JOIN `tabTimesheet` ts ON ts.name = tsd.parent
		WHERE ts.docstatus = 1
		  AND ts.company = %(company)s
		  AND ts.start_date BETWEEN %(from_date)s AND %(to_date)s
		  AND tsd.project LIKE %(project_like)s
		GROUP BY COALESCE(NULLIF(tsd.project, ''), '<<NO PROJECT>>')
	) ts ON ts.project = p.name

/* Expense Claims grouped by detail.project (sanctioned amount preferred) */
LEFT JOIN (
	SELECT
		COALESCE(NULLIF(ecd.project, ''), '<<NO PROJECT>>') AS project,
		SUM(IFNULL(ecd.sanctioned_amount, IFNULL(ecd.amount, 0))) AS ec_amount
	FROM `tabExpense Claim` ec
	JOIN `tabExpense Claim Detail` ecd ON ecd.parent = ec.name
	WHERE ec.docstatus = 1
	  AND ec.company = %(company)s
	  AND ec.posting_date BETWEEN %(from_date)s AND %(to_date)s
	  AND ecd.project LIKE %(project_like)s
	GROUP BY COALESCE(NULLIF(ecd.project, ''), '<<NO PROJECT>>')
) ec ON ec.project = p.name

/* PI remarks rendered as links */
LEFT JOIN (
	SELECT
		COALESCE(NULLIF(pii.project, ''), '<<NO PROJECT>>') AS project,
		GROUP_CONCAT(
			DISTINCT CONCAT(
				'<a href="#Form/Purchase Invoice/', pi.name, '">',
				COALESCE(NULLIF(TRIM(pi.remarks), ''), pi.name),
				'</a>'
			)
			ORDER BY pi.posting_date, pi.name SEPARATOR '; '
		) AS pi_remarks_html
	FROM `tabPurchase Invoice` pi
	JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
	WHERE pi.docstatus = 1
	  AND pi.company = %(company)s
	  AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
	  AND pii.project IS NOT NULL
	  AND pii.project LIKE %(project_like)s
	GROUP BY COALESCE(NULLIF(pii.project, ''), '<<NO PROJECT>>')
) pir ON pir.project = p.name

/* Journal Entry user remarks rendered as links */
LEFT JOIN (
	SELECT
		COALESCE(NULLIF(jea.project, ''), '<<NO PROJECT>>') AS project,
		GROUP_CONCAT(
			DISTINCT CONCAT(
				'<a href="#Form/Journal Entry/', je.name, '">',
				COALESCE(NULLIF(TRIM(je.user_remark), ''), je.name),
				'</a>'
			)
			ORDER BY je.posting_date, je.name SEPARATOR '; '
		) AS je_user_remarks_html
	FROM `tabJournal Entry` je
	JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
	WHERE je.docstatus = 1
	  AND je.company = %(company)s
	  AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
	  AND jea.project LIKE %(project_like)s
	GROUP BY COALESCE(NULLIF(jea.project, ''), '<<NO PROJECT>>')
	) jeur ON jeur.project = p.name

	/* Stock Entry: MR (from Stores) */
	LEFT JOIN (
		SELECT
			COALESCE(NULLIF(COALESCE(sed.project, se.project), ''), '<<NO PROJECT>>') AS project,
			SUM(IFNULL(sed.basic_amount, 0)) AS mr_amount
		FROM `tabStock Entry` se
		JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		WHERE se.docstatus = 1
		  AND se.company = %(company)s
		  AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
		  AND COALESCE(sed.project, se.project) LIKE %(project_like)s
		  AND IFNULL(sed.s_warehouse, '') LIKE '%%Stores%%'
		GROUP BY COALESCE(NULLIF(COALESCE(sed.project, se.project), ''), '<<NO PROJECT>>')
	) mr ON mr.project = p.name

	/* Stock Entry: MRS (to Stores) */
	LEFT JOIN (
		SELECT
			COALESCE(NULLIF(COALESCE(sed.project, se.project), ''), '<<NO PROJECT>>') AS project,
			SUM(IFNULL(sed.basic_amount, 0)) AS mrs_amount
		FROM `tabStock Entry` se
		JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		WHERE se.docstatus = 1
		  AND se.company = %(company)s
		  AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
		  AND COALESCE(sed.project, se.project) LIKE %(project_like)s
		  AND IFNULL(sed.t_warehouse, '') LIKE '%%Stores%%'
		GROUP BY COALESCE(NULLIF(COALESCE(sed.project, se.project), ''), '<<NO PROJECT>>')
	) mrs ON mrs.project = p.name

	WHERE p.company = %(company)s
	  AND p.name LIKE %(project_like)s

	ORDER BY p.name;
	"""

	return frappe.db.sql(query, filters, as_dict=True)