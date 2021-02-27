import datetime
from datetime import timedelta
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, pycompat
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class SocialWork(models.Model):
    _name = "social.work"

    code = fields.Char(
        string="Codigo"
    )
    name = fields.Char(
        string="name",
        required=True
    )
    plan_id = fields.One2many(
        'plan',
        'social_work_id',
        string="plan"
    )
    price_list_id = fields.Many2one(
        'product.pricelist',
        required=True,
        store=True,
        string="Nomenclador",
        index=True
    )


class Plan(models.Model):
    _name = "plan"

    name = fields.Char(
        string="Plan",
        required=True
    )
    social_work_id = fields.Many2one(
        'social.work',
        string="Obra social"
    )


class OeHealthAppointment(models.Model):
    _inherit = 'oeh.medical.appointment'

    social_work_id = fields.Many2one(
        'social.work',
        required=True,
        store=True,
        readonly=True,
        index=True,
        string="Obra social",
        states={'Draft': [('readonly', False)],
                'Measuring': [('readonly', False)],
                'Consultation': [('readonly', True)],
                'Completed': [('readonly', True)]},
        )
    plan_id = fields.Many2one(
        'plan',
        required=True,
        store=True,
        readonly=True,
        index=True,
        string="Plan",
        states={'Draft': [('readonly', False)],
                'Measuring': [('readonly', False)],
                'Consultation': [('readonly', True)],
                'Completed': [('readonly', True)]}
        )
    price_list_id = fields.Many2one(
        'product.pricelist',
        required=True,
        readonly=True,
        states={'Draft': [('readonly', False)],
                'Scheduled': [('readonly', False)]}
    )
    evaluation_ids = fields.One2many(
        'oeh.medical.evaluation',
        'appointment',
        string='Evaluation',
        readonly=True,
        states={'Draft': [('readonly', False)],
                'Measuring': [('readonly', False)],
                'Consultation': [('readonly', False)],
                'Completed': [('readonly', True)]}
    )

    @api.onchange('patient')
    def _update_values_pacient(self):
        if self.patient.social_work_id and self.patient.plan_id:
            self.social_work_id = self.patient.social_work_id
            self.plan_id = self.patient.plan_id.id
            self.price_list_id = self.patient.social_work_id.price_list_id.id


class OehMedicalPatient(models.Model):
    _inherit = 'oeh.medical.patient'

    social_work_id = fields.Many2one('social.work', index=True, string="Obra social")
    plan_id = fields.Many2one('plan', index=True, string="Plan")
