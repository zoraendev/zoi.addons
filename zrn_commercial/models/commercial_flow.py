# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ZrnCommercialCrmLead(models.Model):
    _inherit = 'crm.lead'

    zrn_brand_id = fields.Many2one(
        'zrn_commercial.commercial.brand',
        string='Marca comercial',
        tracking=True,
    )
    zrn_channel_id = fields.Many2one(
        'zrn_commercial.commercial.channel',
        string='Canal comercial',
        tracking=True,
    )
    zrn_allowed_channel_ids = fields.Many2many(
        'zrn_commercial.commercial.channel',
        compute='_compute_zrn_allowed_channel_ids',
        string='Canales permitidos',
    )
    zrn_priority = fields.Selection(
        [
            ('low', 'Baja'),
            ('medium', 'Media'),
            ('high', 'Alta'),
            ('critical', 'Critica'),
        ],
        string='Prioridad comercial',
        default='medium',
        tracking=True,
    )
    zrn_next_step_note = fields.Char(string='Proximo paso comercial', tracking=True)
    zrn_followup_state = fields.Selection(
        [
            ('no_activity', 'Sin actividad'),
            ('planned', 'Con seguimiento'),
            ('today', 'Actividad hoy'),
            ('overdue', 'Actividad vencida'),
        ],
        string='Seguimiento comercial',
        compute='_compute_zrn_followup_state',
    )

    @api.depends('zrn_brand_id', 'zrn_brand_id.suggested_channel_ids')
    def _compute_zrn_allowed_channel_ids(self):
        all_channels = self.env['zrn_commercial.commercial.channel'].search([('active', '=', True)])
        for lead in self:
            lead.zrn_allowed_channel_ids = lead.zrn_brand_id.suggested_channel_ids or all_channels

    @api.depends('activity_state')
    def _compute_zrn_followup_state(self):
        mapping = {
            'planned': 'planned',
            'today': 'today',
            'overdue': 'overdue',
        }
        for lead in self:
            lead.zrn_followup_state = mapping.get(lead.activity_state, 'no_activity')

    @api.constrains('type', 'active', 'zrn_brand_id', 'zrn_channel_id', 'stage_id')
    def _check_zrn_commercial_classification(self):
        for lead in self:
            if lead.type != 'opportunity' or not lead.active:
                continue
            # Solo exigimos marca y canal al llegar a la etapa Ganada (Won / id=4 o probability=100)
            is_won = lead.probability == 100 or (lead.stage_id and lead.stage_id.is_won)
            if is_won and (not lead.zrn_brand_id or not lead.zrn_channel_id):
                raise ValidationError(
                    'Las oportunidades ganadas deben tener marca comercial y canal comercial definidos.'
                )

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        values = super()._prepare_customer_values(partner_name, is_company=is_company, parent_id=parent_id)
        values.update({
            'zrn_account_owner_id': self.user_id.id or False,
            'zrn_commercial_status': 'active',
        })
        if self.zrn_brand_id:
            values['zrn_primary_brand_id'] = self.zrn_brand_id.id
            values['zrn_brand_ids'] = [(4, self.zrn_brand_id.id)]
        return values

    def _prepare_opportunity_quotation_context(self):
        context = super()._prepare_opportunity_quotation_context()
        self.ensure_one()
        context.update({
            'default_zrn_brand_id': self.zrn_brand_id.id,
            'default_zrn_channel_id': self.zrn_channel_id.id,
        })
        return context

    def _convert_opportunity_data(self, customer, team_id=False):
        values = super()._convert_opportunity_data(customer, team_id=team_id)
        self.env.cr.postcommit.add(self._sync_zrn_partner_profile)
        return values

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.partner_id:
                record._sync_zrn_partner_profile()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'partner_id' in vals or 'zrn_brand_id' in vals or 'zrn_channel_id' in vals:
            for record in self:
                if record.partner_id:
                    record._sync_zrn_partner_profile()
        return result

    def _sync_zrn_partner_profile(self):
        channel_partner_model = self.env['zrn_commercial.commercial.channel.partner']
        for lead in self.filtered('partner_id'):
            partner = lead.partner_id
            partner_values = {}
            if lead.zrn_brand_id:
                if lead.zrn_brand_id not in partner.zrn_brand_ids:
                    partner_values.setdefault('zrn_brand_ids', []).append((4, lead.zrn_brand_id.id))
                if not partner.zrn_primary_brand_id:
                    partner_values['zrn_primary_brand_id'] = lead.zrn_brand_id.id
            if lead.user_id and not partner.zrn_account_owner_id:
                partner_values['zrn_account_owner_id'] = lead.user_id.id
            if partner_values:
                partner.write(partner_values)

            if not lead.zrn_channel_id:
                continue
            existing_link = channel_partner_model.search([('partner_id', '=', partner.id)], limit=1)
            if existing_link:
                if existing_link.channel_id != lead.zrn_channel_id:
                    existing_link.write({'channel_id': lead.zrn_channel_id.id})
                continue
            channel_partner_model.create({
                'channel_id': lead.zrn_channel_id.id,
                'partner_id': partner.id,
                'notes': 'Asignado automaticamente desde oportunidad comercial.',
            })


