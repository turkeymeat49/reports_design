from odoo import api,models, fields
from odoo.exceptions import ValidationError

try:
    import qrcode
except ImportError:
    qrcode = None
import base64
import io
from num2words import num2words
from datetime import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    add_product_arabic_name = fields.Boolean("Add Product Arabic Name",default=True)    
    sh_vat = fields.Char(string="Vat",related="company_id.vat")
    sh_qr_code = fields.Text(string="QR Code new",
                             compute="generate_zatac_code")
    sh_qr_code_img = fields.Binary(string = "QR Code Image",compute = "compute_sh_qr_code_img")
    amount_move_undiscounted = fields.Float('Amount Before Discount', compute='_compute_amount_move_undiscounted', digits=0)
    amount_in_words = fields.Char(
        compute='amount_word',
        string='Amount ',
        readonly=True,
    )
    amount_in_words_ar = fields.Char(
        compute='amount_word',
        string=' Amount arabic ',
        readonly=True,
    )

          


    def _get_name_invoice_report(self):
        self.ensure_one()       
        res =  super()._get_name_invoice_report()
        return 'account.report_invoice_document'

    @api.depends('amount_total')
    def amount_word(self):
        for rec in self:
            total_amount = rec.amount_residual        
            rec.ensure_one()       
            amount_str = str('{:2f}'.format(total_amount))
            amount_str_splt = amount_str.split('.')
            before_point_value = amount_str_splt[0]
            after_point_value = amount_str_splt[1][:2]        
            before_amount_words = num2words(int(before_point_value))
            after_amount_words = num2words(int(after_point_value))
            before_amount_ar = num2words(int(before_point_value), lang="ar")
            after_amount_ar = num2words(int(after_point_value), lang="ar")
            amount = before_amount_words
            amount_ar = before_amount_ar
            amount += ' Riyal and ' + after_amount_words + ' Halalas'
            amount_ar += ' ريال و ' + after_amount_ar + ' هللة'
            rec.amount_in_words = amount.title()
            rec.amount_in_words_ar = amount_ar




    def _compute_amount_move_undiscounted(self):
        for order in self:
            total = 0.0
            for line in order.invoice_line_ids:
                total += line.price_subtotal + line.price_unit * ((line.discount or 0.0) / 100.0) * line.quantity  # why is there a discount in a field named amount_undiscounted ??
            order.amount_move_undiscounted = total

    @api.depends('amount_total', 'amount_tax', 'invoice_date', 'company_id','sh_vat')
    def generate_zatac_code(self):
        def get_qr_encoding(tag, field):
            company_name_byte_array = field.encode('UTF-8')
            company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
            company_name_length_encoding = len(
                company_name_byte_array).to_bytes(length=1, byteorder='big')
            return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

        for record in self:
            record.sh_qr_code = False
            if record.state == 'posted':
                qr_code_str = ''
                if record.invoice_date and record.sh_vat:
                    seller_name_enc = get_qr_encoding(
                        1, record.company_id.display_name)
                    company_vat_enc = get_qr_encoding(2, record.sh_vat)
                    now = datetime.now()
                    time = now.time()
                    combined = datetime.combine(record.invoice_date, time)
                    time_sa = fields.Datetime.context_timestamp(
                        self.with_context(tz='Asia/Riyadh'), combined)

                    timestamp_enc = get_qr_encoding(3, time_sa.isoformat())
                    invoice_total_enc = get_qr_encoding(
                        4, str(record.amount_total))
                    total_vat_enc = get_qr_encoding(5, str(record.amount_tax))

                    str_to_encode = seller_name_enc + company_vat_enc + timestamp_enc + invoice_total_enc + total_vat_enc
                    qr_code_str = base64.b64encode(str_to_encode).decode(
                        'UTF-8')
                record.sh_qr_code = qr_code_str

    @api.depends('sh_qr_code')
    def compute_sh_qr_code_img(self):
        for rec in self:

            rec.sh_qr_code_img = False

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
 
            qr.add_data(rec.sh_qr_code)
            qr.make(fit=True)

            img = qr.make_image()
            temp = io.BytesIO()
            img.save(temp, format="PNG")
            qr_code_image = base64.b64encode(temp.getvalue())
            rec.sh_qr_code_img = qr_code_image


    # summary

    s_subtotal = fields.Float(compute="compute_summary_totals")
    s_total_tax = fields.Float(compute="compute_summary_totals")
    s_total = fields.Float(compute="compute_summary_totals")
    s_paid = fields.Float(compute="compute_summary_totals")
    s_residual = fields.Float(compute="compute_summary_totals")

    @api.depends('line_ids')
    def compute_summary_totals(self):
        for rec in self:
            s_subtotal = 0
            s_total_tax = 0
            s_total = 0
            s_paid = 0
            s_residual = 0
            # print(rec._get_reconciled_info_JSON_values())
            if rec.amount_total < 1:
                if rec.line_ids:
                    for line in rec.line_ids:                    
                        if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                            s_total_tax += line.balance
                            s_total += line.balance
                        elif line.display_type in ('product', 'rounding'):
                            s_subtotal += line.balance
                            s_total += line.balance
                        elif line.display_type == 'payment_term':
                            s_residual += line.amount_residual
                
                if s_total < 0.5 and s_paid < 0.5 and s_residual < 0.5: 
                    if rec.payment_state in ['in_payment', 'paid']:
                        s_paid, s_subtotal, s_total = 0, 0 ,0
                        if rec.invoice_line_ids:
                            for line in rec.invoice_line_ids:
                                if line.price_total < 0:
                                    s_paid += abs(line.price_total)
                                elif line.price_total > 0:
                                    s_total += line.price_total
                                    s_subtotal += line.price_subtotal
                                    # s_paid += line.price_total

                            s_total_tax = s_total - s_subtotal                 
                            # resdiual already equal 0
                    elif rec.payment_state in ['not_paid']:
                        s_paid, s_subtotal, s_total, s_residual = 0, 0 ,0, 0
                        if rec.invoice_line_ids:
                            for line in rec.invoice_line_ids:
                                if line.price_total < 0:
                                    s_residual += abs(line.price_total)
                                elif line.price_total > 0:
                                    s_total += line.price_total
                                    s_subtotal += line.price_subtotal
                                    # s_residual += line.price_total

                            s_total_tax = s_total - s_subtotal                 
                            # paid already equal 0
                else:
                    if rec.payment_state in ['in_payment', 'paid']:
                        s_paid = abs(s_total)
                    elif rec.payment_state in ['partial']:
                        s_paid = abs(s_total) - abs(s_residual)
            else:
                s_subtotal = rec.amount_total - rec.amount_tax
                s_total_tax = rec.amount_tax
                s_total = rec.amount_total
                s_paid = rec.amount_total
                s_residual = rec.amount_residual


            rec.s_subtotal = abs(s_subtotal)
            rec.s_total_tax = abs(s_total_tax)
            rec.s_total = abs(s_total)
            rec.s_paid = abs(s_paid)
            rec.s_residual = abs(s_residual )

