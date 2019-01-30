# Copyright 2018 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero, float_compare

from datetime import datetime
from dateutil.relativedelta import relativedelta

_STATES = [
    ('draft', 'Draft'),
    ('to_approve', 'To be approved'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('purchase', 'To purchase'),
    ('to_deliver', 'To Deliver'),
    ('done', 'Delivered')
]


class PurchaseRequisitionOrder(models.Model):

    _name = 'purchase.requisition.order'
    _description = 'Purchase Requisition Order Internal'
    _inherit = 'purchase.request'

    @api.model
    def _get_default_requisition_name(self):
        return self.env['ir.sequence'].next_by_code('purchase.requisition.order')

    @api.depends('line_ids.move_dest_ids.returned_move_ids',
                 'line_ids.move_dest_ids.state',
                 'line_ids.move_dest_ids.picking_id')
    def _compute_picking(self):
        for order in self:
            pickings = self.env['stock.picking'].search([('origin','=',order.name)])
            # for line in order.line_ids:
            #     # We keep a limited scope on purpose. Ideally, we should also use move_orig_ids and
            #     # do some recursive search, but that could be prohibitive if not done correctly.
            #     moves = line.move_dest_ids | line.move_dest_ids.mapped('returned_move_ids')
            #     pickings |= moves.mapped('picking_id')
            order.picking_ids = pickings
            # order.picking_count = len(pickings)

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

    delivery_flag = fields.Integer(string="Delivery", default=0)

    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Receptions', copy=False,
                                   store=True, compute_sudo=True)
    stock_location = fields.Many2one('stock.location', string="Destination stock")

    @api.multi
    def button_done(self):
        lines = []
        request_order = False
        for line in self.line_ids:
            if line.product_qty <= line.product_id.immediately_usable_qty:
                lines.append(line.id)
            else:
                line.state_line = 'purchase'

        if len(lines) == 0:
            for line in self.line_ids:
                line.state_line = 'purchase'
                request_order = self.create_request_order(request_order, line)

            self.state = 'purchase'
            self.delivery_flag = 1
            msg = _("Some products do not have stock in store. You will proceed to create a purchase request.")
            return {
                'type': 'ir.actions.act_window',
                'name': 'Product without stock',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'products.without.stock.wizard',
                'view_id': self.env.ref('purchase_request_order.view_products_without_stock_wizard').id,
                'context': {'default_message': msg, 'request_id': request_order.id},
                'target': 'new',
            }

        else:
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'purchase.requisition.delivery.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'active_model': self.id, 'active_ids': lines}
            }

        # return self.write({'state': 'done'})

    def change_state(self):
        self.state = 'to_deliver'
        self.delivery_flag = 2
        for line in self.line_ids:
            if line.state_line == 'purchase':
                self.state = 'purchase'
                self.delivery_flag = 1
                break

    def create_order_porduct_delivery(self):
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.requisition.delivery.wizard',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_model': self.id, 'active_ids': self.line_ids.ids}
        }

    def button_draft(self):
        super(PurchaseRequisitionOrder, self).button_draft()
        self.delivery_flag = 0

    def button_to_order_purchase(self):
        request_order = False
        self.state = 'to_deliver'
        for line in self.line_ids:
            if line.state_line == 'purchase':
                request_order = self.create_request_order(request_order, line)

        return {
            'name': 'Purchase request',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.request',
            'res_id': request_order.id,
        }

    def button_deliver_done(self):
        lines = []
        for line in self.line_ids:
            if line.state_line == 'purchase':
                if line.product_qty > line.product_id.immediately_usable_qty:
                    raise UserError(
                        _('There are still products without stock'))
                else:
                    lines.append(line.id)

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.requisition.delivery.wizard',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_model': self.id, 'active_ids': lines}
        }

    def button_deliver_move(self):
        if self.stock_location:
            self.delivery_flag = 0
            self.state = 'done'
            picking_id = self._create_picking()
            return {
                'name': 'Picking',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': picking_id,
            }
        else:
            raise UserError(
                _('Define the  stock location'))



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
                  'state': 'approved',
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

    @api.multi
    def _get_destination_location(self):
        self.ensure_one()
        # if self.dest_address_id:
        #     return self.dest_address_id.property_stock_customer.id
        return self.picking_type_id.default_location_dest_id.id

    @api.model
    def _prepare_picking(self):

        partner = self.requested_by.partner_id
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': partner.id,
            'date': self.date_start,
            'origin': self.name,
            # 'location_dest_id': self._get_destination_location(),
            'location_dest_id': self.stock_location.id,
            'location_id': partner.property_stock_supplier.id,
            'company_id': self.company_id.id,
        }

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        # for order in self:
        pickings = self.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
        if not pickings:
            res = self._prepare_picking()
            picking = StockPicking.create(res)
        else:
            picking = pickings[0]
        moves = self.line_ids._create_stock_moves(picking)
        moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
        seq = 0
        for move in sorted(moves, key=lambda move: move.date_expected):
            seq += 5
            move.sequence = seq
        moves._action_assign()
        picking.message_post_with_view('mail.message_origin_link',
                                       values={'self': picking, 'origin': self},
                                       subtype_id=self.env.ref('mail.mt_note').id)
        # return True

        return picking.id



    @api.multi
    def action_view_picking(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]

        # override the context to get rid of the default filtering on operation type
        result['context'] = {}
        # pick_ids = self.mapped('picking_ids')
        pick_ids = self.env['stock.picking'].search([('origin', '=', self.name)])
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids.id
        return result

