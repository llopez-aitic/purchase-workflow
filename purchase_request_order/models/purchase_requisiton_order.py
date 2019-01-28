# Copyright 2018 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from datetime import datetime
from dateutil.relativedelta import relativedelta

_STATES = [
    ('draft', 'Draft'),
    ('to_approve', 'To be approved'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('done', 'Delivered')
]


class PurchaseRequisitionOrder(models.Model):

    _name = 'purchase.requisition.order'
    _description = 'Purchase Requisition Order Internal'
    _inherit = 'purchase.request'

    @api.model
    def _get_default_requisition_name(self):
        return self.env['ir.sequence'].next_by_code('purchase.requisition.order')

    name = fields.Char('Request Reference', required=True,
                       default=_get_default_requisition_name,
                       track_visibility='onchange')

    line_ids = fields.One2many('purchase.requisition.order.line', 'request_id',
                               'Products to requisition',
                               readonly=False,
                               copy=True,
                               track_visibility='onchange')

    state = fields.Selection(selection=_STATES,
                             string='Status',
                             index=True,
                             track_visibility='onchange',
                             required=True,
                             copy=False,
                             default='draft')

    @api.multi
    def button_done(self):
        request_order = False
        for line in self.line_ids:
            if line.product_qty <= line.product_id.immediately_usable_qty:
                self.create_order_porduct_warehouse(line)
            else:
                request_order = self.create_request_order(request_order, line)

        if request_order is not False:
            msg = _("Some products do not have stock in store. You will proceed to create a purchase request.")
            return {
                'type': 'ir.actions.act_window',
                'name': 'Product without stock',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'products.without.stock.wizard',
                'view_id': self.env.ref('purchase_request_order.view_products_without_stock_wizard').id,
                'context': {'default_message':msg, 'request_id': request_order.id},
                'target': 'new',
            }

        return self.write({'state': 'done'})

    def create_request_order(self, request_order, line):

        if request_order is False:
            vals = {
                  'requested_by': line.request_id.requested_by.id,
                  'assigned_to': line.request_id.assigned_to.id,
                  'dpto_id': line.request_id.dpto_id.id or False,
                  'origin': line.origin,
                  'description': line.request_id.description,
                  'date_start': line.date_start,
                  'picking_type_id': line.request_id.picking_type_id.id or False,
                  'state': 'draft',
                  }
            request_order = self.env['purchase.request'].create(vals)

        vals_lines = {
            'product_id': line.product_id.id,
            'name': line.name,
            'product_qty': line.product_qty,
            'analytic_account_id': line.analytic_account_id.id or False,
            'date_required': line.date_required,
            'cancelled': line.cancelled,
            'request_id': request_order.id,
        }

        self.env['purchase.request.line'].create(vals_lines)


        return request_order


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.order.line"
    _inherit = 'purchase.request.line'

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', '=', 'product')],
        track_visibility='onchange')

