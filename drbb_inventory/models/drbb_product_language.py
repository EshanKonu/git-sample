from odoo import fields, models, api


class DRBBProductLanguage(models.Model):
    _name = "drbb.product.language"
    _description = "Product Brand Language"

    name = fields.Char(string="Name", required=True)