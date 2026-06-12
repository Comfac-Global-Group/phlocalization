# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "DOC TYPE", "fieldname": "DOC TYPE", "fieldtype": "Data", "width": 130},
		{"label": "DOC NO", "fieldname": "DOC NO", "fieldtype": "Data", "width": 130},
		{"label": "REFERENCE", "fieldname": "REFERENCE", "fieldtype": "Data", "width": 160},
		{"label": "TRAN DATE", "fieldname": "TRAN DATE", "fieldtype": "Date", "width": 100},
		{"label": "PAYEE/RECEIVED FROM", "fieldname": "PAYEE/RECEIVED FROM", "fieldtype": "Data", "width": 180},
		{"label": "PARTICULARS", "fieldname": "PARTICULARS", "fieldtype": "Data", "width": 260},
		{"label": "DEBIT", "fieldname": "DEBIT", "fieldtype": "Data", "width": 120, "align": "right"},
		{"label": "CREDIT", "fieldname": "CREDIT", "fieldtype": "Data", "width": 120, "align": "right"},
		{"label": "NET CHANGE", "fieldname": "NET CHANGE", "fieldtype": "Data", "width": 120, "align": "right"},
		{"label": "JO NUMBER", "fieldname": "JO NUMBER", "fieldtype": "Data", "width": 130},
	]


