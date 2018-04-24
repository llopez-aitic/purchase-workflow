
# Copyright 2016-2017 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models, exceptions


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    request_id = fields.Many2one(
        comodel_name='purchase.request',
        ondelete='restrict',
        string='Latest Purchase Request',
        copy=False,
    )

    @api.multi
    def _prepare_purchase_request_line(self):
        self.ensure_one()
        product = self.product_id
        procurement_uom_po_qty = self.product_uom._compute_quantity(
            self.product_qty, product.uom_po_id)
        return {
            'product_id': product.id,
            'name': product.name,
            'date_required': self.date_planned,
            'product_uom_id': product.uom_po_id.id,
            'product_qty': procurement_uom_po_qty,
            'request_id': self.request_id.id,
            'rule_id': self._get_rule(product.id, location_)
        }

    @api.multi
    def _prepare_purchase_request(self):
        self.ensure_one()

        return {
            'origin': self.origin,
            'company_id': self.company_id.id,
            'picking_type_id': self.rule_id.picking_type_id.id,
        }

    @api.multi
    def _search_existing_purchase_request(self):
        """
        This method is to be implemented by other modules that can
        provide a criteria to select the appropriate purchase request to be
        extended.
        :return: False
        """
        return False

    @api.multi
    def run(self):
        self.ensure_one()
        if self.is_create_purchase_request_allowed():
            self.create_purchase_request()
            return True
        return super(ProcurementGroup, self).run()

    @api.multi
    def is_create_purchase_request_allowed(self):
        """
        Tell if current procurement order should
        create a purchase request or not.
        :return: boolean
        """
        self.ensure_one()
        return self.rule_id and self.rule_id.action == 'buy' \
            and self.product_id.purchase_request

    @api.multi
    def create_purchase_request(self):
        """
        Create a purchase request containing procurement order product.
        """
        self.ensure_one()
        if not self.is_create_purchase_request_allowed():
            raise exceptions.Warning(
                _("You can't create a purchase request "
                  "for this procurement order (%s).") % self.name)

        purchase_request_model = self.env['purchase.request']
        purchase_request_line_model = self.env['purchase.request.line']

        # Search for an existing Purchase Request to be considered
        # to be extended.
        pr = self._search_existing_purchase_request()
        if not pr:
            request_data = self._prepare_purchase_request()
            req = purchase_request_model.create(request_data)
            self.message_post(body=_("Purchase Request created"))
            self.request_id = req
        request_line_data = self._prepare_purchase_request_line()
        purchase_request_line_model.create(request_line_data),
        self.message_post(body=_("Purchase Request extended."))
        return self.request_id