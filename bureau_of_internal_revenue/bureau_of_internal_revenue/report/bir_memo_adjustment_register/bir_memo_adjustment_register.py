# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Transaction Date",
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": "Doc No",
            "fieldname": "doc_no",
            "fieldtype": "Link",
            "options": "Journal Entry",
            "width": 150
        },
        {
            "label": "Doc Type",
            "fieldname": "doc_type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Account",
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 200
        },
        {
            "label": "Dept Code",
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 150
        },
        {
            "label": "Description",
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": "Debit",
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": "Credit",
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": "Invoice #",
            "fieldname": "invoice_no",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": "Reference Invoice",
            "fieldname": "reference_html",
            "fieldtype": "HTML",
            "width": 180
        },
        {
            "label": "Customer/Supplier",
            "fieldname": "party",
            "fieldtype": "Data",
            "width": 200
        }
    ]


def get_data(filters):
    return frappe.db.sql(
        """
        SELECT
            transaction_date,
            doc_no,
            doc_type,
            account,
            cost_center,
            description,
            debit,
            credit,
            invoice_no,
            reference_html,
            party
        FROM (
            /* ======================= DETAIL ROWS ======================= */
            SELECT
                je.posting_date                                       AS transaction_date,
                je.name                                               AS doc_no,
                je.voucher_type                                       AS doc_type,
                jea.account                                           AS account,
                jea.cost_center                                       AS cost_center,
                jea.user_remark                                       AS description,
                jea.debit                                             AS debit,
                jea.credit                                            AS credit,
                je.user_remark                                        AS invoice_no,
                CASE
                    WHEN jea.reference_name IS NOT NULL AND jea.reference_name != '' THEN
                        CONCAT(
                            '<a href="/app/',
                            LOWER(REPLACE(jea.reference_type, ' ', '-')),
                            '/',
                            jea.reference_name,
                            '" target="_blank">',
                            jea.reference_name,
                            '</a>'
                        )
                    ELSE ''
                END                                                   AS reference_html,
                COALESCE(c.customer_name, jea.party)                  AS party,
                CONCAT(je.posting_date, '-', je.name, '-1-', LPAD(jea.idx, 5, '0')) AS sort_order
            FROM `tabJournal Entry` je
            JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
            LEFT JOIN `tabCustomer` c ON c.name = jea.party AND jea.party_type = 'Customer'
            WHERE
                je.docstatus = 1
                AND je.company = %(company)s
                AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND je.voucher_type IN ('Debit Note', 'Credit Note')

            UNION ALL

            /* ======================= SUBTOTAL ROWS ======================= */
            SELECT
                NULL                                                  AS transaction_date,
                ''                                                    AS doc_no,
                ''                                                    AS doc_type,
                ''                                                    AS account,
                ''                                                    AS cost_center,
                '<b>SUBTOTAL</b>'                                     AS description,
                SUM(jea.debit)                                        AS debit,
                SUM(jea.credit)                                       AS credit,
                ''                                                    AS invoice_no,
                ''                                                    AS reference_html,
                ''                                                    AS party,
                CONCAT(je.posting_date, '-', je.name, '-2-00000')     AS sort_order
            FROM `tabJournal Entry` je
            JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
            WHERE
                je.docstatus = 1
                AND je.company = %(company)s
                AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND je.voucher_type IN ('Debit Note', 'Credit Note')
            GROUP BY je.posting_date, je.name, je.voucher_type

            UNION ALL

            /* ======================= BLANK ROWS ======================= */
            SELECT
                NULL                                                  AS transaction_date,
                ''                                                    AS doc_no,
                ''                                                    AS doc_type,
                ''                                                    AS account,
                ''                                                    AS cost_center,
                ''                                                    AS description,
                NULL                                                  AS debit,
                NULL                                                  AS credit,
                ''                                                    AS invoice_no,
                ''                                                    AS reference_html,
                ''                                                    AS party,
                CONCAT(je.posting_date, '-', je.name, '-3-00000')     AS sort_order
            FROM `tabJournal Entry` je
            WHERE
                je.docstatus = 1
                AND je.company = %(company)s
                AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND je.voucher_type IN ('Debit Note', 'Credit Note')
        ) AS combined
        ORDER BY combined.sort_order
        """,
        filters,
        as_dict=1
    )