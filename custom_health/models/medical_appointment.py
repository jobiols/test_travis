from odoo import models, fields

class OehMedicalAppointment(models.Model):
    _inherit = 'oeh.medical.appointment'

    medical_referred = fields.Many2one(
        'oeh.medical.physician',
        string='Médico Referido',
        domain=[('is_pharmacist', '=', False)],
        readonly=True,
        states={'Consultation': [('readonly', False)],
                'Completed': [('readonly', True)]}
    )
