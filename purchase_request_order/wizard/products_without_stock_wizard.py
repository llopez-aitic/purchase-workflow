# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ProductsWithoutStockWizard(models.TransientModel):
    _name = 'products.without.stock.wizard'

    message = fields.Text('Mensaje', readonly=True)

    @api.multi
    def send(self):
        self.ensure_one()

        context = self.env.context
        active_id = context['active_id']
        request_id = context['request_id']

        self.env['purchase.requisition.order'].browse(active_id).write({'state': 'done'})

        return {
            'name': 'Purchase request',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.request',
            'res_id': request_id,
        }


