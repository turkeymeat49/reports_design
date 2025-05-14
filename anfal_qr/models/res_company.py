# -*- coding: utf-8 -*-
from odoo import api,models, fields

class ResCompany(models.Model):
    _inherit        = 'res.company'

    sh_name         = fields.Char(string='Saudi Company Name', store=True, readonly=False)
    sh_street       = fields.Char()
    sh_street2      = fields.Char()
    sh_zip          = fields.Char()
    sh_city         = fields.Char()
    sh_state_id     = fields.Char()
    sh_country_id   = fields.Char()
    additional_no   = fields.Char("Additional No")
    other_seller_id = fields.Char("Other Seller Id")

    
    building_no     = fields.Char()
    district        = fields.Char()