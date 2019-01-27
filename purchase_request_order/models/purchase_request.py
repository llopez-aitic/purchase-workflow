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
    ('done', 'Done')
]


class PurchaseRequestOrder(models.Model):

    _name = 'purchase.request'
    _description = 'Purchase Request Order'
    _inherit = 'purchase.request'

    dpto_id = fields.Many2one('hr.department', string="Departamento", compute='_compute_dpto',
                              default=lambda self: self.requested_by.employee_ids[0].department_id.id if self.requested_by.employee_ids else False)

    @api.depends('requested_by')
    def _compute_dpto(self):
        self.dpto_id = self.requested_by.employee_ids[0].department_id.id if self.requested_by.employee_ids else False

    @api.multi
    def button_to_approve(self):
        self.ensure_one()
        if self.line_ids:
            for line in self.line_ids:
                if len(line.product_id) == 0:
                    raise ValidationError(
                        _('No puede tener un producto vacio. Debe contactar al admnistrador para crear el producto deseado !'))
        else:
            raise ValidationError(_('Debe introducir una linea de producto'))
        self.to_approve_allowed_check()
        self.send_mail_approved_request()

        return self.write({'state': 'to_approve'})

    def send_mail_approved_request(self):
        self.ensure_one()
        IrModelData = self.env['ir.model.data']
        template_mail = IrModelData.xmlid_to_object('purchase_request_order.email_template_request_approved')
        if template_mail:
            MailTemplate = self.env['mail.template']
            body_html = MailTemplate.render_template(template_mail.body_html, 'purchase.request', self.id)
            subject = MailTemplate.render_template(template_mail.subject, 'purchase.request', self.id)
            email_from = MailTemplate.render_template(template_mail.email_from, 'purchase.request', self.id)

            menu_id = self.env['ir.model.data'].xmlid_to_res_id('purchase_request.menu_purchase_request')
            action_id = self.env['ir.model.data'].xmlid_to_res_id('purchase_request.purchase_request_form_action')
            params = '/web?#id=%s&view_type=form&model=purchase.request&action=%s&menu_id=%s' % (
            self.id,  action_id, menu_id)

            base_url = self.env['ir.config_parameter'].get_param('web.base.url') or ''
            _url = base_url + params

            body_html = body_html.replace('$1', _url)

            values = {
                'model': None,
                'res_id': None,
                'subject': subject,
                'body_html': body_html,
                'parent_id': None,
                'email_from': email_from,
                'email_to': self.assigned_to.email,
            }
            mail_mail_obj = self.env['mail.mail']
            mail_id = mail_mail_obj.create(values)
            mail_id.send()

    @api.multi
    def button_send_to_order(self):
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.request.line.make.purchase.order',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_model': self.id, 'active_ids': self.line_ids.ids}
        }

    @api.multi
    def to_approve_allowed_check(self):
        for rec in self:
            if not rec.assigned_to:
                raise ValidationError("Debe definir un aprobador para la solicitud de compra")


class PurchaseRequesOrdertLine(models.Model):
    _inherit = "purchase.request.line"

    product_id = fields.Many2one(
        'product.product', 'Product',
        track_visibility='onchange')

