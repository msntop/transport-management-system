# -*- coding: utf-8 -*-
# Copyright 2012, Israel Cruz Argil, Argil Consulting
# Copyright 2016, Jarsa Sistemas, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from __future__ import division

from datetime import datetime, timedelta
from openerp import _, api, fields, models
from openerp.exceptions import ValidationError


class TmsTravel(models.Model):
    _name = 'tms.travel'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Travel'
    _order = "date desc"

    waybill_ids = fields.Many2many(
        'tms.waybill', string='Waybills')
    driver_factor_ids = fields.One2many(
        'tms.factor', 'travel_id', string='Travel Driver Payment Factors',
        domain=[('category', '=', 'driver')])
    name = fields.Char('Travel Number')
    state = fields.Selection(
        [('draft', 'Pending'), ('progress', 'In Progress'), ('done', 'Done'),
         ('cancel', 'Cancelled'), ('closed', 'Closed')],
        'State', readonly=True, default='draft')
    route_id = fields.Many2one(
        'tms.route', 'Route', required=True,
        states={'cancel': [('readonly', True)],
                'closed': [('readonly', True)]})
    travel_duration = fields.Float(
        compute='_compute_travel_duration',
        string='Duration Sched',
        help='Travel Scheduled duration in hours')
    travel_duration_real = fields.Float(
        compute='_compute_travel_duration_real',
        string='Duration Real', help="Travel Real duration in hours")
    distance_route = fields.Float(
        related="route_id.distance",
        string='Route Distance (mi./km)')
    fuel_efficiency_expected = fields.Float(
        string='Fuel Efficiency Expected',
        compute="_compute_fuel_efficiency_expected")
    kit_id = fields.Many2one(
        'tms.unit.kit', 'Kit')
    unit_id = fields.Many2one(
        'fleet.vehicle', 'Unit',
        required=True)
    trailer1_id = fields.Many2one(
        'fleet.vehicle', 'Trailer1')
    dolly_id = fields.Many2one(
        'fleet.vehicle', 'Dolly',
        domain=[('fleet_type', '=', 'dolly')])
    trailer2_id = fields.Many2one(
        'fleet.vehicle', 'Trailer2',
        domain=[('fleet_type', '=', 'trailer')])
    employee_id = fields.Many2one(
        'hr.employee', 'Driver', required=True,
        domain=[('driver', '=', True)])
    date = fields.Datetime(
        'Date  registered', required=True,
        default=(fields.Datetime.now))
    date_start = fields.Datetime(
        'Start Sched',
        default=(fields.Datetime.now))
    date_end = fields.Datetime(
        'End Sched',
        store=True,
        compute='_compute_date_end')
    date_start_real = fields.Datetime(
        'Start Real')
    date_end_real = fields.Datetime(
        'End Real')
    distance_driver = fields.Float(
        'Distance traveled by driver (mi./km)',
        compute='_compute_distance_driver',
        store=True)
    distance_loaded = fields.Float(
        'Distance Loaded (mi./km)')
    distance_empty = fields.Float(
        'Distance Empty (mi./km)')
    odometer = fields.Float(
        'Unit Odometer (mi./km)', readonly=True)
    fuel_efficiency_travel = fields.Float(
        'Fuel Efficiency Travel')
    fuel_efficiency_extraction = fields.Float(
        compute='_compute_fuel_efficiency_extraction',
        string='Fuel Efficiency Extraction')
    departure_id = fields.Many2one(
        'tms.place',
        string='Departure',
        compute='_compute_departure_id',
        store=True,
        readonly=True)
    fuel_log_ids = fields.One2many(
        'fleet.vehicle.log.fuel', 'travel_id', string='Fuel Vouchers')
    advance_ids = fields.One2many(
        'tms.advance', 'travel_id', string='Advances')
    arrival_id = fields.Many2one(
        'tms.place',
        string='Arrival',
        compute='_compute_arrival_id',
        store=True,
        readonly=True)
    notes = fields.Text(
        'Description')
    user_id = fields.Many2one(
        'res.users', 'Responsable',
        default=lambda self: self.env.user)
    expense_id = fields.Many2one(
        'tms.expense', 'Expense Record', readonly=True)
    event_ids = fields.One2many('tms.event', 'travel_id', string='Events')
    is_available = fields.Boolean(
        compute='_compute_is_available',
        string='Travel available')
    operating_unit_id = fields.Many2one('operating.unit', 'Operating Unit')
    color = fields.Integer()
    framework = fields.Selection([
        ('unit', 'Unit'),
        ('single', 'Single'),
        ('double', 'Double')],
        compute='_compute_framework')
    partner_ids = fields.Many2many(
        'res.partner', string='Customer', compute='_compute_partner_ids',
        store=True)

    @api.depends('waybill_ids')
    def _compute_partner_ids(self):
        for rec in self:
            partner_ids = []
            for waybill in rec.waybill_ids:
                partner_ids.append(waybill.partner_id.id)
            rec.partner_ids = partner_ids

    @api.depends('route_id')
    def _compute_departure_id(self):
        for rec in self:
            rec.departure_id = rec.route_id.departure_id

    @api.depends('route_id')
    def _compute_arrival_id(self):
        for rec in self:
            rec.arrival_id = rec.route_id.arrival_id

    @api.depends('fuel_efficiency_expected', 'fuel_efficiency_travel')
    def _compute_fuel_efficiency_extraction(self):
        for rec in self:
            rec.fuel_efficiency_extraction = (
                rec.fuel_efficiency_expected - rec.fuel_efficiency_travel)

    @api.depends('date_start')
    def _compute_date_end(self):
        for rec in self:
            if rec.date_start:
                strp_date = datetime.strptime(
                    rec.date_start, "%Y-%m-%d %H:%M:%S")
                rec.date_end = strp_date + timedelta(
                    hours=rec.route_id.travel_time)

    @api.depends('date_start', 'date_end')
    def _compute_travel_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                start_date = datetime.strptime(
                    rec.date_start, "%Y-%m-%d %H:%M:%S")
                end_date = datetime.strptime(rec.date_end, "%Y-%m-%d %H:%M:%S")
                difference = (end_date - start_date).total_seconds() / 60 / 60
                rec.travel_duration = difference

    @api.depends('date_start_real', 'date_end_real')
    def _compute_travel_duration_real(self):
        for rec in self:
            if rec.date_start_real and rec.date_end_real:
                start_date = datetime.strptime(
                    rec.date_start_real, "%Y-%m-%d %H:%M:%S")
                end_date = datetime.strptime(
                    rec.date_end_real, "%Y-%m-%d %H:%M:%S")
                difference = (end_date - start_date).total_seconds() / 60 / 60
                rec.travel_duration_real = difference

    @api.onchange('kit_id')
    def _onchange_kit(self):
        for rec in self:
            rec.unit_id = rec.kit_id.unit_id
            rec.trailer2_id = rec.kit_id.trailer2_id
            rec.trailer1_id = rec.kit_id.trailer1_id
            rec.dolly_id = rec.kit_id.dolly_id
            rec.employee_id = rec.kit_id.employee_id

    @api.onchange('route_id')
    def _onchange_route(self):
        self.driver_factor_ids = self.route_id.driver_factor_ids
        self.travel_duration = self.route_id.travel_time
        for rec in self:
            rec.driver_factor_ids = rec.route_id.driver_factor_ids
            rec.distance_route = rec.route_id.distance
            rec.distance_loaded = rec.route_id.distance_loaded
            rec.distance_empty = rec.route_id.distance_empty

    @api.depends('distance_empty', 'distance_loaded')
    def _compute_distance_driver(self):
        for rec in self:
            rec.distance_driver = rec.distance_empty + rec.distance_loaded

    @api.multi
    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    @api.multi
    def action_progress(self):
        for rec in self:
            rec.validate_driver_license()
            rec.validate_vehicle_insurance()
            travels = rec.search(
                [('state', '=', 'progress'), '|',
                 ('employee_id', '=', rec.employee_id.id),
                 ('unit_id', '=', rec.unit_id.id)])
            if len(travels) >= 1:
                raise ValidationError(
                    _('The unit or driver are already in use!'))
            rec.state = "progress"
            rec.date_start_real = fields.Datetime.now()
            rec.message_post('Travel Dispatched')

    @api.multi
    def action_done(self):
        for rec in self:
            odometer = self.env['fleet.vehicle.odometer'].create({
                'travel_id': rec.id,
                'vehicle_id': rec.unit_id.id,
                'last_odometer': rec.unit_id.odometer,
                'distance': rec.distance_driver,
                'current_odometer': rec.unit_id.odometer + rec.distance_driver,
                'value': rec.unit_id.odometer + rec.distance_driver
            })
            rec.state = "done"
            rec.odometer = odometer.current_odometer
            rec.date_end_real = fields.Datetime.now()
            rec.message_post('Travel Finished')

    @api.multi
    def action_cancel(self):
        for rec in self:
            advances = rec.advance_ids.search([
                ('state', '!=', 'cancel'),
                ('travel_id', '=', rec.id)])
            fuel_log = rec.fuel_log_ids.search([
                ('state', '!=', 'cancel'),
                ('travel_id', '=', rec.id)])
            if len(advances) >= 1 or len(fuel_log) >= 1:
                raise ValidationError(
                    _('If you want to cancel this travel,'
                      ' you must cancel the fuel logs or the advances '
                      'attached to this travel'))
            rec.state = "cancel"
            rec.message_post('Travel Cancelled')

    @api.model
    def create(self, values):
        travel = super(TmsTravel, self).create(values)
        sequence = travel.operating_unit_id.travel_sequence_id
        travel.name = sequence.next_by_id()
        return travel

    @api.depends()
    def _compute_is_available(self):
        for rec in self:
            objects = ['tms.advance', 'fleet.vehicle.log.fuel', 'tms.waybill']
            advances = len(rec.advance_ids)
            fuel_vehicle = len(rec.fuel_log_ids)
            count = 0
            for model in objects:
                if model == 'tms.advance' or model == 'fleet.vehicle.log.fuel':
                    object_ok = len(rec.env[model].search(
                        [('state', '=', 'confirmed'),
                         ('travel_id', '=', rec.id)]))
                    if (model == 'tms.advance' and
                            advances == object_ok or advances == 0):
                        count += 1
                    elif (model == 'fleet.vehicle.log.fuel' and
                            fuel_vehicle == object_ok or fuel_vehicle == 0):
                        count += 1
                if model == 'tms.waybill':
                    object_ok = len(rec.env[model].search(
                        [('state', '=', 'confirmed'),
                         ('travel_ids', 'in', rec.id)]))
                    if len(rec.waybill_ids) == object_ok:
                        count += 1
            if count == 3:
                rec.is_available = True

    @api.depends('route_id', 'framework')
    def _compute_fuel_efficiency_expected(self):
        for rec in self:
            res = self.env['tms.route.fuelefficiency'].search([
                ('route_id', '=', rec.route_id.id),
                ('engine_id', '=', rec.unit_id.engine_id.id),
                ('type', '=', rec.framework)
            ]).performance
            rec.fuel_efficiency_expected = res

    @api.depends('trailer1_id', 'trailer2_id')
    def _compute_framework(self):
        for rec in self:
            if rec.trailer2_id:
                rec.framework = 'double'
            elif rec.trailer1_id:
                rec.framework = 'single'
            else:
                rec.framework = 'unit'

    @api.multi
    def validate_driver_license(self):
        val = self.env['ir.config_parameter'].get_param(
            'driver_license_security_days')
        days = int(val) or 0
        for rec in self:
            if rec.employee_id.days_to_expire <= days:
                raise ValidationError(
                    _("You can not Dispatch this Travel because %s "
                      "Driver's License Validity (%s) is expired or"
                      " about to expire in next %s day(s)") % (
                        rec.employee_id.name,
                        rec.employee_id.license_expiration, val))
        return True

    @api.multi
    def validate_vehicle_insurance(self):
        val = self.env['ir.config_parameter'].get_param(
            'tms_vehicle_insurance_security_days')
        xdays = int(val) or 0
        date = datetime.now() + timedelta(days=xdays)
        for rec in self:
            units = [
                rec.unit_id, rec.trailer1_id, rec.dolly_id, rec.trailer2_id]
            for unit in units:
                if (unit and unit.insurance_expiration and
                        unit.insurance_expiration <= date.strftime(
                            '%Y-%m-%d')):
                    raise ValidationError(_(
                        "You can not Dispatch this Travel because this Vehicle"
                        "(%s) Insurance (%s) is expired or about to expire in "
                        "next %s day(s)") % (
                        rec.unit_id.name, rec.unit_id.insurance_expiration,
                        val))