_STATES_LINE = [
    ('draft', 'Draft'),
    ('delivery', 'Delivery'),
    ('purchase', 'To purchase')
]


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.order.line"
    _inherit = 'purchase.request.line'

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', '=', 'product')],
        track_visibility='onchange')

    state_line = fields.Selection(selection=_STATES_LINE,
                             string='Status',
                             index=True,
                             track_visibility='onchange',
                             copy=False,
                             default='draft')

    request_id = fields.Many2one('purchase.requisition.order',
                                 'Purchase Requisition',
                                 ondelete='cascade', readonly=True)

    @api.multi
    def _get_stock_move_price_unit(self):
        self.ensure_one()
        line = self[0]
        order = line.request_id
        # price_unit = line.price_unit
        price_unit = 0
        # if line.taxes_id:
        #     price_unit = line.taxes_id.with_context(round=False).compute_all(
        #         price_unit, currency=line.request_id.currency_id, quantity=1.0, product=line.product_id,
        #         partner=line.request_id.requested_by.partner_id
        #     )['total_excluded']
        # if line.product_uom.id != line.product_id.uom_id.id:
        #     price_unit *= line.product_id.uom_id.factor / line.product_id.uom_id.factor
        # if order.currency_id != order.company_id.currency_id:
        #     price_unit = order.currency_id.compute(price_unit, order.company_id.currency_id, round=False)
        return price_unit

    @api.multi
    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res
        qty = 0.0
        price_unit = self._get_stock_move_price_unit()
        for move in self.move_dest_ids.filtered(
                lambda x: x.state != 'cancel' and not x.location_dest_id.usage == "supplier"):
            qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_id.uom_id, rounding_method='HALF-UP')
        template = {
            'name': self.name or '',
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_id.id,
            'date': self.request_id.date_start,
            'date_expected': self.date_required,
            'location_id': self.request_id.requested_by.partner_id.property_stock_supplier.id,
            'location_dest_id': self.request_id.stock_location.id,
            'picking_id': picking.id,
            'partner_id': self.request_id.requested_by.partner_id.id,
            'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.request_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.request_id.picking_type_id.id,
            'group_id': self.request_id.group_id.id,
            'origin': self.request_id.name,
            'route_ids': self.request_id.picking_type_id.warehouse_id and [
                (6, 0, [x.id for x in self.request_id.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': self.request_id.picking_type_id.warehouse_id.id,
        }
        diff_quantity = self.product_qty - qty
        if float_compare(diff_quantity, 0.0, precision_rounding=self.product_id.uom_id.rounding) > 0:
            quant_uom = self.product_id.uom_id
            get_param = self.env['ir.config_parameter'].sudo().get_param
            if self.product_id.uom_id.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                product_qty = self.product_id.uom_id._compute_quantity(diff_quantity, quant_uom, rounding_method='HALF-UP')
                template['product_uom'] = quant_uom.id
                template['product_uom_qty'] = product_qty
            else:
                template['product_uom_qty'] = diff_quantity
            res.append(template)
        return res

    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            for val in line._prepare_stock_moves(picking):
                done += moves.create(val)
        return done

