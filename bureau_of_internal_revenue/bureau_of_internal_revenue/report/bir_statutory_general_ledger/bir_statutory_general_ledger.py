from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.setdefault("account", "All Accounts")

	if not filters.get("from_date"):
		filters.from_date = frappe.utils.get_first_day(frappe.utils.nowdate())
	if not filters.get("to_date"):
		filters.to_date = frappe.utils.nowdate()

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Account"),             "fieldname": "account",         "fieldtype": "Link",     "options": "Account", "width": 250},
		{"label": _("Reference"),           "fieldname": "reference",       "fieldtype": "Data",     "width": 150},
		{"label": _("Transaction Date"),    "fieldname": "transaction_date","fieldtype": "Data",     "width": 220},
		{"label": _("Payee/Received From"), "fieldname": "payee",           "fieldtype": "Data",     "width": 200},
		{"label": _("Particulars"),         "fieldname": "particulars",     "fieldtype": "Data",     "width": 200},
		{"label": _("Beginning Balance"),   "fieldname": "beg_balance",     "fieldtype": "Currency", "width": 150},
		{"label": _("Debit"),               "fieldname": "debit",           "fieldtype": "Currency", "width": 130},
		{"label": _("Credit"),              "fieldname": "credit",          "fieldtype": "Currency", "width": 130},
		{"label": _("Ending Balance"),      "fieldname": "ending_balance",  "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	sql = """
	WITH
	/* ── Accounts that have transactions within the date range ── */
	accounts_with_txn AS (
		SELECT DISTINCT g.account
		FROM `tabGL Entry` g
		WHERE g.docstatus = 1
		  AND IFNULL(g.is_cancelled, 0) = 0
		  AND g.company = %(company)s
		  AND g.posting_date BETWEEN %(from_date)s AND %(to_date)s
	),

	/* ── Accounts that have a non-zero balance before the date range ── */
	accounts_with_bb AS (
		SELECT gle.account
		FROM `tabGL Entry` gle
		WHERE gle.docstatus = 1
		  AND IFNULL(gle.is_cancelled, 0) = 0
		  AND gle.company = %(company)s
		  AND gle.posting_date < %(from_date)s
		GROUP BY gle.account
		HAVING ROUND(SUM(gle.debit - gle.credit), 2) <> 0
	),

	/* ── Union of both sets, filtered by account type selection ── */
	accounts_in_scope AS (
		SELECT air.account
		FROM (
			SELECT account FROM accounts_with_txn
			UNION
			SELECT account FROM accounts_with_bb
		) air
		JOIN `tabAccount` a
		  ON a.name = air.account
		 AND a.company = %(company)s
		WHERE
			%(account)s = 'All Accounts'
			OR (
				%(account)s = 'Cost of Sales Accounts'
				AND a.account_type = 'Cost of Goods Sold'
			)
	),

	/* ── Net balance per account BEFORE from_date ── */
	bb_per_account AS (
		SELECT
			gle.account,
			ROUND(SUM(gle.debit - gle.credit), 2) AS net_bb
		FROM `tabGL Entry` gle
		WHERE gle.docstatus = 1
		  AND IFNULL(gle.is_cancelled, 0) = 0
		  AND gle.company = %(company)s
		  AND gle.posting_date < %(from_date)s
		  AND gle.account IN (SELECT account FROM accounts_in_scope)
		GROUP BY gle.account
	),

	/* ── All in-period GL entries (raw) ── */
	period_entries AS (
		SELECT
			g.account,
			g.posting_date,
			g.voucher_type,
			g.voucher_no,
			g.party                                         AS party,
			g.debit,
			g.credit,
			DATE_FORMAT(g.posting_date, '%%Y-%%m')          AS ym,
			g.name                                          AS gle_name
		FROM `tabGL Entry` g
		WHERE g.docstatus = 1
		  AND IFNULL(g.is_cancelled, 0) = 0
		  AND g.company = %(company)s
		  AND g.posting_date BETWEEN %(from_date)s AND %(to_date)s
		  AND g.account IN (SELECT account FROM accounts_in_scope)
	),

	/* ── One summarised row per account per month ── */
	monthly_summary AS (
		SELECT
			account,
			ym,
			CONCAT(
				DATE_FORMAT(STR_TO_DATE(CONCAT(ym, '-01'), '%%Y-%%m-%%d'), '%%M 1 - '),
				DAY(LAST_DAY(STR_TO_DATE(CONCAT(ym, '-01'), '%%Y-%%m-%%d'))),
				' Transactions'
			)                                               AS txn_date_label,
			CONCAT(
				UPPER(DATE_FORMAT(LAST_DAY(STR_TO_DATE(CONCAT(ym, '-01'), '%%Y-%%m-%%d')), '%%M')),
				' ',
				DAY(LAST_DAY(STR_TO_DATE(CONCAT(ym, '-01'), '%%Y-%%m-%%d'))),
				' TRANSACTION'
			)                                               AS particulars,
			MIN(voucher_type)                               AS voucher_type,
			ROUND(SUM(debit),  2)                           AS total_debit,
			ROUND(SUM(credit), 2)                           AS total_credit
		FROM period_entries
		GROUP BY account, ym
	),

	/* ── Cumulative ending balance per account per month ── */
	month_ending AS (
		SELECT
			ms.account,
			ms.ym,
			ms.particulars,
			ms.txn_date_label,
			ms.voucher_type,
			ms.total_debit,
			ms.total_credit,
			ROUND(
				COALESCE(bb.net_bb, 0) +
				SUM(ms.total_debit - ms.total_credit) OVER (
					PARTITION BY ms.account
					ORDER BY ms.ym
				),
			2) AS ending_balance
		FROM monthly_summary ms
		LEFT JOIN bb_per_account bb ON bb.account = ms.account
	),

	/* ── Carry previous month ending as this month's beginning ── */
	month_with_bb AS (
		SELECT
			me.*,
			LAG(me.ending_balance) OVER (
				PARTITION BY me.account ORDER BY me.ym
			) AS row_beg_balance
		FROM month_ending me
	),

	/* ── Rank rows so account name shows only on first month ── */
	month_ranked AS (
		SELECT
			mwb.*,
			ROW_NUMBER() OVER (
				PARTITION BY mwb.account ORDER BY mwb.ym
			) AS rn
		FROM month_with_bb mwb
	)

	SELECT
		account         AS account,
		reference       AS reference,
		txn_date        AS transaction_date,
		payee           AS payee,
		particulars     AS particulars,
		beg_balance     AS beg_balance,
		debit           AS debit,
		credit          AS credit,
		ending_balance  AS ending_balance
	FROM (

		/* ======== MONTHLY SUMMARY ROWS ======== */
		SELECT
			CASE WHEN rn = 1 THEN account ELSE NULL END     AS account,
			voucher_type                                     AS reference,
			txn_date_label                                   AS txn_date,
			NULL                                             AS payee,
			particulars                                      AS particulars,
			row_beg_balance                                  AS beg_balance,
			total_debit                                      AS debit,
			total_credit                                     AS credit,
			ending_balance                                   AS ending_balance,
			CONCAT(account, '-', ym, '-2')                   AS sort_order
		FROM month_ranked

		UNION ALL

		/* ======== BLANK SEPARATOR ROW BEFORE EACH ACCOUNT ======== */
		SELECT
			NULL    AS account,
			NULL    AS reference,
			NULL    AS txn_date,
			NULL    AS payee,
			''      AS particulars,
			NULL    AS beg_balance,
			NULL    AS debit,
			NULL    AS credit,
			NULL    AS ending_balance,
			CONCAT(account, '-0000-1') AS sort_order
		FROM (
			SELECT DISTINCT account FROM month_ranked
			UNION
			SELECT account FROM bb_per_account
			WHERE account NOT IN (SELECT DISTINCT account FROM period_entries)
		) all_accounts

		UNION ALL

		/* ======== BEGINNING BALANCE ROW FOR ALL PERIOD ACCOUNTS ======== */
		SELECT
			NULL                                             AS account,
			NULL                                             AS reference,
			NULL                                             AS txn_date,
			NULL                                             AS payee,
			CONCAT(
				UPPER(DATE_FORMAT(%(from_date)s, '%%M')),
				' 1 BEGINNING BALANCE'
			)                                                AS particulars,
			COALESCE(bb.net_bb, 0)                           AS beg_balance,
			NULL                                             AS debit,
			NULL                                             AS credit,
			COALESCE(bb.net_bb, 0)                           AS ending_balance,
			CONCAT(mr.account, '-0000-2')                    AS sort_order
		FROM (SELECT DISTINCT account FROM month_ranked) mr
		LEFT JOIN bb_per_account bb ON bb.account = mr.account

		UNION ALL

		/* ======== BB-ONLY ACCOUNTS (no period transactions) ======== */
		SELECT
			bb.account                                       AS account,
			NULL                                             AS reference,
			NULL                                             AS txn_date,
			NULL                                             AS payee,
			CONCAT(
				UPPER(DATE_FORMAT(%(from_date)s, '%%M')),
				' 1 BEGINNING BALANCE'
			)                                                AS particulars,
			bb.net_bb                                        AS beg_balance,
			NULL                                             AS debit,
			NULL                                             AS credit,
			bb.net_bb                                        AS ending_balance,
			CONCAT(bb.account, '-0000-2')                    AS sort_order
		FROM bb_per_account bb
		WHERE bb.account NOT IN (SELECT DISTINCT account FROM period_entries)

	) combined
	ORDER BY sort_order
	"""
	return frappe.db.sql(sql, filters, as_dict=True)