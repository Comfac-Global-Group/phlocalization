// Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
// For license information, please see license.txt

frappe.query_reports["BIR Project 360"] = {
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
			reqd: 1,
			default: frappe.datetime.month_start()
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end()
		},
		{
			fieldname: "project_like",
			label: "Project ID",
			fieldtype: "Data",
			reqd: 1,
		}
	],
	formatter: function(value, row, column, data, default_formatter) {

		// Customer: show customer_name as display text, linked to Customer form
		if (column.fieldname === "customer") {
			if (data && data.customer) {
				const display = data.customer_name || data.customer;
				return `<a href="/app/customer/${encodeURIComponent(data.customer)}"
						style="white-space: nowrap; display: block;">${frappe.utils.escape_html(display)}</a>`;
			}
			return "";
		}

		// HTML remark columns: wrap in a scrollable fixed-height div to prevent row blowout
		if (["pi_remarks", "je_remarks"].includes(column.fieldname)) {
			if (!value) return "";
			return `<div style="max-height: 60px; overflow-y: auto; white-space: normal; line-height: 1.4;">
						${value}
					</div>`;
		}

		// SO Items: truncate with tooltip if too long
		if (column.fieldname === "so_items") {
			if (!value) return "";
			const MAX = 80;
			const str = String(value);
			if (str.length > MAX) {
				const truncated = frappe.utils.escape_html(str.slice(0, MAX)) + "…";
				const full = frappe.utils.escape_html(str);
				return `<span title="${full}" style="cursor: default;">${truncated}</span>`;
			}
			return frappe.utils.escape_html(str);
		}

		// Currency columns: right-align explicitly
		if (column.fieldtype === "Currency") {
			const formatted = default_formatter(value, row, column, data);
			return `<div style="text-align: right;">${formatted}</div>`;
		}

		return default_formatter(value, row, column, data);
	}
};