class ZrnCommercialResPartner(models.Model):
    _inherit = 'res.partner'

    zrn_primary_brand_id = fields.Many2one(
        'zrn_commercial.commercial.brand',
        string='Marca comercial principal',
    )
    zrn_brand_ids = fields.Many2many(
        'zrn_commercial.commercial.brand',
        'zrn_commercial_partner_brand_rel',
        'partner_id',
        'brand_id',
        string='Marcas comerciales',
    )
    zrn_primary_channel_id = fields.Many2one(
        'zrn_commercial.commercial.channel',
        string='Canal comercial principal',
        compute='_compute_zrn_primary_channel_id',
        search='_search_zrn_primary_channel_id',
    )
    zrn_commercial_status = fields.Selection(
        [
            ('prospect', 'Prospecto'),
            ('active', 'Activo'),
            ('dormant', 'Dormido'),
            ('blocked', 'Bloqueado'),
        ],
        string='Estado comercial',
        default='prospect',
    )
    zrn_account_owner_id = fields.Many2one(
        'res.users',
        string='Responsable comercial',
    )
    zrn_last_activity_date = fields.Date(
        string='Ultima gestion',
        compute='_compute_zrn_activity_metrics',
    )
    zrn_followup_state = fields.Selection(
        [
            ('no_activity', 'Sin actividad'),
            ('planned', 'Con seguimiento'),
            ('today', 'Actividad hoy'),
            ('overdue', 'Actividad vencida'),
        ],
        string='Seguimiento comercial',
        compute='_compute_zrn_activity_metrics',
    )
    zrn_opportunity_count = fields.Integer(
        string='Oportunidades',
        compute='_compute_zrn_commercial_counts',
    )
    zrn_quotation_count = fields.Integer(
        string='Cotizaciones',
        compute='_compute_zrn_commercial_counts',
    )

    def _compute_zrn_primary_channel_id(self):
        link_model = self.env['zrn_commercial.commercial.channel.partner'].sudo()
        grouped_links = {
            link.partner_id.id: link.channel_id
            for link in link_model.search([('partner_id', 'in', self.ids)])
        }
        for partner in self:
            partner.zrn_primary_channel_id = grouped_links.get(partner.id)

    def _search_zrn_primary_channel_id(self, operator, value):
        links = self.env['zrn_commercial.commercial.channel.partner'].sudo().search([
            ('channel_id', operator, value),
        ])
        return [('id', 'in', links.mapped('partner_id').ids)]

    @api.depends('activity_state', 'activity_ids.date_deadline')
    def _compute_zrn_activity_metrics(self):
        mapping = {
            'planned': 'planned',
            'today': 'today',
            'overdue': 'overdue',
        }
        for partner in self:
            partner.zrn_followup_state = mapping.get(partner.activity_state, 'no_activity')
            deadlines = partner.activity_ids.mapped('date_deadline')
            partner.zrn_last_activity_date = max(deadlines) if deadlines else False

    def _compute_zrn_commercial_counts(self):
        lead_model = self.env['crm.lead'].sudo()
        order_model = self.env['sale.order'].sudo()
        for partner in self:
            partner_ids = (partner | partner.child_ids).ids
            partner.zrn_opportunity_count = lead_model.search_count([
                ('partner_id', 'in', partner_ids),
                ('type', '=', 'opportunity'),
            ])
            partner.zrn_quotation_count = order_model.search_count([
                ('partner_id', 'in', partner_ids),
                ('state', 'in', ['draft', 'sent', 'sale']),
            ])


