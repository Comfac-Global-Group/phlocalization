// Copyright (c) 2026, Ambibuzz Technologies LLP
// For license information, please see license.txt

frappe.query_reports["Custom Trial Balance"] = {
	filters: [
		{
			fieldname: "company",
			label: "Company",
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date",
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
			reqd: 1
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
					is_group: 0,
				});
			},
		},
		{
			fieldname: "row_mode",
			label: "Rows",
			fieldtype: "Select",
			options: [
				"All",
				"Non Zero",
				"Income & Expense",
			],
			default: "All"
		},
		{
			fieldname: "periodicity",
			label: "Periodicity",
			fieldtype: "Select",
			options: [
				"",
				"Monthly"
			],
			default: ""
		}
	]
};