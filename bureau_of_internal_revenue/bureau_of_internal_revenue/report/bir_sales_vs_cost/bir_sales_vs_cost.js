// Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
// For license information, please see license.txt

frappe.query_reports["BIR Sales vs Cost"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "project",
			"label": __("Project Like"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname": "invoice_filter",
			"label": __("Invoice Status"),
			"fieldtype": "Select",
			"options": "\nShow even without Invoices\nWith Invoices"
		},
		{
			"fieldname": "hide_zero_projects",
			"label": __("Hide Zero-Value Projects"),
			"fieldtype": "Check"
		}
	]
};
