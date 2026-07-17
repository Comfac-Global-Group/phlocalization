// Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('BIR CAS Settings', {
	refresh: function(frm) {
		fetch_app_version(frm);
	},

	address: function(frm) {
		if (!frm.doc.address) {
			frm.set_value('registered_address', '');
			return;
		}

		// Fetch formatted address display from Frappe's Address DocType
		frappe.call({
			method: 'frappe.contacts.doctype.address.address.get_address_display',
			args: { address_dict: frm.doc.address },
			callback: function(r) {
				if (r.message) {
					// Strip <br> tags and clean up extra commas
					let clean = r.message
						.replace(/<br\s*\/?>/gi, ', ')
						.replace(/,\s*,/g, ',')
						.replace(/,\s*$/g, '')
						.trim();
					frm.set_value('registered_address', clean);
				}
			}
		});
	}
});

function fetch_app_version(frm) {
	// Fetch all installed app versions from Frappe
	frappe.call({
		method: 'frappe.utils.change_log.get_versions',
		callback: function(r) {
			if (r.message) {
				// Match by app title or app name depending on Frappe version
				let app = r.message['Bureau of Internal Revenue']
					   || r.message['bureau_of_internal_revenue'];

				if (app) {
					frm.set_value('software_name', app.title);
					frm.set_value('version_number', app.version);
				}
			}
		}
	});
}