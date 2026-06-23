# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ZrnCommercialChannel(models.Model):
    _name = 'zrn_commercial.commercial.channel'
    _description = 'Canal comercial'
    _order = 'name, id'

    name = fields.Char(string='Canal comercial', required=True)
    code = fields.Char(string='Codigo')
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )
    description = fields.Text(string='Descripcion')
    notes = fields.Text(string='Notas internas')
    owner_user_id = fields.Many2one(
        'res.users',
        string='Responsable comercial',
    )
    partner_link_ids = fields.One2many(
        'zrn_commercial.commercial.channel.partner',
        'channel_id',
        string='Clientes / PDVs asignados',
    )
    partner_count = fields.Integer(
        string='Clientes / PDVs',
        compute='_compute_partner_count',
        store=False,
    )
    opportunity_count = fields.Integer(
        string='Oportunidades',
        compute='_compute_related_counts',
        store=False,
    )
    quotation_count = fields.Integer(
        string='Cotizaciones',
        compute='_compute_related_counts',
        store=False,
    )
    account_without_followup_count = fields.Integer(
        string='Cuentas sin seguimiento',
        compute='_compute_related_counts',
        store=False,
    )

    _sql_constraints = [
        (
            'company_code_uniq',
            'unique(company_id, code)',
            'El codigo de canal debe ser unico por compania.',
        ),
        (
            'company_name_uniq',
            'unique(company_id, name)',
            'El nombre de canal debe ser unico por compania.',
        ),
    ]

    @api.depends('partner_link_ids')
    def _compute_partner_count(self):
        for channel in self:
            channel.partner_count = len(channel.partner_link_ids)

    @api.depends('partner_link_ids', 'partner_link_ids.partner_id')
    def _compute_related_counts(self):
        lead_model = self.env['crm.lead'].sudo()
        order_model = self.env['sale.order'].sudo()
        for channel in self:
            channel.opportunity_count = lead_model.search_count([
                ('zrn_channel_id', '=', channel.id),
                ('type', '=', 'opportunity'),
            ])
            channel.quotation_count = order_model.search_count([
                ('zrn_channel_id', '=', channel.id),
                ('state', 'in', ['draft', 'sent', 'sale']),
            ])
            channel.account_without_followup_count = len(channel.partner_link_ids.filtered(
                lambda link: not link.partner_id.activity_state or link.partner_id.activity_state == 'overdue'
            ))

    def action_open_customers(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('zrn_commercial.action_zrn_commercial_customers')
        action['domain'] = [('zrn_primary_channel_id', '=', self.id)]
        return action

    def action_open_opportunities(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('zrn_commercial.action_zrn_commercial_opportunities')
        action['domain'] = [('zrn_channel_id', '=', self.id), ('type', '=', 'opportunity')]
        action['context'] = dict(self.env.context, default_zrn_channel_id=self.id)
        return action

    def action_open_quotations(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('zrn_commercial.action_zrn_commercial_quotations')
        action['domain'] = [('zrn_channel_id', '=', self.id)]
        action['context'] = dict(self.env.context, default_zrn_channel_id=self.id)
        return action


class ZrnCommercialChannelPartner(models.Model):
    _name = 'zrn_commercial.commercial.channel.partner'
    _description = 'Cliente o PDV asignado a canal comercial'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    channel_id = fields.Many2one(
        'zrn_commercial.commercial.channel',
        string='Canal comercial',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        related='channel_id.company_id',
        store=True,
        readonly=True,
    )
    available_partner_ids = fields.Many2many(
        'res.partner',
        string='Clientes disponibles',
        compute='_compute_available_partner_ids',
        store=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente / PDV',
        required=True,
        ondelete='restrict',
        domain="[('id', 'in', available_partner_ids)]",
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente comercial',
        related='partner_id.commercial_partner_id',
        store=True,
        readonly=True,
    )
    vat = fields.Char(
        string='NIT',
        related='partner_id.vat',
        store=True,
        readonly=True,
    )
    city = fields.Char(
        string='Ciudad',
        related='partner_id.city',
        store=True,
        readonly=True,
    )
    state_id = fields.Many2one(
        'res.country.state',
        string='Departamento',
        related='partner_id.state_id',
        store=True,
        readonly=True,
    )
    country_id = fields.Many2one(
        'res.country',
        string='Pais',
        related='partner_id.country_id',
        store=True,
        readonly=True,
    )
    active = fields.Boolean(string='Activo', default=True)
    notes = fields.Text(string='Notas')

    _sql_constraints = [
        (
            'partner_uniq',
            'unique(partner_id)',
            'El cliente o PDV ya fue asignado a un canal comercial.',
        ),
    ]

    @api.depends('channel_id', 'partner_id')
    def _compute_available_partner_ids(self):
        Partner = self.env['res.partner']
        assigned_partner_ids = self.search([]).mapped('partner_id').ids
        for record in self:
            current_partner_ids = record.partner_id.ids
            blocked_partner_ids = list(set(assigned_partner_ids) - set(current_partner_ids))
            available_partners = Partner.search([
                ('customer_rank', '>', 0),
                ('type', '!=', 'private'),
                ('id', 'not in', blocked_partner_ids),
            ])
            record.available_partner_ids = available_partners

    @api.constrains('partner_id')
    def _check_customer_partner(self):
        for record in self:
            partner = record.partner_id
            if not partner:
                continue
            if partner.type == 'private':
                raise ValidationError('No se pueden asignar contactos privados a un canal comercial.')
            if partner.customer_rank <= 0:
                raise ValidationError('Solo se pueden asignar clientes o PDVs con perfil comercial.')
