# Copyright (c) 2026, inzi and contributors
# For license information, please see license.txt

# ==============================================================================
# doctype/deal_product/deal_product.py -- "Deal Product" is a CHILD TABLE
# doctype (see its .json: "istable": 1), not something anyone ever opens as
# its own standalone record. It exists purely to be the row-shape behind
# Deal's `products` field, a "Table MultiSelect" that lets someone pick
# multiple Items to attach to a Deal (shown in the Products tab, see
# deal.json's field_order). Each Deal Product row is just one wrapped Item
# Link -- no extra fields, no custom logic needed, which is why the class
# body below is empty (`pass`).
# ==============================================================================

from frappe.model.document import Document


class DealProduct(Document):
	pass
