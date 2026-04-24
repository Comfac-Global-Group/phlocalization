import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.get("company"):
		frappe.throw(_("Company is required"))

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
		{"label": _("Transaction Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 110},
		{"label": _("CR/OR No"), "fieldname": "cr_or_no", "fieldtype": "Link", "options": "Payment Entry", "width": 140},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
		{"label": _("Customer Address"), "fieldname": "customer_address", "fieldtype": "Data", "width": 200},
		{"label": _("Customer TIN"), "fieldname": "customer_tin", "fieldtype": "Data", "width": 120},
		{"label": _("Reference Invoice No."), "fieldname": "reference_invoice_no", "fieldtype": "Data", "width": 140},
		{"label": _("Invoice No"), "fieldname": "invoice_no", "fieldtype": "Data", "width": 130},
		{"label": _("Account Name (DR)"), "fieldname": "account_name_dr", "fieldtype": "Data", "width": 200},
		{"label": _("Cash Amount"), "fieldname": "cash_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Check Amount"), "fieldname": "check_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Other Charges"), "fieldname": "other_charges", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("CWT"), "fieldname": "cwt", "fieldtype": "Currency", "options": "currency", "width": 100},
		{"label": _("Overpayment"), "fieldname": "overpayment", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Accounts Receivable"), "fieldname": "accounts_receivable", "fieldtype": "Currency", "options": "currency", "width": 130},
	]


def get_account_range(account_number, company):
	"""Get lft/rgt for a parent account to cover all child accounts"""
	result = frappe.db.get_value(
		"Account",
		{"account_number": account_number, "company": company},
		["lft", "rgt"],
		as_dict=True
	)
	return result or {"lft": 0, "rgt": 0}


def get_data(filters):
	company = filters.get("company")

	range_1600 = get_account_range("1600", company)

	query = """
		SELECT
			pe.posting_date AS transaction_date,
			pe.name AS cr_or_no,
			pe.party_name AS customer_name,
			IFNULL((SELECT a.address_line1 FROM `tabAddress` a INNER JOIN `tabDynamic Link` dl ON dl.parent = a.name WHERE dl.link_doctype = 'Customer' AND dl.link_name = pe.party LIMIT 1), '') AS customer_address,
			IFNULL((SELECT c.tax_id FROM `tabCustomer` c WHERE c.name = pe.party LIMIT 1), '') AS customer_tin,
			IFNULL((SELECT per.reference_name FROM `tabPayment Entry Reference` per WHERE per.parent = pe.name AND per.reference_doctype = 'Sales Invoice' LIMIT 1), '') AS reference_invoice_no,
			IFNULL((SELECT per.reference_name FROM `tabPayment Entry Reference` per WHERE per.parent = pe.name AND per.reference_doctype = 'Sales Invoice' LIMIT 1), '') AS invoice_no,
			pe.paid_to AS account_name_dr,
			CASE WHEN pe.mode_of_payment = 'Cash' THEN pe.paid_amount ELSE 0 END AS cash_amount,
			CASE WHEN pe.mode_of_payment != 'Cash' THEN pe.paid_amount ELSE 0 END AS check_amount,
			0 AS other_charges,
			IFNULL((SELECT SUM(ped.amount) FROM `tabPayment Entry Deduction` ped
				INNER JOIN `tabAccount` acc ON acc.name = ped.account
				WHERE ped.parent = pe.name AND acc.lft >= {lft_1600} AND acc.rgt <= {rgt_1600}), 0) AS cwt,
			IFNULL(pe.difference_amount, 0) AS overpayment,
			pe.total_allocated_amount AS accounts_receivable,
			pe.paid_from_account_currency AS currency

		FROM `tabPayment Entry` pe
		WHERE
			pe.docstatus = 1
			AND pe.company = %(company)s
			AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND pe.payment_type = 'Receive'
			AND pe.party_type = 'Customer'
		ORDER BY pe.posting_date ASC, pe.name ASC
	""".format(
		lft_1600=range_1600["lft"], rgt_1600=range_1600["rgt"],
	)

	raw_data = frappe.db.sql(query, filters, as_dict=True)

	processed_data = []
	grand_total_cash = 0
	grand_total_check = 0
	grand_total_other = 0
	grand_total_cwt = 0
	grand_total_overpayment = 0
	grand_total_ar = 0
	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	for row in raw_data:
		processed_data.append(row)
		grand_total_cash        += row.get("cash_amount") or 0
		grand_total_check       += row.get("check_amount") or 0
		grand_total_other       += row.get("other_charges") or 0
		grand_total_cwt         += row.get("cwt") or 0
		grand_total_overpayment += row.get("overpayment") or 0
		grand_total_ar          += row.get("accounts_receivable") or 0

	if processed_data:
		processed_data.append({
			"transaction_date": None, "cr_or_no": None, "customer_name": "",
			"customer_address": "", "customer_tin": "", "reference_invoice_no": "",
			"invoice_no": "", "account_name_dr": "", "cash_amount": None,
			"check_amount": None, "other_charges": None, "cwt": None,
			"overpayment": None, "accounts_receivable": None,
			"currency": company_currency
		})
		processed_data.append({
			"transaction_date": None, "cr_or_no": None, "customer_name": "",
			"customer_address": "", "customer_tin": "", "reference_invoice_no": "",
			"invoice_no": "", "account_name_dr": "<b>GRAND TOTAL</b>",
			"cash_amount": grand_total_cash, "check_amount": grand_total_check,
			"other_charges": grand_total_other, "cwt": grand_total_cwt,
			"overpayment": grand_total_overpayment, "accounts_receivable": grand_total_ar,
			"currency": company_currency
		})

	return processed_data