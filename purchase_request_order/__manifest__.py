# Copyright 2018 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Purchase Request Order",
    "author": "Eficent, "
              "AITIC",
    "version": "11.0.1.0.0",
    "summary": "Use this module to create order purchase "
               "from approved purchase request. ",
    "category": "Purchase Management",
    "depends": [
        "purchase_request",
        "hr"
    ],
    "data": [
        "data/purchase_template_mail_request.xml",
        "views/purchase_request_view.xml",
        "security/purchase_request_order.xml",
        "wizard/purchase_request_line_make_purchase_order_view.xml",
    ],
    'demo': [
    ],
    "license": 'LGPL-3',
    'installable': True,
    'application': True,
}
