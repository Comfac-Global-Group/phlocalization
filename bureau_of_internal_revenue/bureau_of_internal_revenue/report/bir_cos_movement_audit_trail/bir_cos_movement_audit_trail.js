// Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
// For license information, please see license.txt

frappe.query_reports["BIR COS Movement Audit Trail"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			mandatory: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			mandatory: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			mandatory: 1,
			default: frappe.datetime.get_today(),
		},
	],
};
