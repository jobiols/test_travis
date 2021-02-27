# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# from odoo.

class OeHealthAppointment(models.Model):
    _inherit = 'oeh.medical.appointment'

    APPOINTMENT_STATUS = [
        ('Draft', 'BORRADOR'),
        ('Scheduled', 'Scheduled'),
        ('Invoiced', 'Invoiced'),
        ('Received', 'ADMITIDO'),
        ('Measuring', 'ADMITIDO-PENDIENTE DE MEDICIÓN'),
        ('Consultation', 'ADMITIDO-PENDIENTE DE CONSULTA'),
        ('Completed', 'Completed'),
        ]

    @api.onchange('appointment_end')
    @api.multi
    def _get_appointment_end(self):
        for apm in self:
            duration = 1
            if apm.appointment_date and  apm.appointment_end:
                start_date = datetime.datetime.strptime(apm.appointment_date, "%Y-%m-%d %H:%M:%S")
                end_date = datetime.datetime.strptime(apm.appointment_end, "%Y-%m-%d %H:%M:%S")
                diff = end_date - start_date
                diff_minutes = (diff.days * 24 * 60) + (diff.seconds/60)
                duration = str(datetime.timedelta(minutes= diff_minutes))
                apm.duration = duration

    def set_to_measuring(self):
        self.write({'state': 'Measuring'})

    @api.multi
    def _get_physician(self):
        """Return default physician value"""
        therapist_obj = self.env['oeh.medical.physician']
        domain = [('oeh_user_id', '=', self.env.uid)]
        user_ids = therapist_obj.search(domain, limit=1)
        if user_ids:
            return user_ids.id or False
        else:
            return False

    def set_to_consultation(self):
        self.write({'state': 'Consultation'})

    def set_to_scheduled(self):
        self.write({'state': 'Scheduled'})

    def set_to_draft(self):
        self.write({'state': 'Draft', 'check_status':1})

    def _get_additional_pratice(self):
        date = []
        for rec in self:
            if rec.appointment_lines:
                for line in rec.appointment_lines:
                    if line.additional_practice == True:
                        date.append(True)
                    else:
                        date.append(False)
                return date

    def action_appointment_invoice_create(self):
        invoice_obj = self.env["account.invoice"]
        invoice_line_obj = self.env["account.invoice.line"]
        inv_ids = []

        for acc in self:
            # Create Invoice
            if acc.patient:
                curr_invoice = {
                    'partner_id': acc.patient.partner_id.id,
                    'account_id': acc.patient.partner_id.property_account_receivable_id.id,
                    'journal_id': 53,
                    'afip_responsability_type_id':6,
                    'patient': acc.patient.id,
                    'type':'out_invoice',
                    'date_invoice':acc.appointment_date,
                    'origin': "Appointment # : " + acc.name,
                    'appointment_id': acc.id,
                }

                inv_ids = invoice_obj.create(curr_invoice)
                inv_id = inv_ids.id
                add_practice = self._get_additional_pratice()

                if inv_ids:
                    prd_account_id = self._default_account()
                    # Create Invoice line
                    if acc.appointment_lines:

                        for line in acc.appointment_lines:
                            imput = []
                            if int(line.coinsurance_price) == 0 and  int(line.social_work_price) == 0:
                                raise ValidationError('Verificar precio Coseguro o Obra social, no pueden ser cero !!')
                            elif int(line.coinsurance_price) == 0 and int(line.social_work_price) > 0:
                                continue
                            elif int(line.social_work_price) == 0and  int(line.coinsurance_price) > 0:
                                price = line.coinsurance_price
                            elif int(line.coinsurance_price) > 0 and  int(line.social_work_price) > 0:
                                price = line.coinsurance_price

                            for impu in line.reference.product_tmpl_id.taxes_id:
                                imput.append(impu.id)
                            if line.additional_practice == True:
                                curr_invoice_line = {
                                    'product_id': line.reference.product_tmpl_id.id,
                                    'name': line.name,
                                    'price_unit': price,
                                    'price_subtotal': price,
                                    'quantity': 1,
                                    'account_id': 596,
                                    'invoice_id': inv_id,
                                    'invoice_line_tax_ids': [(6,0,imput)],
                                }

                                inv_line_ids = invoice_line_obj.create(curr_invoice_line)
                                taxes_grouped = inv_ids.get_taxes_values()
                                tax_lines = inv_ids.tax_line_ids.filtered('manual')
                                for tax in taxes_grouped.values():
                                    tax_lines += tax_lines.new(tax)
                                inv_ids.tax_line_ids = tax_lines
                                add_practice.append(True)

                            elif line.additional_practice == False and  not True in add_practice:
                                curr_invoice_line = {
                                    'product_id': line.reference.product_tmpl_id.id,
                                    'name': line.name,
                                    'price_unit': price,
                                    'price_subtotal': price,
                                    'quantity': 1,
                                    'account_id': 596,
                                    'invoice_id': inv_id,
                                    'invoice_line_tax_ids': [(6,0,imput)],
                                }

                                inv_line_ids = invoice_line_obj.create(curr_invoice_line)
                                taxes_grouped = inv_ids.get_taxes_values()
                                tax_lines = inv_ids.tax_line_ids.filtered('manual')
                                for tax in taxes_grouped.values():
                                    tax_lines += tax_lines.new(tax)
                                inv_ids.tax_line_ids = tax_lines


                invoice_obj.search([('id','=',inv_id)]).action_date_assign()
                # invoice_obj.search([('id','=',inv_id)]).action_move_create()
                if  not True in add_practice:
                    self.write({'state': 'Invoiced', 'account_invoice_id':inv_ids.id })
                    view_id = self.env.ref('account.invoice_form').id
                else:
                    view_id = self.env.ref('account.invoice_form').id
        return {
            'domain': "[('id','=', " + str(inv_id) + ")]",
            'name': _('Appointment Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': inv_ids.id,
            'res_model': 'account.invoice',
            'views': [[view_id, 'form']],
            'type': 'ir.actions.act_window'
        }

    @api.depends('appointment_lines')
    @api.one
    def _additional_pratice(self):
        if self.appointment_lines:
            for line in self.appointment_lines:
                if line.additional_practice == True and self.additional_practice == False:
                    self.additional_practice = True


    check_status = fields.Integer(default=0)
    state = fields.Selection(APPOINTMENT_STATUS, string='State', readonly=True, default=lambda *a: 'Draft')
    patient = fields.Many2one('oeh.medical.patient', string='Patient', help="Patient Name", required=True, readonly=True, states={'Draft': [('readonly', False)],'Draft': [('readonly', False)]})
    appointment_date = fields.Datetime(string='Appointment Date', required=True, readonly=True,states={'Draft': [('readonly', False)],'Scheduled': [('readonly', False)]}, default=datetime.datetime.now())
    appointment_end = fields.Datetime(string='Appointment End Date', readonly=True, store=True, states={'Draft': [('readonly', False)],'Scheduled': [('readonly', False)]})
    account_invoice_id  = fields.Many2one('account.invoice', 'Factura')
    price_list_id = fields.Many2one('product.pricelist', required=True, readonly=True, states={'Draft': [('readonly', False)],'Scheduled': [('readonly', False)]})
    product_price_list = fields.One2many('product.pricelist.item', 'pricelist_id', copy=True, readonly=True, states={'Draft': [('readonly', False)],'Scheduled': [('readonly', False)]})
    duration = fields.Char(string='Duracion', store=True, readonly=True, states={'Draft': [('readonly', False)],'Scheduled': [('readonly', False)]})
    appointment_lines = fields.One2many('appointment.line', 'appointment_id', store=True, readonly=True, states={'Draft': [('readonly', False)],'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    evaluation_ids = fields.One2many('oeh.medical.evaluation', 'appointment', string='Evaluation', readonly=True, states={'Draft': [('readonly', False)],'Measuring': [('readonly', False)],'Consultation': [('readonly', False)], 'Completed': [('readonly', True)] })
    total_duration = fields.Float(string="Total Duracion", compute="_total_duration", readonly=True)
    total_coinsurance_price =  fields.Float(string="Total Coseguro", compute="_total_coinsurance_price", readonly=True)
    total_social_work_price = fields.Float(string="Total Obra Social", compute="_total_social_work_price", readonly=True)
    doctor = fields.Many2one('oeh.medical.physician', string='Physician', help="Current primary care / family doctor", domain=[('is_pharmacist','=',False)], required=True, readonly=True, states={'Consultation': [('readonly', True)],}, default=_get_physician)
    additional_practice = fields.Boolean(string="Practica adicional", default=False, index=True, compute='_additional_pratice')


    #ENFERMEDAD MEDICA PASADA

    hbv_infection_chk = fields.Boolean(string='HBV Infection', readonly=True, states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    hbv_infection_remarks = fields.Text(string='HBV Infection Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    dm_chk = fields.Boolean(string='DM', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    dm_remarks = fields.Text(string='DM Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    ihd_chk = fields.Boolean(string='IHD', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    ihd_remarks = fields.Text(string='IHD Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    cold_chk = fields.Boolean(string='Cold', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    cold_remarks = fields.Text(string='Cold Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    hypertension_chk = fields.Boolean(string='Hypertension', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    hypertension_remarks = fields.Text(string='Hypertension Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    surgery_chk = fields.Boolean(string='Surgery', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    surgery_remarks = fields.Text(string='Surgery Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    others_past_illness = fields.Text(string='Others Past Illness', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    nsaids_chk = fields.Boolean(string='Nsaids', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    nsaids_remarks = fields.Text(string='Nsaids Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    aspirin_chk = fields.Boolean(string='Aspirin', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    aspirin_remarks = fields.Text(string='Aspirin Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    laxative_chk = fields.Boolean(string='Laxative', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    laxative_remarks = fields.Text(string='Laxative Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    others_drugs = fields.Text(string='Others Drugs', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    lmp_chk = fields.Boolean(string='LMP', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    lmp_dt = fields.Date(string='Date', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    menorrhagia_chk = fields.Boolean(string='Menorrhagia', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    menorrhagia_remarks = fields.Text(string='Menorrhagia Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    dysmenorrhoea_chk = fields.Boolean(string='Dysmenorrhoea', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    dysmenorrhoea_remarks = fields.Text(string='Dysmenorrhoea Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    bleeding_pv_chk = fields.Boolean(string='Bleeding PV', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    bleeding_pv_remarks = fields.Text(string='Bleeding PV Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    last_pap_smear_chk = fields.Boolean(string='Last PAP smear', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})
    last_pap_smear_remarks = fields.Text(string='Last PAP smear Remarks', readonly=True,states={'Scheduled': [('readonly', False)], 'Consultation': [('readonly', False)]})


    @api.depends('appointment_lines.social_work_price')
    def _total_social_work_price(self):
        for order in self:
            comm_total = 0.0
            for line in order.appointment_lines:
                comm_total += line.social_work_price
            order.update({'total_social_work_price': comm_total })


    @api.depends('appointment_lines.duration')
    def _total_duration(self):
        for order in self:
            comm_total = 0.0
            for line in order.appointment_lines:
                comm_total += float(line.duration)
            order.update({'total_duration': comm_total })

    @api.depends('appointment_lines.coinsurance_price')
    def _total_coinsurance_price(self):
        for order in self:
            comm_total = 0.0
            for line in order.appointment_lines:
                comm_total += line.coinsurance_price
            order.update({'total_coinsurance_price': comm_total })

    @api.multi
    def unlink(self):
        pass
        for appointment in self.filtered(lambda appointment: appointment.state not in ['Draft']):
            pass
            # raise UserError(_('You can not delete an appointment which is not in "Draft" state !!'))
        return super(OeHealthAppointment, self).unlink()

    # def get_time_string(self,duration):
    #     result =''
    #     hours = 0
    #     if duration >= 60:
    #         currentHours = int(duration // 60)
    #         currentMinutes =int(duration % 60)
    #     else:
    #         currentHours = 0
    #         currentMinutes = duration
    #     if(currentHours <= 9):
    #         currentHours = "0" + str(currentHours)
    #     if(currentMinutes <= 9):
    #         currentMinutes = "0" + str(currentMinutes)
    #     result = str(currentHours)+":"+str(currentMinutes)
    #     return result



    @api.multi
    def write(self, vals):
        for rec in self:
            appointment_end = rec.appointment_end[:10]
            tz = pytz.timezone('America/Argentina/Buenos_Aires')
            date_now = datetime.datetime.now(tz=tz).strftime('%Y-%m-%d')

            if appointment_end < date_now:
                raise ValidationError('No se puede modificar una cita pasada')

        return super(OeHealthAppointment, self).write(vals)


class OeHealthAppointmentLine(models.Model):
    _name ="appointment.line"

    appointment_id = fields.Many2one('oeh.medical.appointment')
    reference = fields.Many2one('product.pricelist.item', string="Referencia")
    name = fields.Char(required=True, string="Nombre")
    social_work_price = fields.Float(string="Precio Obra social")
    coinsurance_price =fields.Float(string="Precio Coseguro")
    duration = fields.Char(string="Duracion")
    observation = fields.Char(string='Observacion')
    price_list_id = fields.Many2one('product.pricelist')
    additional_practice = fields.Boolean(default=False, string="Practica Adicional")
    state = fields.Selection(string="Estado", related='appointment_id.state')





    @api.onchange('reference')
    @api.multi
    def _default_value(self):
        for rec in self:
            if rec.reference:
                for line in rec.reference:
                    rec.name = line.name
                    rec.social_work_price = line.social_work_price
                    rec.coinsurance_price = line.coinsurance_price
                    rec.duration = line.duration
                    rec.observation = line.observation
                    rec.additional_practice = line.additional_practice



class ProductPriceListItem(models.Model):
    _inherit ='product.pricelist.item'

    name = fields.Char(required=True, string="Nombre")
    social_work_price = fields.Float(string="Precio Obra social")
    coinsurance_price =fields.Float(string="Precio Coseguro")
    duration = fields.Char(string="Duracion")
    observation = fields.Char(string='Observacion')
    additional_practice = fields.Boolean(default=False, string="Practica Adicional")

class OehMedicalPatient(models.Model):
    _inherit ='oeh.medical.patient'

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            if rec.main_id_number and rec.affiliate_number:
                res.append((rec.id, rec.name  + ' ' + '-' +  ' ' + rec.main_id_number + ' ' + rec.affiliate_number))
            elif rec.affiliate_number:
                res.append((rec.id, rec.name  + ' ' + '-' +  ' ' + rec.main_id_number + ' ' + rec.affiliate_number))
            else:
                res.append((rec.id, rec.name))
        return res
    @api.one
    @api.constrains('main_id_number', 'affiliate_number')
    def __check_main_id_number(self):
        main_id_number = self.env['oeh.medical.patient'].search(
            [('main_id_number', '=', self.main_id_number)]
        )
        if len(main_id_number) > 1:
            raise ValidationError('El DNI' + ' ' +  self.main_id_number + ' ' +
                                  ' ya esta asignado' + ' en el paciente ' + main_id_number[0].name)



        if self.affiliate_number:
            affiliate_number = self.env['oeh.medical.patient'].search(
                [('affiliate_number', '=', self.affiliate_number)]
            )
            if len(affiliate_number) > 1:
                raise ValidationError('El Numero de afiliado' + ' ' +  self.affiliate_number + ' ' +
                                    ' ya esta asignado' + ' en el paciente ' + affiliate_number[0].name)


    @api.model
    def create(self, values):
        if values['main_id_number']:
            main_id_number = self.env['oeh.medical.patient'].search(
                [('main_id_number', '=', values['main_id_number'])]
            )
            if len(main_id_number) > 1:
                raise ValidationError('El DNI' + ' ' +  values['main_id_number'] + ' ' +
                                    ' ya esta asignado' + ' en el paciente ' + main_id_number[0].name)

        if values['affiliate_number']:
            affiliate_number = self.env['oeh.medical.patient'].search(
                [('affiliate_number', '=', values['affiliate_number'])]
            )
            if len(affiliate_number) > 1:
                raise ValidationError('El Numero de afiliado' + ' ' +  values['affiliate_number'] + ' ' +
                                    ' ya esta asignado' + ' en el paciente ' + affiliate_number[0].name)


        result = super(OehMedicalPatient, self).create(values)
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        recs = self.search(['|','|', ('main_id_number', operator, name), ('affiliate_number', operator, name), ('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    affiliate_number = fields.Char(string='Numero de Afiliado', store=True, index=True)
