# Copyright (c) 2026, Ambibuzz Technologies LLP
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict
from frappe.utils import getdate, add_months, formatdate


def execute(filters=None):
	"""
	Main execution function for the report.
	Validates filters, prepares columns, and fetches report data.
	"""
	filters = frappe._dict(filters or {})

	filters.setdefault("cost_center", "")
	filters.setdefault("row_mode", "All")
	filters.setdefault("periodicity", "")

	filters.row_mode = (filters.row_mode or "").strip()
	validate_filters(filters)

	if filters.periodicity == "Monthly":
		columns = get_monthly_columns(filters)
		data = get_monthly_data(filters)
	else:
		columns = get_columns()
		data = get_data(filters)

	return columns, data


def validate_filters(filters):
	"""
	Validate mandatory filters and date range logic.
	"""
	if not filters.get("company"):
		frappe.throw(_("Company is required"))

	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required"))

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))


def parse_cost_centers(filters):
	"""
	Parse the cost_center filter into a clean Python list.
	Handles:
	  - Empty / None              -> [] (no filter = show all accounts, no CC breakdown)
	  - 'ALL DEPARTMENT'          -> [] (special token = same as no filter)
	  - Single value string       -> ['CC Name']
	  - Comma-separated string    -> ['CC1', 'CC2', ...]
	  - Already a list            -> returned as-is (de-duped, stripped)
	"""
	raw = filters.get("cost_center") or ""

	if isinstance(raw, list):
		cc_list = [c.strip() for c in raw if c and c.strip()]
	else:
		raw = raw.strip()
		if not raw or raw.upper() == "ALL DEPARTMENT" or raw == "None":
			cc_list = []
		else:
			cc_list = [c.strip() for c in raw.split(",") if c.strip()]

	return cc_list


def get_columns():
	"""
	Define report columns structure.
	"""
	return [
		{
			"label": _("Account Name"),
			"fieldname": "account_name",
			"fieldtype": "HTML",
			"width": 420,
		},
		{
			"label": _("Opening (Dr)"),
			"fieldname": "opening_dr",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Opening (Cr)"),
			"fieldname": "opening_cr",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Debit"),
			"fieldname": "debit",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Credit"),
			"fieldname": "credit",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Closing (Dr)"),
			"fieldname": "closing_dr",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Closing (Cr)"),
			"fieldname": "closing_cr",
			"fieldtype": "Currency",
			"width": 120,
		},
	]


