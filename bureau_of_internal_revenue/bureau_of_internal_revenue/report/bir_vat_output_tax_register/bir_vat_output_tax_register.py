import frappe


def execute(filters=None):
	"""
	Entry point for VAT Sales Report with dynamic VAT account filtering.
	"""

	filters = filters or {}

	if not filters.get("company"):
		frappe.throw("Company filter is required")

	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw("From Date and To Date are required")

	filters["vat_account"] = filters.get("vat_account") or "2500 - VAT Output Taxes Payable"

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": "Sales Invoice ID", "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
		{"label": "Sales Orders ID (via Project)", "fieldname": "sales_orders", "fieldtype": "Data", "width": 240},
		{"label": "Projects/JO (List)", "fieldname": "projects", "fieldtype": "Link", "options": "Project", "width": 220},
		{"label": "Customer Tax ID", "fieldname": "tax_id", "fieldtype": "Data", "width": 150},
		{"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},

		{"label": "Invoice Total", "fieldname": "total", "fieldtype": "Currency", "options": "currency", "width": 150},
		{"label": "Grand Total", "fieldname": "grand_total", "fieldtype": "Currency", "options": "currency", "width": 150},
		{"label": "Amount (VAT Account)", "fieldname": "vat_amount", "fieldtype": "Currency", "options": "currency", "width": 180},

		{"label": "Payment ID", "fieldname": "payment_id", "fieldtype": "Link", "options": "Payment Entry", "width": 220},
		{"label": "VAT Account", "fieldname": "account_head", "fieldtype": "Data", "width": 260},
		{"label": "Debit To", "fieldname": "debit_to", "fieldtype": "Link", "options": "Account", "width": 200},
		{"label": "Against Income Account", "fieldname": "income_accounts", "fieldtype": "Data", "width": 240},
		{"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 400},
	]


def get_data(filters):

	query = """
	SELECT
		si.posting_date,
		si.currency,
		si.name,

		(
			SELECT GROUP_CONCAT(DISTINCT so_x.name SEPARATOR ', ')
			FROM `tabSales Invoice Item` sii_px
			JOIN `tabProject` proj ON proj.name = sii_px.project
			JOIN `tabSales Order` so_x ON so_x.name = proj.sales_order
			WHERE sii_px.parent = si.name
		) AS sales_orders,

		(
			SELECT GROUP_CONCAT(DISTINCT sii_pl.project SEPARATOR ', ')
			FROM `tabSales Invoice Item` sii_pl
			WHERE sii_pl.parent = si.name
		) AS projects,

		cust.tax_id,
		si.customer_name,
		si.total,
		si.grand_total,

		COALESCE(agg_taxes.total_tax_amount, 0) AS vat_amount,

		(
			SELECT GROUP_CONCAT(DISTINCT per.parent SEPARATOR ', ')
			FROM `tabPayment Entry Reference` per
			WHERE per.reference_doctype = 'Sales Invoice'
			AND per.reference_name = si.name
		) AS payment_id,

		agg_taxes.account_heads AS account_head,

		si.debit_to,

		(
			SELECT GROUP_CONCAT(DISTINCT sii_ia.income_account SEPARATOR ', ')
			FROM `tabSales Invoice Item` sii_ia
			WHERE sii_ia.parent = si.name
		) AS income_accounts,

		(
			SELECT GROUP_CONCAT(
				IFNULL(NULLIF(sii_d.description, ''), IFNULL(sii_d.item_name, sii_d.item_code))
				SEPARATOR '; '
			)
			FROM `tabSales Invoice Item` sii_d
			WHERE sii_d.parent = si.name
		) AS description

	FROM `tabSales Invoice` si
	LEFT JOIN `tabCustomer` cust ON cust.name = si.customer

	LEFT JOIN (
		SELECT
			stc.parent,
			SUM(stc.tax_amount_after_discount_amount) AS total_tax_amount,
			GROUP_CONCAT(DISTINCT stc.account_head SEPARATOR ', ') AS account_heads
		FROM `tabSales Taxes and Charges` stc
		LEFT JOIN `tabAccount` acc ON acc.name = stc.account_head
		LEFT JOIN `tabAccount` vat_root
			ON vat_root.name = %(vat_account)s
		WHERE acc.lft >= vat_root.lft
		AND acc.rgt <= vat_root.rgt
		GROUP BY stc.parent
	) agg_taxes ON agg_taxes.parent = si.name

	WHERE
		si.docstatus = 1
		AND si.company = %(company)s
		AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
		AND agg_taxes.parent IS NOT NULL

	ORDER BY si.posting_date, si.name
	"""

	return frappe.db.sql(query, filters, as_dict=True)