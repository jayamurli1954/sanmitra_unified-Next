"""MongoDB collection names for the MitraBooks business module.

Kept in a module with no app imports so that any business submodule (for
example services/indexes.py) can use them without importing
app.modules.business.service, which would create an import cycle.
app.modules.business.service re-exports every name, so existing
`business_service.X_COLLECTION` references are unchanged.
"""

PARTIES_COLLECTION = "business_parties"
VOUCHERS_COLLECTION = "business_vouchers"
VOUCHER_COUNTERS_COLLECTION = "business_voucher_counters"
SALES_INVOICES_COLLECTION = "business_sales_invoices"
PURCHASE_BILLS_COLLECTION = "business_purchase_bills"
INVOICE_SETTINGS_COLLECTION = "business_invoice_settings"
ADMIN_SETTINGS_COLLECTION = "business_admin_settings"
GST_PERIOD_LOCKS_COLLECTION = "business_gst_period_locks"
CREDIT_NOTES_COLLECTION = "business_credit_notes"
DEBIT_NOTES_COLLECTION = "business_debit_notes"
GST_SETTLEMENTS_COLLECTION = "business_gst_settlements"
CA_DOCUMENTS_COLLECTION = "business_ca_document_metadata"
CA_CLIENTS_COLLECTION = "business_ca_clients"
BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION = "business_document_attachments"
