# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"label": _("JO Number"), "fieldtype": "HTML", "fieldname": "jo_number", "width": 250},
		{"label": _("Date"), "fieldtype": "Date", "fieldname": "jdate", "width": 120},
		{"label": _("Account"), "fieldtype": "Data", "fieldname": "accounts", "width": 250},
		{"label": _("Customer"), "fieldtype": "Link", "fieldname": "customer_name", "options": "Customer", "width": 150},
		{"label": _("Product Line"), "fieldtype": "Data", "fieldname": "item_code", "width": 150},
		{"label": _("Description"), "fieldtype": "Data", "fieldname": "descrip", "width": 250},
		{"label": _("YTD Matls"), "fieldtype": "Currency", "fieldname": "ytd_matls", "width": 120},
		{"label": _("YTD Labor"), "fieldtype": "Currency", "fieldname": "ytd_labor", "width": 120},
		{"label": _("YTD OH"), "fieldtype": "Currency", "fieldname": "ytd_oh", "width": 120},
		{"label": _("YTD GL"), "fieldtype": "Currency", "fieldname": "ytd_gl", "width": 120},
		{"label": _("MTD Matls"), "fieldtype": "Currency", "fieldname": "mtd_matls", "width": 120},
		{"label": _("MTD Labor"), "fieldtype": "Currency", "fieldname": "mtd_labor", "width": 120},
		{"label": _("MTD OH"), "fieldtype": "Currency", "fieldname": "mtd_oh", "width": 120},
		{"label": _("MTD GL"), "fieldtype": "Currency", "fieldname": "mtd_gl", "width": 120},
		{"label": _("JO Total"), "fieldtype": "Currency", "fieldname": "jo_total", "width": 120},
	]