def get_data(filters):
	"""
	Build and execute the Trial Balance SQL query
	with optional multi-Cost Center breakdown.
	"""
	cc_list = parse_cost_centers(filters)
	has_cc_filter = bool(cc_list)

	if has_cc_filter:
		cc_in_clause = "(" + ", ".join([frappe.db.escape(cc) for cc in cc_list]) + ")"
	else:
		cc_in_clause = "('')"

	if has_cc_filter:
		opening_acc_cc_filter = f"AND cost_center IN {cc_in_clause}"
		period_acc_cc_filter  = f"AND cost_center IN {cc_in_clause}"
		cc_list_filter        = f"AND name IN {cc_in_clause}"
		no_cc_filter_cond     = "1 = 0"
		has_cc_filter_cond    = "1 = 1"
		has_cc_filter_cond2   = "1 = 1"
	else:
		opening_acc_cc_filter = ""
		period_acc_cc_filter  = ""
		cc_list_filter        = "AND 1 = 0"
		no_cc_filter_cond     = "1 = 1"
		has_cc_filter_cond    = "1 = 0"
		has_cc_filter_cond2   = "1 = 0"

	sql = """
WITH acc_cte AS (
	SELECT a.name, a.account_number, a.account_name, a.root_type
	FROM `tabAccount` a
	WHERE a.company = %(company)s
		AND a.is_group = 0
		AND IFNULL(a.disabled, 0) = 0
),

/* Opening balances — filtered to selected CCs when active */
opening_acc AS (
	SELECT account, SUM(debit - credit) AS opening_net
	FROM `tabGL Entry`
	WHERE company = %(company)s
		AND is_cancelled = 0
		AND posting_date < %(from_date)s
		{opening_acc_cc_filter}
	GROUP BY account
),

/* Period movements — filtered to selected CCs when active */
period_acc AS (
	SELECT account, SUM(debit) AS debit_amt, SUM(credit) AS credit_amt
	FROM `tabGL Entry`
	WHERE company = %(company)s
		AND is_cancelled = 0
		AND posting_date BETWEEN %(from_date)s AND %(to_date)s
		{period_acc_cc_filter}
	GROUP BY account
),

leaf_calc_acc AS (
	SELECT
		IFNULL(a.account_number, '') AS ac_no,
		CASE
			WHEN a.account_number IS NOT NULL AND a.account_number <> ''
			THEN CONCAT(a.account_number, ' - ', IFNULL(a.account_name, a.name))
			ELSE IFNULL(a.account_name, a.name)
		END AS account_label,
		a.root_type,
		a.name AS account_key,
		CASE
			WHEN a.account_number IS NOT NULL AND a.account_number <> ''
			THEN a.account_number
			ELSE CONCAT('ZZZZ_', a.name)
		END AS account_sort_key,
		CASE WHEN IFNULL(o.opening_net, 0) >= 0 THEN  IFNULL(o.opening_net, 0) ELSE 0 END AS opening_dr,
		CASE WHEN IFNULL(o.opening_net, 0)  < 0 THEN -IFNULL(o.opening_net, 0) ELSE 0 END AS opening_cr,
		IFNULL(p.debit_amt, 0)  AS debit,
		IFNULL(p.credit_amt, 0) AS credit,
		CASE
			WHEN IFNULL(o.opening_net, 0) + IFNULL(p.debit_amt, 0) - IFNULL(p.credit_amt, 0) >= 0
			THEN IFNULL(o.opening_net, 0) + IFNULL(p.debit_amt, 0) - IFNULL(p.credit_amt, 0)
			ELSE 0
		END AS closing_dr,
		CASE
			WHEN IFNULL(o.opening_net, 0) + IFNULL(p.debit_amt, 0) - IFNULL(p.credit_amt, 0) < 0
			THEN -(IFNULL(o.opening_net, 0) + IFNULL(p.debit_amt, 0) - IFNULL(p.credit_amt, 0))
			ELSE 0
		END AS closing_cr
	FROM acc_cte a
	LEFT JOIN opening_acc o ON o.account = a.name
	LEFT JOIN period_acc  p ON p.account  = a.name
),

filtered_acc AS (
	SELECT *
	FROM leaf_calc_acc
	WHERE
		%(row_mode)s = 'All'
		OR (%(row_mode)s = 'Income'  AND root_type = 'Income')
		OR (%(row_mode)s = 'Expense' AND root_type = 'Expense')
		OR (
			%(row_mode)s IN ('Income & Expense', 'Income and Expense', 'Income & Expenses')
			AND root_type IN ('Income', 'Expense')
		)
		OR (
			%(row_mode)s = 'Non Zero'
			AND (opening_dr <> 0 OR opening_cr <> 0 OR debit <> 0 OR credit <> 0)
		)
),

/* Selected cost centers only */
cc_list AS (
	SELECT
		name,
		IFNULL(cost_center_number, '') AS cost_center_number,
		cost_center_name
	FROM `tabCost Center`
	WHERE is_group = 0
		AND IFNULL(disabled, 0) = 0
		AND company = %(company)s
		AND name <> 'Name of Main Cost Center to Exclude'
		{cc_list_filter}
),

opening_cc AS (
	SELECT account, cost_center, SUM(debit - credit) AS opening_net
	FROM `tabGL Entry`
	WHERE company = %(company)s
		AND is_cancelled = 0
		AND posting_date < %(from_date)s
		AND cost_center IS NOT NULL
	GROUP BY account, cost_center
),

period_cc AS (
	SELECT account, cost_center, SUM(debit) AS debit_amt, SUM(credit) AS credit_amt
	FROM `tabGL Entry`
	WHERE company = %(company)s
		AND is_cancelled = 0
		AND posting_date BETWEEN %(from_date)s AND %(to_date)s
		AND cost_center IS NOT NULL
	GROUP BY account, cost_center
),

cc_data_calc AS (
	SELECT
		a.account_key,
		a.ac_no,
		a.account_sort_key,
		CASE
			WHEN cc.cost_center_number IS NOT NULL AND cc.cost_center_number <> ''
			THEN CONCAT('  -  ', cc.cost_center_number, ' - ', cc.cost_center_name)
			ELSE CONCAT('  -  ', cc.cost_center_name)
		END AS cc_label,
		cc.name AS cc_key,
		CASE WHEN IFNULL(o.opening_net, 0) >= 0 THEN  IFNULL(o.opening_net, 0) ELSE 0 END AS opening_dr,
		CASE WHEN IFNULL(o.opening_net, 0)  < 0 THEN -IFNULL(o.opening_net, 0) ELSE 0 END AS opening_cr,
		IFNULL(p.debit_amt, 0)  AS debit,
		IFNULL(p.credit_amt, 0) AS credit,
		CASE
			WHEN IFNULL(o.opening_net, 0) + IFNULL(p.debit_amt, 0) - IFNULL(p.credit_amt, 0) >= 0
			THEN IFNULL(o.opening_net, 0) + IFNULL(p.debit_amt, 0) - IFNULL(p.credit_amt, 0)
			ELSE 0
		END AS closing_dr,
		CASE
			WHEN IFNULL(o.opening_net, 0) + IFNULL(p.debit_amt, 0) - IFNULL(p.credit_amt, 0) < 0
			THEN -(IFNULL(o.opening_net, 0) + IFNULL(p.debit_amt, 0) - IFNULL(p.credit_amt, 0))
			ELSE 0
		END AS closing_cr
	FROM filtered_acc a
	CROSS JOIN cc_list cc
	LEFT JOIN opening_cc o ON o.account = a.account_key AND o.cost_center = cc.name
	LEFT JOIN period_cc  p ON p.account  = a.account_key AND p.cost_center = cc.name
),

filtered_cc AS (
	SELECT * FROM cc_data_calc
),

/*
 * cc_subtotals — aggregate filtered_cc at account level so the
 * Subtotal row shows the SUM of only the selected CCs, not the
 * full account balance from filtered_acc.
 */
cc_subtotals AS (
	SELECT
		account_key,
		ac_no,
		account_sort_key,
		SUM(opening_dr) AS opening_dr,
		SUM(opening_cr) AS opening_cr,
		SUM(debit)      AS debit,
		SUM(credit)     AS credit,
		SUM(closing_dr) AS closing_dr,
		SUM(closing_cr) AS closing_cr
	FROM filtered_cc
	GROUP BY account_key, ac_no, account_sort_key
),

final_tb AS (

	/* ============================================================
	   STRUCTURE 1 — Standard TB (no CC filter selected)
	   ============================================================ */
	SELECT
		account_label AS display_acct_name,
		opening_dr, opening_cr, debit, credit, closing_dr, closing_cr,
		account_sort_key AS sort_key_acct_no,
		0 AS sort_order, account_key, 'Account' AS row_type
	FROM filtered_acc
	WHERE {no_cc_filter_cond}

	UNION ALL
	SELECT '' AS display_acct_name, NULL, NULL, NULL, NULL, NULL, NULL,
		'' AS sort_key_acct_no, 2, '', 'Spacer'
	FROM (SELECT 1) x
	WHERE {no_cc_filter_cond}

	/* ============================================================
	   STRUCTURE 2 — Breakdown by selected Cost Centers
	   ============================================================ */
	UNION ALL
	/* Account header row (label only, no financials) */
	SELECT
		account_label AS display_acct_name,
		NULL, NULL, NULL, NULL, NULL, NULL,
		account_sort_key AS sort_key_acct_no,
		0 AS sort_order, account_key, 'Account' AS row_type
	FROM filtered_acc
	WHERE {has_cc_filter_cond}

	UNION ALL
	/* One data row per cost center per account */
	SELECT
		cc_label AS display_acct_name,
		opening_dr, opening_cr, debit, credit, closing_dr, closing_cr,
		account_sort_key AS sort_key_acct_no,
		1 AS sort_order,
		cc_key AS account_key,
		'Cost Center' AS row_type
	FROM filtered_cc
	WHERE {has_cc_filter_cond}

	UNION ALL
	/*
	 * Subtotal row — SUM of only the selected CCs for this account.
	 * Sourced from cc_subtotals (aggregated from filtered_cc),
	 * NOT from filtered_acc, to avoid showing the full account balance
	 * when only a subset of cost centers is selected.
	 */
	SELECT
		CASE
			WHEN s.ac_no IS NOT NULL AND s.ac_no <> ''
			THEN CONCAT('    ', s.ac_no, ' - SUBTOTAL')
			ELSE '    SUBTOTAL'
		END AS display_acct_name,
		s.opening_dr, s.opening_cr, s.debit, s.credit, s.closing_dr, s.closing_cr,
		s.account_sort_key AS sort_key_acct_no,
		2 AS sort_order,
		'' AS account_key,
		'Subtotal' AS row_type
	FROM cc_subtotals s
	WHERE {has_cc_filter_cond}

	UNION ALL
	/* Blank spacer after each account block */
	SELECT
		'' AS display_acct_name,
		NULL, NULL, NULL, NULL, NULL, NULL,
		account_sort_key AS sort_key_acct_no,
		3 AS sort_order,
		'' AS account_key,
		'Spacer' AS row_type
	FROM filtered_acc
	WHERE {has_cc_filter_cond}
		AND account_key IN (SELECT DISTINCT account_key FROM filtered_cc)

	UNION ALL
	/* Trailing spacer before TOTAL */
	SELECT '' AS display_acct_name, NULL, NULL, NULL, NULL, NULL, NULL,
		'' AS sort_key_acct_no, 4 AS sort_order, '', 'Spacer'
	FROM (SELECT 1) x
	WHERE {has_cc_filter_cond}

	/* ============================================================
	   Single TOTAL row — covers both structures
	   ============================================================ */
	UNION ALL
	SELECT 'TOTAL' AS display_acct_name,
		SUM(opening_dr), SUM(opening_cr), SUM(debit), SUM(credit), SUM(closing_dr), SUM(closing_cr),
		'' AS sort_key_acct_no,
		CASE WHEN {has_cc_filter_cond2} THEN 5 ELSE 3 END AS sort_order,
		'', 'Total'
	FROM filtered_acc
)

/* --- Final Output --- */
SELECT
	CASE
		WHEN row_type = 'Account'     AND IFNULL(account_key, '') <> ''
			THEN CONCAT('<a href="/app/account/', account_key, '">', display_acct_name, '</a>')
		WHEN row_type = 'Cost Center' AND IFNULL(account_key, '') <> ''
			THEN CONCAT('<a href="/app/cost_center/', account_key, '">', display_acct_name, '</a>')
		ELSE display_acct_name
	END AS account_name,
	opening_dr,
	opening_cr,
	debit,
	credit,
	closing_dr,
	closing_cr
FROM final_tb
ORDER BY
	(sort_order >= 4),
	(sort_key_acct_no = ''), 
	LPAD(sort_key_acct_no, 20, '0'),
	sort_order,
	display_acct_name;
	""".format(
		opening_acc_cc_filter=opening_acc_cc_filter,
		period_acc_cc_filter=period_acc_cc_filter,
		cc_list_filter=cc_list_filter,
		no_cc_filter_cond=no_cc_filter_cond,
		has_cc_filter_cond=has_cc_filter_cond,
		has_cc_filter_cond2=has_cc_filter_cond2,
	)

	result = frappe.db.sql(sql, filters, as_dict=True)
	return result


