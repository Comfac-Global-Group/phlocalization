# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"fieldname": "proj",               "label": "PROJECT ID",            "fieldtype": "Link", "options": "Project",      "width": 160},
		{"fieldname": "sales_order",        "label": "S.O. No.",              "fieldtype": "Link", "options": "Sales Order",  "width": 150},
		{"fieldname": "department",         "label": "DEPARTMENT",            "fieldtype": "Link", "options": "Department",   "width": 370},
		{"fieldname": "customer",           "label": "CUSTOMER",              "fieldtype": "Link", "options": "Customer",     "width": 160},
		{"fieldname": "customer_name",      "label": "CUSTOMER NAME",         "fieldtype": "Data",                            "width": 280},
		{"fieldname": "remarks_html",       "label": "SALES INVOICE REMARKS", "fieldtype": "HTML",                            "width": 200},
		{"fieldname": "description",        "label": "DESCRIPTION",           "fieldtype": "Data",                            "width": 300},
		{"fieldname": "sales_html",         "label": "SALES",                 "fieldtype": "HTML",                            "width": 180},
		{"fieldname": "actual_cos_html",    "label": "ACTUAL COS",            "fieldtype": "HTML",                            "width": 170},
		{"fieldname": "accrued_cos_html",   "label": "ACCRUED COS",           "fieldtype": "HTML",                            "width": 170},
		{"fieldname": "cost_of_sales_html", "label": "COST OF SALES",         "fieldtype": "HTML",                            "width": 170},
		{"fieldname": "cost_pct_html",      "label": "COST %",                "fieldtype": "HTML",                            "width":  90},
	]