class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    is_advanced_payment    = fields.Boolean(default=False)
    is_retention           = fields.Boolean(default=False)
    line_tax_Amount        = fields.Float("Total Tax",compute='get_product_line_wise_tax_amount')
    taxable_amount         = fields.Float("Taxable Amount",compute="get_computable_tax")

    @api.depends('tax_ids', 'price_subtotal')
    def get_product_line_wise_tax_amount(self):
        self.line_tax_Amount = 0.0
        if self:
            for rec in self:
                if rec.price_subtotal:
                    if rec.tax_ids:
                        price = rec.price_unit * (
                            1 - (rec.discount or 0.0) / 100.0)
                        taxes = rec.tax_ids.compute_all(
                            price,
                            rec.move_id.currency_id,
                            rec.quantity,
                            product=rec.product_id)
                        line_tax = sum(
                            t.get('amount', 0.0)
                            for t in taxes.get('taxes', [])),
                        rec.line_tax_Amount = line_tax[0]
                    else:
                        rec.line_tax_Amount = 0.0
    @api.depends('price_unit','quantity')
    def get_computable_tax(self):
        for rec in self:
            rec.taxable_amount = 0.0
            if rec.price_unit and rec.quantity:
                rec.taxable_amount = rec.price_unit * rec.quantity






    