def get_monthly_data(filters):

	sql = """
		SELECT
			DATE_FORMAT(posting_date, '%%Y-%%m-01') AS month_start,
			account,
			SUM(debit - credit) AS amount
		FROM `tabGL Entry`
		WHERE company = %(company)s
			AND is_cancelled = 0
			AND posting_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY month_start, account
	"""

	raw_data = frappe.db.sql(sql, filters, as_dict=True)

	months = []
	current = getdate(filters.from_date)
	end = getdate(filters.to_date)

	while current <= end:
		months.append(current.strftime("%b_%Y").lower())
		current = add_months(current, 1)

	data_map = defaultdict(lambda: {"total": 0})

	for row in raw_data:
		month_key = getdate(row.month_start).strftime("%b_%Y").lower()
		account = row.account

		if "account_name" not in data_map[account]:
			data_map[account]["account_name"] = account

		data_map[account][month_key] = row.amount
		data_map[account]["total"] += row.amount

	return list(data_map.values())


def get_monthly_columns(filters):
	columns = [
		{
			"label": _("Account"),
			"fieldname": "account_name",
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		}
	]

	current = getdate(filters.from_date)
	end = getdate(filters.to_date)

	while current <= end:
		columns.append({
			"label": formatdate(current, "MMM yyyy"),
			"fieldname": current.strftime("%b_%Y").lower(),
			"fieldtype": "Currency",
			"width": 120,
		})
		current = add_months(current, 1)

	columns.append({
		"label": _("Total"),
		"fieldname": "total",
		"fieldtype": "Currency",
		"width": 120,
	})

	return columns