def get_data(filters):
	params = {
		"company":            filters.get("company"),
		"from_date":          filters.get("from_date"),
		"to_date":            filters.get("to_date"),
		"project":            "%" + filters.get("project", "") + "%" if filters.get("project") else "",
		"invoice_filter":     filters.get("invoice_filter") or "Show even without Invoices",
		"hide_zero_projects": 1 if filters.get("hide_zero_projects") else 0,
	}

	sql = """
		WITH project_rows AS (
			SELECT
				p.name                                  AS proj,
				p.sales_order                           AS sales_order,
				p.department                            AS department,
				p.customer                              AS customer,
				cust.customer_name                      AS customer_name,
				si.remarks_html                         AS remarks_html,
				si.si_item_descriptions                 AS description,
				COALESCE(si.si_items_total_base, 0)     AS sales,
				COALESCE(actual_cos.actual_amount, 0)   AS actual_cos,
				COALESCE(accrued_cos.accrued_amount, 0) AS accrued_amount_raw,
				accrued_cos.accrued_amount_html         AS accrued_cos_html,
				(COALESCE(actual_cos.actual_amount, 0) + COALESCE(accrued_cos.accrued_amount, 0)) AS cost_of_sales,
				CASE
					WHEN COALESCE(si.si_items_total_base, 0) = 0 THEN NULL
					ELSE (COALESCE(actual_cos.actual_amount, 0) + COALESCE(accrued_cos.accrued_amount, 0))
						 / COALESCE(si.si_items_total_base, 0) * 100
				END                                     AS cost_pct,
				si.si_name_flag                         AS si_name_flag

			FROM `tabProject` p

			LEFT JOIN (
				SELECT
					COALESCE(NULLIF(sii.project, ''), '<<NO PROJECT>>') AS project,
					SUM(sii.base_net_amount) AS si_items_total_base,
					GROUP_CONCAT(
						DISTINCT
						CONCAT('<a href="/app/sales-invoice/', si.name, '">', si.remarks, '</a>')
						SEPARATOR '<br>'
					) AS remarks_html,
					GROUP_CONCAT(
						DISTINCT
						CASE
							WHEN LOCATE(' - ', sii.description) > 0
							THEN SUBSTRING(sii.description, LOCATE(' - ', sii.description) + 2)
							ELSE sii.description
						END
						SEPARATOR '; '
					) AS si_item_descriptions,
					MAX(si.name) AS si_name_flag
				FROM `tabSales Invoice` si
				JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
				WHERE si.docstatus = 1
					AND si.company = %(company)s
					AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND ( %(project)s = '' OR sii.project LIKE %(project)s )
				GROUP BY COALESCE(NULLIF(sii.project, ''), '<<NO PROJECT>>')
			) si ON si.project = p.name

			LEFT JOIN (
				SELECT
					project,
					accrued_amount,
					CASE
						WHEN accrued_amount = 0 OR first_je IS NULL THEN CONCAT('₱ ', FORMAT(accrued_amount, 2))
						ELSE CONCAT(
							'<a href="/app/journal-entry/',
							first_je,
							'" style="color: inherit; text-decoration: none;">₱ ',
							FORMAT(accrued_amount, 2),
							'</a>'
						)
					END AS accrued_amount_html
				FROM (
					SELECT
						COALESCE(NULLIF(gle.project, ''), '<<NO PROJECT>>') AS project,
						SUM(IFNULL(gle.credit, 0) - IFNULL(gle.debit, 0)) AS accrued_amount,
						(
							SELECT je.name
							FROM `tabGL Entry` gle2
							JOIN `tabAccount` a2 ON a2.name = gle2.account
							JOIN `tabJournal Entry` je ON je.name = gle2.voucher_no
							WHERE gle2.is_cancelled = 0
								AND je.docstatus = 1
								AND gle2.company = %(company)s
								AND gle2.posting_date BETWEEN %(from_date)s AND %(to_date)s
								AND COALESCE(NULLIF(gle2.project, ''), '<<NO PROJECT>>') = COALESCE(NULLIF(gle.project, ''), '<<NO PROJECT>>')
								AND a2.account_number LIKE '2404%%'
							ORDER BY gle2.posting_date ASC, gle2.voucher_no ASC
							LIMIT 1
						) AS first_je
					FROM `tabGL Entry` gle
					JOIN `tabAccount` a ON a.name = gle.account
					JOIN `tabJournal Entry` je_check ON je_check.name = gle.voucher_no
					WHERE gle.is_cancelled = 0
						AND je_check.docstatus = 1
						AND gle.company = %(company)s
						AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
						AND gle.voucher_type = 'Journal Entry'
						AND gle.project IS NOT NULL AND gle.project != ''
						AND a.account_number LIKE '2404%%'
						AND ( %(project)s = '' OR gle.project LIKE %(project)s )
					GROUP BY COALESCE(NULLIF(gle.project, ''), '<<NO PROJECT>>')
				) sub
			) accrued_cos ON accrued_cos.project = p.name

			LEFT JOIN (
				SELECT
					COALESCE(NULLIF(gle.project, ''), '<<NO PROJECT>>') AS project,
					SUM(IFNULL(gle.credit, 0)) AS actual_amount
				FROM `tabGL Entry` gle
				JOIN `tabAccount` a ON a.name = gle.account
				JOIN `tabJournal Entry` je_check ON je_check.name = gle.voucher_no
				WHERE gle.is_cancelled = 0
					AND je_check.docstatus = 1
					AND gle.company = %(company)s
					AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND gle.voucher_type = 'Journal Entry'
					AND gle.project IS NOT NULL AND gle.project != ''
					AND a.account_number LIKE '1521%%'
					AND ( %(project)s = '' OR gle.project LIKE %(project)s )
				GROUP BY COALESCE(NULLIF(gle.project, ''), '<<NO PROJECT>>')
			) actual_cos ON actual_cos.project = p.name

			LEFT JOIN `tabCustomer` cust ON cust.name = p.customer

			WHERE p.company = %(company)s
			  AND ( %(project)s = '' OR p.name LIKE %(project)s )
			  AND IF(%(invoice_filter)s = 'With Invoices', si.si_name_flag IS NOT NULL, 1=1)
			  AND IF(
					%(hide_zero_projects)s = 1,
					(
						COALESCE(si.si_items_total_base, 0) <> 0
						OR COALESCE(actual_cos.actual_amount, 0) <> 0
						OR COALESCE(accrued_cos.accrued_amount, 0) <> 0
					),
					1=1
			  )
		)

		SELECT
			proj, sales_order, department, customer, customer_name,
			remarks_html, description,
			sales_html, actual_cos_html, accrued_cos_html,
			cost_of_sales_html, cost_pct_html
		FROM (

			SELECT
				proj, sales_order, department, customer, customer_name,
				remarks_html, description,
				CONCAT('₱ ', FORMAT(sales, 2))         AS sales_html,
				CONCAT('₱ ', FORMAT(actual_cos, 2))    AS actual_cos_html,
				accrued_cos_html,
				CONCAT('₱ ', FORMAT(cost_of_sales, 2)) AS cost_of_sales_html,
				CASE
					WHEN cost_pct IS NULL THEN ''
					ELSE CONCAT(FORMAT(cost_pct, 2), '%%')
				END                                     AS cost_pct_html,
				1     AS sort_order,
				proj  AS sort_key
			FROM project_rows

			UNION ALL
			SELECT
				NULL, NULL, NULL, NULL, NULL,
				'<b>SUBTOTAL</b>',
				NULL,
				CONCAT('<b>₱ ', FORMAT(COALESCE(SUM(sales), 0), 2),              '</b>'),
				CONCAT('<b>₱ ', FORMAT(COALESCE(SUM(actual_cos), 0), 2),         '</b>'),
				CONCAT('<b>₱ ', FORMAT(COALESCE(SUM(accrued_amount_raw), 0), 2), '</b>'),
				CONCAT('<b>₱ ', FORMAT(COALESCE(SUM(cost_of_sales), 0), 2),      '</b>'),
				CASE
					WHEN COALESCE(SUM(sales), 0) = 0 THEN ''
					ELSE CONCAT('<b>', FORMAT(SUM(cost_of_sales) / SUM(sales) * 100, 2), '%%</b>')
				END,
				2, ''
			FROM project_rows

			UNION ALL
			SELECT
				NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
				3, ''

			UNION ALL
			SELECT
				NULL, NULL, NULL, NULL, NULL,
				'PAYROLL',
				CONCAT('COS - OVERHEAD (',
					   UPPER(SUBSTRING(MONTHNAME(%(from_date)s), 1, 2)),
					   ' ', YEAR(%(from_date)s), ')'),
				CONCAT('₱ ', FORMAT(0, 2)),
				CONCAT('₱ ', FORMAT(COALESCE(payroll.amount, 0), 2)),
				'₱ 0.00',
				CONCAT('₱ ', FORMAT(COALESCE(payroll.amount, 0), 2)),
				'',
				4, ''
			FROM (
				SELECT SUM(IFNULL(gle.debit, 0) - IFNULL(gle.credit, 0)) AS amount
				FROM `tabGL Entry` gle
				JOIN `tabAccount` a ON a.name = gle.account
				JOIN `tabJournal Entry` je_check ON je_check.name = gle.voucher_no
				WHERE gle.is_cancelled = 0
					AND je_check.docstatus = 1
					AND gle.company = %(company)s
					AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND gle.voucher_type = 'Journal Entry'
					AND a.account_number LIKE '4603%%'
			) payroll

			UNION ALL
			SELECT
				NULL, NULL, NULL, NULL, NULL,
				'<b>GRAND TOTAL</b>',
				NULL,
				CONCAT('<b>₱ ', FORMAT(COALESCE(t.total_sales, 0), 2), '</b>'),
				CONCAT('<b>₱ ', FORMAT(COALESCE(t.total_actual, 0) + COALESCE(p.amount, 0), 2), '</b>'),
				CONCAT('<b>₱ ', FORMAT(COALESCE(t.total_accrued, 0), 2), '</b>'),
				CONCAT('<b>₱ ', FORMAT(COALESCE(t.total_cost, 0) + COALESCE(p.amount, 0), 2), '</b>'),
				CASE
					WHEN COALESCE(t.total_sales, 0) = 0 THEN ''
					ELSE CONCAT('<b>',
								FORMAT((COALESCE(t.total_cost, 0) + COALESCE(p.amount, 0))
									   / t.total_sales * 100, 2),
								'%%</b>')
				END,
				5, ''
			FROM (
				SELECT
					SUM(sales)              AS total_sales,
					SUM(actual_cos)         AS total_actual,
					SUM(accrued_amount_raw) AS total_accrued,
					SUM(cost_of_sales)      AS total_cost
				FROM project_rows
			) t
			CROSS JOIN (
				SELECT SUM(IFNULL(gle.debit, 0) - IFNULL(gle.credit, 0)) AS amount
				FROM `tabGL Entry` gle
				JOIN `tabAccount` a ON a.name = gle.account
				JOIN `tabJournal Entry` je_check ON je_check.name = gle.voucher_no
				WHERE gle.is_cancelled = 0
					AND je_check.docstatus = 1
					AND gle.company = %(company)s
					AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND gle.voucher_type = 'Journal Entry'
					AND a.account_number LIKE '4603%%'
			) p

		) combined
		ORDER BY combined.sort_order, combined.sort_key
	"""

	return frappe.db.sql(sql, params, as_dict=True)