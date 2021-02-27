import datetime
from datetime import timedelta
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class OehMedicalPhysicianLine(models.Model):
    _inherit = 'oeh.medical.physician.line'


    PHY_DAY = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    @api.depends('name')
    @api.one
    def _day(self):
        try:
            if self.name:
                if self.name == 'Monday':
                    self.code_day = 1
                elif self.name == 'Tuesday':
                    self.code_day = 2
                elif self.name == 'Wednesday':
                    self.code_day = 3
                elif self.name == 'Thursday':
                    self.code_day = 4
                elif self.name == 'Friday':
                    self.code_day = 5
                elif self.name == 'Saturday':
                    self.code_day = 6
                elif self.name == 'Sunday':
                    self.code_day = 7
        except Exception as e:
            raise UserError(e)

    code_day = fields.Integer(
        string="codigo dia",
        index=True,
        compute="_day",
        readonly=True
    )
    name = fields.Selection(
        PHY_DAY,
        string='Available Day(s)',
        required=True
    )


class OehMedicalPhysician(models.Model):
    _inherit = 'oeh.medical.physician'

    app_count_referred = fields.Integer(
        compute="_compute_app_count_referred",
        string="citas Referidas"
    )
    shift_every = fields.Integer(
        string="Tiempo de cita",
        default=lambda *a: 15,
        store=True
    )

    @api.multi
    def _compute_app_count_referred(self):
        oe_apps = self.env['oeh.medical.appointment']
        for pa in self:
            domain = [('medical_referred', '=', pa.id)]
            app_ids = oe_apps.search(domain)
            apps = oe_apps.browse(app_ids)
            app_count = 0
            for ap in apps:
                app_count+=1
            pa.app_count_referred = app_count
        return True

    def _create_appointment(self, doctor_time, date_now, doctor, minute_appointment):
        start = 0
        minuts = minute_appointment

        while True:
            time_start_appoint = datetime.timedelta(hours=doctor_time.start_time)
            time_end_appoint = datetime.timedelta(hours=doctor_time.end_time)
            time_end = time_start_appoint +  timedelta(minutes=minuts)
            if start != 0:
                time_start_appoint = time_start_appoint + timedelta(minutes=start)
            else:
                time_start_appoint = time_start_appoint + timedelta(minutes=1)

            doctor_check = self.env['oeh.medical.appointment'].sudo().search([('appointment_date', '=', str(date_now) + ' ' + str((time_start_appoint + timedelta(hours=3)))),
            ('appointment_end', '=', str(date_now) + ' ' + str((time_end + timedelta(hours=3)))), ('doctor', '=', doctor)])
            if doctor_check:
                raise UserError('El doctor ya tiene una cita asignada esos dias !')

            duration = '00:' + str(minute_appointment)
            self.env['oeh.medical.appointment'].sudo().create({
                'patient':16,
                'doctor':doctor,
                'appointment_date':str(date_now) + ' ' + str((time_start_appoint + timedelta(hours=3))),
                'appointment_end':str(date_now) + ' ' + str(time_end + timedelta(hours=3)),
                'duration': duration,
            })
            if time_end >= time_end_appoint:
                minuts = minute_appointment
                break
            else:
                minuts += minute_appointment
                start +=minute_appointment

    @api.multi
    def create_appointment_doctor(self, value=None):
        try:
            date_star = None
            date_end = None
            date_now = datetime.date.today()
            if not self:
                self = value
            for line in self:
                if line.available_lines:
                    if line.walkin_schedule_lines:
                        date_star = datetime.datetime.strptime(line.walkin_schedule_lines.name, '%Y-%m-%d').date()
                        date_end = datetime.datetime.strptime(line.walkin_schedule_lines.end_date, '%Y-%m-%d').date()
                    else:
                        raise UserError(_('El medico no tiene cargado ningun dia de trabajo!'))
                if date_now <= date_star and date_now <= date_end:
                    days = -1
                    count = abs(date_now - date_end).days
                    if date_now < date_star:
                        count = abs(date_star - date_end).days
                        date_now = date_star
                    for i in range(count+1):
                        days += 1
                        date_check = date_now + timedelta(days=days)
                        week_now = date_check.weekday()
                        for doctor_time in line.available_lines:
                            if doctor_time.code_day == week_now + 1:
                                self._create_appointment(doctor_time, date_check,line.id, line.shift_every)
                                _logger.debug('que hace')

                else:
                    raise UserError(_('No se pueden crear citas para el doctor verifique la fecha de consulta'))
        except Exception as ex:
            raise UserError(ex)


    @api.one
    @api.constrains('shift_every')
    def _check_duration_appointmen(self):

        if self.shift_every < 15 or  self.shift_every > 60:
            raise ValidationError('El tiempo de la cita no puede ser menor a 15 minutos o mayor a 60 minutos!')
