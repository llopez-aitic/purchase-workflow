# Copyright 2018 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).


from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class PurchaseRequisitionDeliveryWizard(models.TransientModel):
    _name = "purchase.requisition.delivery.wizard"
    _description = "Purchase Requisition Delivery"

    item_ids = fields.One2many(
        'purchase.requisition.delivery.wizard.item',
        'wiz_id', string='Items')
    requisition_order_id = fields.Many2one('purchase.requisition.order',
                                        string='Requisition Order')
    requisition_order = fields.Char(string='Requisition Order')

    @api.model
    def _prepare_item(self, line):

        if line.product_id.immediately_usable_qty <= 0:
            product_available = 0
        else:
            product_available = line.product_id.immediately_usable_qty

        return {
            'line_id': line.id,
            'request_id': line.request_id.id,
            'requisition_order': line.request_id.name,
            'product_id': line.product_id.id,
            'name': line.name or line.product_id.name,
            'product_qty': line.product_qty,
            'product_available': product_available,
            'product_uom_id': line.product_uom_id.id,
        }

    @api.model
    def _check_valid_request_line(self, request_line_ids):
        picking_type = False
        company_id = False

        for line in self.env['purchase.request.line'].browse(request_line_ids):

            if line.request_id.state != 'approved':
                raise UserError(
                    _('Purchase Request %s is not approved') %
                    line.request_id.name)

            if line.purchase_state == 'done':
                raise UserError(
                    _('The purchase has already been completed.'))

            line_company_id = line.company_id \
                and line.company_id.id or False
            if company_id is not False \
                    and line_company_id != company_id:
                raise UserError(
                    _('You have to select lines '
                      'from the same company.'))
            else:
                company_id = line_company_id

            line_picking_type = line.request_id.picking_type_id or False
            if not line_picking_type:
                raise UserError(
                    _('You have to enter a Picking Type.'))
            if picking_type is not False \
                    and line_picking_type != picking_type:
                raise UserError(
                    _('You have to select lines '
                      'from the same Picking Type.'))
            else:
                picking_type = line_picking_type

    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequisitionDeliveryWizard, self).default_get(
            fields)
        request_line_obj = self.env['purchase.requisition.order.line']
        active_model_obj = self.env['purchase.requisition.order']
        request_line_ids = self.env.context.get('active_ids', False)
        active_model = self.env.context.get('active_model', False)
        # if not request_line_ids:
        #     return res
        # assert active_model == 'purchase.request.line', \
        #     'Bad context propagation'
        items = []
        # groups = []
        # self._check_valid_request_line(request_line_ids)
        request = active_model_obj.browse(active_model)
        request_lines = request_line_obj.browse(request_line_ids)
        for line in request_lines:
            items.append([0, 0, self._prepare_item(line)])
        #     groups.append(line.request_id.group_id.id)
        # if len(list(set(groups))) > 1:
        #     raise UserError(
        #         _('You cannot create a single purchase order from '
        #           'purchase requests that have different procurement group.'))
        res['item_ids'] = items
        res['requisition_order_id'] = request.id
        res['requisition_order'] = request.name
        # supplier_ids = request_lines.mapped('supplier_id').ids
        # if len(supplier_ids) == 1:
        #     res['supplier_id'] = supplier_ids[0]
        return res

    @api.multi
    def delivery_order(self):
        for item in self.item_ids:
            if item.product_qty < item.product_available:
                raise UserError(
                    _('The amount you have requested can not be greater than the actual'))
            item.line_id.write({'state_line': 'delivery', 'product_qty': item.product_qty})
        self.requisition_order_id.change_state()
        return True


class PurchaseRequesitionDeliveryItemWizard(models.TransientModel):
    _name = "purchase.requisition.delivery.wizard.item"
    _description = "Purchase Requisition Delivery Item"

    wiz_id = fields.Many2one(
        'purchase.requisition.delivery.wizard',
        string='Wizard', required=True, ondelete='cascade',
        readonly=True)
    line_id = fields.Many2one('purchase.requisition.order.line',
                              string='Purchase Requisition Line')
    request_id = fields.Many2one('purchase.requisition.order',
                                 related='line_id.request_id',
                                 string='Purchase Requisition')
    product_id = fields.Many2one('product.product', string='Product',
                                 related='line_id.product_id')
    name = fields.Char(string='Description', required=True)
    product_qty = fields.Float(string='Quantity to purchase',
                               digits=dp.get_precision('Product UoS'))
    product_available = fields.Float(string='Quantity available',
                               digits=dp.get_precision('Product UoS'))
    product_uom_id = fields.Many2one('product.uom', string='UoM')
    keep_description = fields.Boolean(string='Copy descriptions to new PO',
                                      help='Set true if you want to keep the '
                                           'descriptions provided in the '
                                           'wizard in the new PO.'
                                      )
