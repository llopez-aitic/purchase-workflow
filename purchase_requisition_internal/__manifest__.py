# Copyright 2018 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Purchase Requisition Internal",
    "author": "Eficent, "
              "AITIC",
    "version": "11.0.1.0.0",
    "summary": "Use this module to create a requisition internal "
               "If there are no products, it becomes a purchase request. ",
    "category": "Purchase Management",
    "depends": [
        "purchase_request_order",
    ],
    "data": [
        "data/purchase_requisition_sequence.xml",
        "views/purchase_requisition_order_view.xml",
        "wizard/products_without_stock_wizard_view.xml",
        "wizard/purchase_requisition_line_delivery_wizard_view.xml",
    ],
    'demo': [
    ],
    "license": 'LGPL-3',
    'installable': True,
    'application': True,
}