class ZrnCommercialSaleOrder(models.Model):
    _inherit = 'sale.order'

    zrn_brand_id = fields.Many2one(
        'zrn_commercial.commercial.brand',
        string='Marca comercial',
        tracking=True,
    )
    zrn_channel_id = fields.Many2one(
        'zrn_commercial.commercial.channel',
        string='Canal comercial',
        tracking=True,
    )
    zrn_lead_id = fields.Many2one(
        'crm.lead',
        string='Oportunidad comercial',
        compute='_compute_zrn_lead_id',
        store=True,
    )
    zrn_followup_state = fields.Selection(
        [
            ('no_activity', 'Sin actividad'),
            ('planned', 'Con seguimiento'),
            ('today', 'Actividad hoy'),
            ('overdue', 'Actividad vencida'),
        ],
        string='Seguimiento comercial',
        compute='_compute_zrn_followup_state',
    )
    zrn_brand_portfolio_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_zrn_brand_portfolio_product_ids',
        string='Portafolio de marca',
    )
    zrn_brand_mismatch_count = fields.Integer(
        string='Productos fuera de marca',
        compute='_compute_zrn_brand_warning',
    )
    zrn_brand_warning = fields.Text(
        string='Alerta comercial',
        compute='_compute_zrn_brand_warning',
    )

    @api.depends('opportunity_id')
    def _compute_zrn_lead_id(self):
        for order in self:
            order.zrn_lead_id = order.opportunity_id

    @api.depends('activity_state')
    def _compute_zrn_followup_state(self):
        mapping = {
            'planned': 'planned',
            'today': 'today',
            'overdue': 'overdue',
        }
        for order in self:
            order.zrn_followup_state = mapping.get(order.activity_state, 'no_activity')

    @api.depends('zrn_brand_id', 'zrn_brand_id.product_link_ids', 'zrn_brand_id.product_link_ids.product_id')
    def _compute_zrn_brand_portfolio_product_ids(self):
        for order in self:
            order.zrn_brand_portfolio_product_ids = order.zrn_brand_id.product_link_ids.mapped('product_id')

    @api.depends('zrn_brand_id', 'order_line.product_id', 'order_line.display_type')
    def _compute_zrn_brand_warning(self):
        for order in self:
            order.zrn_brand_warning = False
            order.zrn_brand_mismatch_count = 0
            if not order.zrn_brand_id:
                continue
            brand_product_ids = set(order.zrn_brand_id.product_link_ids.mapped('product_id').ids)
            if not brand_product_ids:
                continue
            mismatch_lines = order.order_line.filtered(
                lambda line: not line.display_type and line.product_id and line.product_id.id not in brand_product_ids
            )
            order.zrn_brand_mismatch_count = len(mismatch_lines)
            if mismatch_lines:
                product_names = ', '.join(mismatch_lines.mapped('product_id.display_name')[:5])
                order.zrn_brand_warning = (
                    'La cotizacion incluye productos fuera del portafolio oficial de la marca: %s.'
                ) % product_names

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            opportunity_id = values.get('opportunity_id')
            if opportunity_id:
                lead = self.env['crm.lead'].browse(opportunity_id)
                values.setdefault('zrn_brand_id', lead.zrn_brand_id.id)
                values.setdefault('zrn_channel_id', lead.zrn_channel_id.id)
            partner_id = values.get('partner_id')
            if partner_id and not values.get('zrn_channel_id'):
                partner = self.env['res.partner'].browse(partner_id)
                values['zrn_channel_id'] = partner.zrn_primary_channel_id.id
        return super().create(vals_list)

    @api.onchange('opportunity_id')
    def _onchange_zrn_opportunity_id(self):
        if not self.opportunity_id:
            return
        self.zrn_brand_id = self.opportunity_id.zrn_brand_id
        self.zrn_channel_id = self.opportunity_id.zrn_channel_id

    @api.onchange('partner_id')
    def _onchange_zrn_partner_id(self):
        if self.partner_id and not self.zrn_channel_id:
            self.zrn_channel_id = self.partner_id.zrn_primary_channel_id
        if self.partner_id and not self.zrn_brand_id and self.partner_id.zrn_primary_brand_id:
            self.zrn_brand_id = self.partner_id.zrn_primary_brand_id

    def action_confirm(self):
        for order in self:
            # Solo exigimos marca y canal si la venta proviene de un flujo de oportunidad CRM comercial
            if order.opportunity_id and (not order.zrn_brand_id or not order.zrn_channel_id):
                raise ValidationError(
                    'No se puede confirmar una cotizacion comercial sin marca y canal comercial definidos.'
                )
        return super().action_confirm()