def get_data(filters):
	query = """
		WITH stock_entry_data AS (
			SELECT
				se.name AS erp_doc_no,
				CASE
					WHEN se.stock_entry_type = 'Material Transfer' THEN
						CASE
							WHEN COALESCE(sed.s_warehouse, '') LIKE 'Stores%%' THEN 'MR'
							ELSE 'MRS'
						END
					ELSE se.stock_entry_type
				END AS doc_type,
				se.posting_date AS tran_date,
				(SELECT p.customer FROM `tabProject` p WHERE p.name = se.project LIMIT 1) AS reference,
				CONCAT('Item#', sed.item_code, ': ', COALESCE(sed.description, ''), ' - ', sed.qty, ' PC') AS particulars,
				'INVENTORY ENTRY TO GL' AS payee_received_from,
				CASE
					WHEN se.stock_entry_type = 'Material Transfer'
					 AND COALESCE(sed.s_warehouse, '') LIKE 'Stores%%' THEN sed.amount
					WHEN se.stock_entry_type = 'Material Transfer'
					 AND COALESCE(sed.s_warehouse, '') NOT LIKE 'Stores%%' THEN 0
					ELSE sed.amount
				END AS debit,
				CASE
					WHEN se.stock_entry_type = 'Material Transfer'
					 AND COALESCE(sed.s_warehouse, '') LIKE 'Stores%%' THEN 0
					WHEN se.stock_entry_type = 'Material Transfer'
					 AND COALESCE(sed.s_warehouse, '') NOT LIKE 'Stores%%' THEN sed.amount
					ELSE 0
				END AS credit,
				CASE
					WHEN se.stock_entry_type = 'Material Transfer'
					 AND COALESCE(sed.s_warehouse, '') LIKE 'Stores%%' THEN sed.amount
					WHEN se.stock_entry_type = 'Material Transfer'
					 AND COALESCE(sed.s_warehouse, '') NOT LIKE 'Stores%%' THEN -sed.amount
					ELSE sed.amount
				END AS net_change,
				CASE
					WHEN se.stock_entry_type = 'Material Transfer'
					 AND COALESCE(sed.s_warehouse, '') LIKE 'Stores%%' THEN 'MR'
					WHEN se.stock_entry_type = 'Material Transfer'
					 AND COALESCE(sed.s_warehouse, '') NOT LIKE 'Stores%%' THEN 'MRS'
					ELSE 'OTHER'
				END AS stock_subtype,
				sed.project AS jo_number,
				se.name AS doc_no_field
			FROM `tabStock Entry` se
			JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
			WHERE se.docstatus = 1
			  AND se.company = %(company)s
			  AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
			  AND sed.project IS NOT NULL
		),

		stock_reconciliation_data AS (
			SELECT
				sr.name AS erp_doc_no,
				'Stock Reconciliation' AS doc_type,
				gle.posting_date AS tran_date,
				NULL AS reference,
				CASE
					WHEN (SELECT COUNT(*) FROM `tabStock Reconciliation Item` sri
						  WHERE sri.parent = gle.voucher_no) > 0 THEN
						CONCAT(
							'Item#',
							(SELECT sri.item_code FROM `tabStock Reconciliation Item` sri
							 WHERE sri.parent = gle.voucher_no LIMIT 1),
							': ',
							COALESCE(
								(SELECT it.item_name FROM `tabStock Reconciliation Item` sri
								 JOIN `tabItem` it ON it.name = sri.item_code
								 WHERE sri.parent = gle.voucher_no LIMIT 1),
								''),
							' - ',
							(SELECT sri.qty FROM `tabStock Reconciliation Item` sri
							 WHERE sri.parent = gle.voucher_no LIMIT 1),
							' PC')
					ELSE COALESCE(gle.remarks, 'Stock Reconciliation Adjustment')
				END AS particulars,
				'INVENTORY ENTRY TO GL' AS payee_received_from,
				gle.debit AS debit,
				gle.credit AS credit,
				(gle.debit - gle.credit) AS net_change,
				'RECON' AS stock_subtype,
				gle.project AS jo_number,
				sr.name AS doc_no_field
			FROM `tabGL Entry` gle
			JOIN `tabStock Reconciliation` sr ON sr.name = gle.voucher_no
			WHERE gle.company = %(company)s
			  AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			  AND gle.voucher_type = 'Stock Reconciliation'
			  AND gle.account LIKE '1521%%'
			  AND gle.project IS NOT NULL
		),

		journal_entry_data AS (
			SELECT
				je.name AS erp_doc_no,
				je.voucher_type AS doc_type,
				je.posting_date AS tran_date,
				je.user_remark AS reference,
				jea.user_remark AS particulars,
				CASE
					WHEN je.user_remark LIKE '%%SA#%%'      THEN je.pay_to_recd_from
					WHEN je.user_remark LIKE '%%COS%%'      THEN 'CLOSED TO COS'
					WHEN je.user_remark LIKE '%%VP-ALPHA%%' THEN 'ADJUSTMENT TO COS'
					WHEN je.user_remark LIKE '%%INV%%'      THEN 'CLOSED TO COS'
					WHEN je.user_remark LIKE '%%VP#%%'      THEN jea.party
					ELSE jea.party
				END AS payee_received_from,
				jea.debit  AS debit,
				jea.credit AS credit,
				jea.party  AS party,
				(jea.debit - jea.credit) AS net_change,
				jea.project AS jo_number,
				REPLACE(REPLACE(REPLACE(je.name,'ACC-JV-R-',''),'ACC-JV-A-',''),'ACC-JVP-','') AS doc_no_field
			FROM `tabJournal Entry` je
			JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			WHERE je.docstatus = 1
			  AND je.company = %(company)s
			  AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
			  AND jea.project IS NOT NULL
		),

		purchase_invoice_data AS (
			SELECT
				pi.name AS erp_doc_no,
				'Purchase Invoice' AS doc_type,
				pi.posting_date AS tran_date,
				CONCAT(COALESCE(pii.item_code,''),' ',COALESCE(pii.item_name,'')) AS reference,
				COALESCE(pii.description, pii.item_name, '') AS particulars,
				pi.supplier AS payee_received_from,
				pii.base_amount AS debit,
				0 AS credit,
				pi.supplier AS party,
				pii.base_amount AS net_change,
				pii.project AS jo_number,
				pi.remarks AS doc_no_field
			FROM `tabPurchase Invoice Item` pii
			JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
			WHERE pi.docstatus = 1
			  AND pi.company = %(company)s
			  AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
			  AND pii.expense_account LIKE '1521%%'
			  AND pii.project IS NOT NULL
		),

		all_jos AS (
			SELECT jo_number FROM stock_entry_data           WHERE jo_number IS NOT NULL
			UNION
			SELECT jo_number FROM stock_reconciliation_data  WHERE jo_number IS NOT NULL
			UNION
			SELECT jo_number FROM journal_entry_data         WHERE jo_number IS NOT NULL
			UNION
			SELECT jo_number FROM purchase_invoice_data      WHERE jo_number IS NOT NULL
		),

		mr_only_by_jo AS (
			SELECT jo_number, SUM(net_change) AS net_change
			FROM stock_entry_data WHERE stock_subtype IN ('MR','MRS')
			GROUP BY jo_number
		),
		recon_by_jo AS (
			SELECT jo_number, SUM(debit) AS debit, SUM(credit) AS credit, SUM(net_change) AS net_change
			FROM stock_reconciliation_data GROUP BY jo_number
		),
		stock_by_jo AS (
			SELECT jo_number, SUM(debit) AS debit, SUM(credit) AS credit, SUM(net_change) AS net_change
			FROM (
				SELECT jo_number, debit, credit, net_change FROM stock_entry_data
				UNION ALL
				SELECT jo_number, debit, credit, net_change FROM stock_reconciliation_data
			) x GROUP BY jo_number
		),
		jepi_by_jo AS (
			SELECT jo_number, SUM(debit) AS debit, SUM(credit) AS credit, SUM(net_change) AS net_change
			FROM (
				SELECT jo_number, debit, credit, net_change FROM journal_entry_data
				UNION ALL
				SELECT jo_number, debit, credit, net_change FROM purchase_invoice_data
			) x GROUP BY jo_number
		),

		mr_mrs_total AS (
			SELECT SUM(debit) AS debit, SUM(credit) AS credit, SUM(net_change) AS net_change
			FROM stock_entry_data WHERE stock_subtype IN ('MR','MRS')
		),
		stock_recon_total AS (
			SELECT SUM(debit) AS debit, SUM(credit) AS credit, SUM(net_change) AS net_change
			FROM stock_reconciliation_data
		),
		stock_gl_total AS (
			SELECT SUM(debit) AS debit, SUM(credit) AS credit, SUM(net_change) AS net_change
			FROM (
				SELECT debit, credit, net_change FROM stock_entry_data
				UNION ALL
				SELECT debit, credit, net_change FROM stock_reconciliation_data
			) x
		),
		jepi_total AS (
			SELECT SUM(debit) AS debit, SUM(credit) AS credit, SUM(net_change) AS net_change
			FROM (
				SELECT debit, credit, net_change FROM journal_entry_data
				UNION ALL
				SELECT debit, credit, net_change FROM purchase_invoice_data
			) x
		),

		all_rows AS (
			-- ============ PER-JO BLOCK ============

			-- 1. Stock detail rows
			SELECT
				1 AS block_order, j.jo_number, 1 AS section_order,
				s.tran_date, s.doc_no_field, s.doc_type, s.reference,
				s.payee_received_from, s.particulars,
				s.debit, s.credit, s.net_change
			FROM all_jos j
			JOIN (
				SELECT jo_number, tran_date, doc_no_field, doc_type, reference,
					   payee_received_from, particulars, debit, credit, net_change
				FROM stock_entry_data
				UNION ALL
				SELECT jo_number, tran_date, doc_no_field, doc_type, reference,
					   payee_received_from, particulars, debit, credit, net_change
				FROM stock_reconciliation_data
			) s ON s.jo_number = j.jo_number

			UNION ALL

			-- 2. MR/MRS TOTAL:  (skip if 0)
			SELECT 1, j.jo_number, 2,
				   NULL, NULL, '', NULL,
				   'INVENTORY ENTRY TO GL', 'MR/MRS TOTAL:',
				   m.net_change, NULL, NULL
			FROM all_jos j
			JOIN mr_only_by_jo m ON m.jo_number = j.jo_number
			WHERE COALESCE(m.net_change, 0) <> 0

			UNION ALL

			-- 3. STOCK RECON TOTAL:  (skip if 0)
			SELECT 1, j.jo_number, 3,
				   NULL, NULL, '', NULL,
				   'INVENTORY ENTRY TO GL', 'STOCK RECON TOTAL:',
				   r.net_change, NULL, NULL
			FROM all_jos j
			JOIN recon_by_jo r ON r.jo_number = j.jo_number
			WHERE COALESCE(r.net_change, 0) <> 0

			UNION ALL

			-- 4. OVER ALL TOTAL:  (bold, skip if all zero)
			SELECT 1, j.jo_number, 4,
				   NULL, NULL, '', NULL,
				   '<b>INVENTORY ENTRY TO GL</b>', '<b>OVER ALL TOTAL:</b>',
				   COALESCE(m.net_change, 0),
				   COALESCE(r.net_change, 0),
				   COALESCE(s.net_change, 0)
			FROM all_jos j
			LEFT JOIN mr_only_by_jo m ON m.jo_number = j.jo_number
			LEFT JOIN recon_by_jo    r ON r.jo_number = j.jo_number
			LEFT JOIN stock_by_jo    s ON s.jo_number = j.jo_number
			WHERE COALESCE(m.net_change,0) <> 0
			   OR COALESCE(r.net_change,0) <> 0
			   OR COALESCE(s.net_change,0) <> 0

			UNION ALL

			-- 5. JE/PI detail rows
			SELECT 1, j.jo_number, 5,
				   c.tran_date, c.doc_no_field, c.doc_type, c.reference,
				   c.payee_received_from, c.particulars,
				   c.debit, c.credit, c.net_change
			FROM all_jos j
			JOIN (
				SELECT jo_number, tran_date, doc_no_field, doc_type, reference,
					   payee_received_from, particulars, debit, credit, net_change
				FROM journal_entry_data
				UNION ALL
				SELECT jo_number, tran_date, doc_no_field, doc_type, reference,
					   payee_received_from, particulars, debit, credit, net_change
				FROM purchase_invoice_data
			) c ON c.jo_number = j.jo_number

			UNION ALL

			-- 6. TOTAL:  (JE/PI subtotal, skip if all zero)
			SELECT 1, j.jo_number, 6,
				   NULL, NULL, '', NULL,
				   NULL, 'TOTAL:',
				   jp.debit, jp.credit, jp.net_change
			FROM all_jos j
			JOIN jepi_by_jo jp ON jp.jo_number = j.jo_number
			WHERE COALESCE(jp.debit,0) <> 0
			   OR COALESCE(jp.credit,0) <> 0
			   OR COALESCE(jp.net_change,0) <> 0

			UNION ALL

			-- 7. GRAND TOTAL: per JO (bold, skip if all zero)
			SELECT 1, j.jo_number, 7,
				   NULL, NULL, '', NULL,
				   NULL, '<b>GRAND TOTAL:</b>',
				   COALESCE(s.debit,0)  + COALESCE(jp.debit,0),
				   COALESCE(s.credit,0) + COALESCE(jp.credit,0),
				   COALESCE(s.net_change,0) + COALESCE(jp.net_change,0)
			FROM all_jos j
			LEFT JOIN stock_by_jo s  ON s.jo_number  = j.jo_number
			LEFT JOIN jepi_by_jo  jp ON jp.jo_number = j.jo_number
			WHERE COALESCE(s.debit,0)  + COALESCE(jp.debit,0)  <> 0
			   OR COALESCE(s.credit,0) + COALESCE(jp.credit,0) <> 0
			   OR COALESCE(s.net_change,0) + COALESCE(jp.net_change,0) <> 0

			UNION ALL

			-- 8 & 9. Two blank separator rows
			SELECT 1, j.jo_number, 8, NULL, NULL, '', NULL, NULL, NULL, NULL, NULL, NULL FROM all_jos j
			UNION ALL
			SELECT 1, j.jo_number, 9, NULL, NULL, '', NULL, NULL, NULL, NULL, NULL, NULL FROM all_jos j

			-- ============ REPORT-WIDE FOOTER ============

			UNION ALL
			SELECT 2, NULL, 1, NULL, NULL, '', NULL,
				   'INVENTORY ENTRY TO GL', 'MR/MRS TOTAL:',
				   net_change, NULL, NULL
			FROM mr_mrs_total
			WHERE COALESCE(net_change,0) <> 0

			UNION ALL
			SELECT 2, NULL, 2, NULL, NULL, '', NULL,
				   'INVENTORY ENTRY TO GL', 'STOCK RECON TOTAL:',
				   NULL, net_change, NULL
			FROM stock_recon_total
			WHERE COALESCE(net_change,0) <> 0

			UNION ALL
			SELECT 2, NULL, 3, NULL, NULL, '', NULL,
				   '<b>INVENTORY ENTRY TO GL</b>', '<b>OVER ALL TOTAL:</b>',
				   COALESCE(m.net_change,0), COALESCE(r.net_change,0), COALESCE(gl.net_change,0)
			FROM mr_mrs_total m CROSS JOIN stock_recon_total r CROSS JOIN stock_gl_total gl
			WHERE COALESCE(m.net_change,0)  <> 0
			   OR COALESCE(r.net_change,0)  <> 0
			   OR COALESCE(gl.net_change,0) <> 0

			UNION ALL
			SELECT 2, NULL, 4, NULL, NULL, '', NULL,
				   NULL, '<b>TOTAL:</b>',
				   debit, credit, net_change
			FROM jepi_total
			WHERE COALESCE(debit,0) <> 0
			   OR COALESCE(credit,0) <> 0
			   OR COALESCE(net_change,0) <> 0

			UNION ALL
			SELECT 2, NULL, 5, NULL, NULL, '', NULL,
				   NULL, '<b>GRAND TOTAL:</b>',
				   COALESCE(gl.debit,0)  + COALESCE(jp.debit,0),
				   COALESCE(gl.credit,0) + COALESCE(jp.credit,0),
				   COALESCE(gl.net_change,0) + COALESCE(jp.net_change,0)
			FROM stock_gl_total gl CROSS JOIN jepi_total jp
			WHERE COALESCE(gl.debit,0)  + COALESCE(jp.debit,0)  <> 0
			   OR COALESCE(gl.credit,0) + COALESCE(jp.credit,0) <> 0
			   OR COALESCE(gl.net_change,0) + COALESCE(jp.net_change,0) <> 0
		)

		SELECT
			r.doc_type            AS `DOC TYPE`,
			r.doc_no_field        AS `DOC NO`,
			r.reference           AS `REFERENCE`,
			r.tran_date           AS `TRAN DATE`,
			r.payee_received_from AS `PAYEE/RECEIVED FROM`,
			r.particulars         AS `PARTICULARS`,
			CASE WHEN r.debit      IS NOT NULL THEN
				CASE WHEN r.section_order IN (4,6,7) OR (r.block_order = 2 AND r.section_order IN (3,4,5))
				THEN CONCAT('<b>', FORMAT(r.debit, 2), '</b>')
					 ELSE FORMAT(r.debit, 2)
				END
			END AS `DEBIT`,
			CASE WHEN r.credit     IS NOT NULL THEN
				CASE WHEN r.section_order IN (4,6,7) OR (r.block_order = 2 AND r.section_order IN (3,4,5))
				THEN CONCAT('<b>', FORMAT(r.credit, 2), '</b>')
					 ELSE FORMAT(r.credit, 2)
				END
			END AS `CREDIT`,
			CASE WHEN r.net_change IS NOT NULL THEN
				CASE WHEN r.section_order IN (4,6,7) OR (r.block_order = 2 AND r.section_order IN (3,4,5))
				THEN CONCAT('<b>', FORMAT(r.net_change, 2), '</b>')
					 ELSE FORMAT(r.net_change, 2)
				END
			END AS `NET CHANGE`,
			CASE WHEN r.block_order = 1 AND r.section_order IN (8,9) THEN NULL
				 ELSE r.jo_number
			END AS `JO NUMBER`
		FROM all_rows r
		ORDER BY
			r.block_order,
			r.jo_number,
			r.section_order,
			r.tran_date,
			r.doc_no_field
	"""

	return frappe.db.sql(query, filters, as_dict=True)