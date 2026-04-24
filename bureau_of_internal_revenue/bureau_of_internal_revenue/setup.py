import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Account": [
		{
			"fieldname": "schedule",
			"fieldtype": "Select",
			"label": "Schedule",
			"insert_after": "parent_account",
			"options": "\nSCHED 1\nSCHED 2\nSCHED 3\nSCHED 4\nSCHED 5\nSCHED 6\nSCHED 7\nSCHED 8\nSCHED 9\nSCHED 10\nSCHED 11\nSCHED 12\nSCHED 13\nSCHED 14\nSCHED 15\nSCHED 16\nSCHED 17\nSCHED 18\nSCHED 19\nSCHED 20\nSCHED 21\nSCHED 22\nSCHED 23",
			"translatable": 0,
		},
	],
}


def delete_custom_fields(custom_fields):
	for doctype, fields in custom_fields.items():
		for field in fields:
			fieldname = field.get("fieldname")
			custom_field_name = f"{doctype}-{fieldname}"
			if frappe.db.exists("Custom Field", custom_field_name):
				frappe.delete_doc("Custom Field", custom_field_name, force=True)
		frappe.clear_cache(doctype=doctype)


def after_install():
	create_custom_fields(CUSTOM_FIELDS, update=True)


def before_uninstall():
	delete_custom_fields(CUSTOM_FIELDS)