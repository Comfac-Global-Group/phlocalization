// Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
// For license information, please see license.txt

frappe.query_reports["BIR Job Order Masterfile"] = {
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
		 "reqd": 0,
		 "default": frappe.datetime.get_today()
	 },
	 {
		 "fieldname": "to_date",
		 "label": __("To Date"),
		 "fieldtype": "Date",
		 "reqd": 0,
		 "default": frappe.datetime.get_today()
	 }
 ]
};