def get_data(filters):
	sql = """
		SELECT * FROM (
		WITH
		-- Pre-aggregate sales order data by project (ONE ROW PER PROJECT)
		SalesOrderData AS (
			SELECT
				p.name AS project,
				MIN(so.transaction_date) AS first_transaction_date,
				MAX(so.customer_name) AS customer_name,
				GROUP_CONCAT(DISTINCT soi.item_code ORDER BY soi.item_code SEPARATOR ', ') AS item_code
			FROM `tabProject` p
			JOIN `tabSales Order` so ON so.name = p.sales_order
			LEFT JOIN `tabSales Order Item` soi ON soi.parent = so.name
			WHERE p.sales_order IS NOT NULL
			GROUP BY p.name
		),

		-- STOCK ENTRY DATA (Material Transfer - MR/MRS)
		StockEntryData AS (
			SELECT
				COALESCE(sed.project, se.project) AS project,
				se.posting_date,
				CASE
					WHEN se.stock_entry_type = 'Material Transfer'
					AND COALESCE(sed.s_warehouse, '') LIKE 'Stores%%'
						THEN sed.amount
					WHEN se.stock_entry_type = 'Material Transfer'
					AND COALESCE(sed.s_warehouse, '') NOT LIKE 'Stores%%'
						THEN 0
					ELSE sed.amount
				END AS debit,
				CASE
					WHEN se.stock_entry_type = 'Material Transfer'
					AND COALESCE(sed.s_warehouse, '') LIKE 'Stores%%'
						THEN 0
					WHEN se.stock_entry_type = 'Material Transfer'
					AND COALESCE(sed.s_warehouse, '') NOT LIKE 'Stores%%'
						THEN sed.amount
					ELSE 0
				END AS credit,
				CASE
					WHEN se.stock_entry_type = 'Material Transfer'
					AND COALESCE(sed.s_warehouse, '') LIKE 'Stores%%'
						THEN sed.amount
					WHEN se.stock_entry_type = 'Material Transfer'
					AND COALESCE(sed.s_warehouse, '') NOT LIKE 'Stores%%'
						THEN -sed.amount
					ELSE sed.amount
				END AS net_change
			FROM `tabStock Entry` se
			JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
			WHERE se.docstatus = 1
			AND se.company = %(company)s
			AND se.posting_date <= %(to_date)s
			AND COALESCE(sed.project, se.project) IS NOT NULL
		),

		-- Stock Reconciliation Data (from GL Entry) -- uses standard gle.project
		StockReconciliationData AS (
			SELECT
				gle.project AS project,
				gle.posting_date,
				gle.debit,
				gle.credit,
				(gle.debit - gle.credit) AS net_change
			FROM `tabGL Entry` gle
			JOIN `tabStock Reconciliation` sr ON sr.name = gle.voucher_no
			WHERE gle.company = %(company)s
			AND gle.posting_date <= %(to_date)s
			AND gle.voucher_type = 'Stock Reconciliation'
			AND gle.project IS NOT NULL
			AND gle.account LIKE '1521 - PROJECTS IN PROGRESS - ESC2%%'
		),

		StockTransactions AS (
			SELECT project, posting_date, debit, credit, net_change
			FROM StockEntryData

			UNION ALL

			SELECT project, posting_date, debit, credit, net_change
			FROM StockReconciliationData
		),

		-- YTD GL Transactions (everything strictly before from_date)
		YTDGLTransactions AS (
			SELECT
				gle.project,
				gle.posting_date,
				gle.account AS expense_account,
				gle.debit,
				gle.credit
			FROM `tabGL Entry` gle
			WHERE gle.docstatus = 1
			AND gle.company = %(company)s
			AND gle.posting_date < %(from_date)s
			AND gle.project IS NOT NULL
			AND gle.voucher_type = 'Journal Entry'
			AND (
				gle.voucher_no LIKE 'ACC-JV-A-%%'
				OR gle.voucher_no LIKE 'ACC-JV-O-%%'
				OR gle.voucher_no LIKE 'ACC-JVP-%%'
			)
			AND gle.account LIKE '1521 - PROJECTS IN PROGRESS - ESC2%%'

			UNION ALL

			SELECT
				pii.project,
				pi.posting_date,
				pii.expense_account,
				pii.base_amount AS debit,
				0 AS credit
			FROM `tabPurchase Invoice` pi
			INNER JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
			WHERE pi.docstatus = 1
			AND pi.company = %(company)s
			AND pi.posting_date < %(from_date)s
			AND pii.project IS NOT NULL
		),

		-- MTD GL Transactions (within from_date .. to_date)
		MTDGLTransactions AS (
			SELECT
				gle.project,
				gle.posting_date,
				gle.account AS expense_account,
				gle.debit,
				gle.credit
			FROM `tabGL Entry` gle
			WHERE gle.docstatus = 1
			AND gle.company = %(company)s
			AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND gle.project IS NOT NULL
			AND gle.voucher_type = 'Journal Entry'
			AND (
				gle.voucher_no LIKE 'ACC-JV-A-%%'
				OR gle.voucher_no LIKE 'ACC-JV-O-%%'
				OR gle.voucher_no LIKE 'ACC-JVP-%%'
			)
			AND gle.account LIKE '1521 - PROJECTS IN PROGRESS - ESC2%%'

			UNION ALL

			SELECT
				pii.project,
				pi.posting_date,
				pii.expense_account,
				pii.base_amount AS debit,
				0 AS credit
			FROM `tabPurchase Invoice` pi
			INNER JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
			WHERE pi.docstatus = 1
			AND pi.company = %(company)s
			AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND pii.project IS NOT NULL
		),

		-- Aggregate STOCK transactions by project
		ProjectData AS (
			SELECT
				project,
				COALESCE(SUM(
					CASE
						WHEN posting_date < %(from_date)s THEN net_change
						ELSE 0
					END
				), 0) AS ytd_matls,
				COALESCE(SUM(
					CASE
						WHEN posting_date BETWEEN %(from_date)s AND %(to_date)s THEN net_change
						ELSE 0
					END
				), 0) AS mtd_matls
			FROM StockTransactions
			WHERE project IS NOT NULL
			GROUP BY project
		),

		-- Per-project YTD GL aggregate (one row per project)
		YTDGLData AS (
			SELECT
				project,
				SUM(COALESCE(debit, 0) - COALESCE(credit, 0)) AS ytd_gl
			FROM YTDGLTransactions
			WHERE project IS NOT NULL
			GROUP BY project
		),

		-- Per-project MTD GL aggregate (one row per project)
		MTDGLData AS (
			SELECT
				project,
				SUM(COALESCE(debit, 0) - COALESCE(credit, 0)) AS mtd_gl,
				MIN(posting_date) AS min_posting_date,
				GROUP_CONCAT(DISTINCT expense_account ORDER BY expense_account SEPARATOR ', ') AS accounts
			FROM MTDGLTransactions
			WHERE project IS NOT NULL
			GROUP BY project
		),

		-- All projects that have any GL activity (YTD or MTD)
		GLProjects AS (
			SELECT project FROM YTDGLData
			UNION
			SELECT project FROM MTDGLData
		),

		-- Combine YTD and MTD GL by project via JOIN (no correlated subquery)
		GLData AS (
			SELECT
				gp.project,
				COALESCE(y.ytd_gl, 0) AS ytd_gl,
				COALESCE(m.mtd_gl, 0) AS mtd_gl,
				m.min_posting_date,
				m.accounts
			FROM GLProjects gp
			LEFT JOIN YTDGLData y ON y.project = gp.project
			LEFT JOIN MTDGLData m ON m.project = gp.project
		),

		-- ALL PROJECTS
		AllProjects AS (
			SELECT project FROM ProjectData
			UNION
			SELECT project FROM GLData
		),

		-- CALCULATE OVERALL TOTALS
		OverallTotals AS (
			SELECT
				SUM(COALESCE(pd.ytd_matls, 0)) AS total_ytd_matls,
				SUM(COALESCE(gd.ytd_gl, 0)) AS total_ytd_gl,
				SUM(COALESCE(pd.mtd_matls, 0)) AS total_mtd_matls,
				SUM(COALESCE(gd.mtd_gl, 0)) AS total_mtd_gl
			FROM AllProjects ap
			LEFT JOIN ProjectData pd ON ap.project = pd.project
			LEFT JOIN GLData gd ON ap.project = gd.project
		),

		-- COMBINE PROJECT DATA WITH OVERALL TOTAL ROW
		CombinedData AS (
			SELECT
				ap.project,
				COALESCE(sod.first_transaction_date, gd.min_posting_date) AS jdate,
				gd.accounts,
				sod.customer_name,
				sod.item_code,
				p.notes AS descrip,
				COALESCE(pd.ytd_matls, 0) AS ytd_matls,
				0 AS ytd_labor,
				0 AS ytd_oh,
				COALESCE(gd.ytd_gl, 0) AS ytd_gl,
				COALESCE(pd.mtd_matls, 0) AS mtd_matls,
				0 AS mtd_labor,
				0 AS mtd_oh,
				COALESCE(gd.mtd_gl, 0) AS mtd_gl,
				(COALESCE(pd.ytd_matls, 0) + COALESCE(gd.ytd_gl, 0) +
				COALESCE(pd.mtd_matls, 0) + COALESCE(gd.mtd_gl, 0)) AS jo_total,
				1 AS sort_order
			FROM AllProjects ap
			LEFT JOIN ProjectData pd ON ap.project = pd.project
			LEFT JOIN GLData gd ON ap.project = gd.project
			LEFT JOIN `tabProject` p ON p.name = ap.project
			LEFT JOIN SalesOrderData sod ON sod.project = ap.project

			UNION ALL

			SELECT
				'<B>OVERALL TOTAL</B>' AS project,
				NULL AS jdate,
				NULL AS accounts,
				NULL AS customer_name,
				NULL AS item_code,
				NULL AS descrip,
				ot.total_ytd_matls AS ytd_matls,
				0 AS ytd_labor,
				0 AS ytd_oh,
				ot.total_ytd_gl AS ytd_gl,
				ot.total_mtd_matls AS mtd_matls,
				0 AS mtd_labor,
				0 AS mtd_oh,
				ot.total_mtd_gl AS mtd_gl,
				(ot.total_ytd_matls + ot.total_ytd_gl + ot.total_mtd_matls + ot.total_mtd_gl) AS jo_total,
				2 AS sort_order
			FROM OverallTotals ot
		)

		-- Final SELECT  (aliases MUST match get_columns fieldnames)
		SELECT
			IF(
				project LIKE '<B>OVERALL TOTAL</B>',
				project,
				CONCAT('<a href="/app/project/', project, '">', project, '</a>')
			) AS jo_number,
			jdate AS jdate,
			accounts AS accounts,
			customer_name AS customer_name,
			item_code AS item_code,
			descrip AS descrip,
			ROUND(ytd_matls, 2) AS ytd_matls,
			ROUND(ytd_labor, 2) AS ytd_labor,
			ROUND(ytd_oh, 2) AS ytd_oh,
			ROUND(ytd_gl, 2) AS ytd_gl,
			ROUND(mtd_matls, 2) AS mtd_matls,
			ROUND(mtd_labor, 2) AS mtd_labor,
			ROUND(mtd_oh, 2) AS mtd_oh,
			ROUND(mtd_gl, 2) AS mtd_gl,
			ROUND(jo_total, 2) AS jo_total
		FROM CombinedData
		ORDER BY sort_order, project
		) AS final_query
		"""
	return frappe.db.sql(sql, filters, as_dict=True)