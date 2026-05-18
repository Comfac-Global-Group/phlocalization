// Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
// For license information, please see license.txt

frappe.query_reports["BIR VAT Output Tax Register"] = {
	"filters": [
		{
			fieldname: "company",
			label: "Company",
			fieldtype: "Link",
			options: "Company",
			reqd: 1
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
			fieldname: "vat_account",
			label: "Account",
			fieldtype: "Link",
			options: "Account",
			reqd: 1,

			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");

				return {
					filters: {
						company: company,
						is_group: 0,
						parent_account: ["like", "2200 - VAT Output Tax%"]
					}
				};
			}
		}
	]
};
