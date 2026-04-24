frappe.query_reports["BIR Statutory General Ledger"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 0
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 0
		},
		{
			"fieldname": "account",
			"label": __("Account"),
			"fieldtype": "Select",
			"options": "All Accounts\nCost of Sales Accounts",
			"reqd": 0,
			"default": "All Accounts"
		}
	]
};