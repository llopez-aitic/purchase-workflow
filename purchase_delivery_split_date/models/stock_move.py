# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model
    def _get_assign_picking_domain(self, move):
        move_dt_expected = fields.Date.from_string(move.date_expected)
        req_date = fields.Date.to_string(move_dt_expected)
        return [
            ('group_id', '=', move.group_id.id),
            ('location_id', '=', move.location_id.id),
            ('location_dest_id', '=', move.location_dest_id.id),
            ('picking_type_id', '=', move.picking_type_id.id),
            ('printed', '=', False),
            ('scheduled_date', '>=', '%s 00:00:00' % req_date),
            ('scheduled_date', '<=', '%s 23:59:59' % req_date),
            ('state', 'in', ['draft', 'confirmed', 'waiting',
                             'partially_available', 'assigned'])]

    @api.model
    def assign_picking_by_date_expected(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations, picking
        type and expected date (moves should already have them identical).
        Otherwise, create a new picking to assign them to.
        This method is a variation of _assign_picking.
        """
        Picking = self.env['stock.picking']
        for move in self:
            recompute = False
            picking = Picking.search(self._get_assign_picking_domain(move),
                                     limit=1)
            if picking:
                if picking.partner_id.id != move.partner_id.id or \
                        picking.origin != move.origin:
                    picking.write({
                        'partner_id': False,
                        'origin': False,
                    })
            else:
                recompute = True
                picking = Picking.create(move._get_new_picking_values())
            move.write({'picking_id': picking.id})
            move._assign_picking_post_process(new=recompute)
            # If this method is called in batch by a write on a
            if recompute:
                move.recompute()
        return True
