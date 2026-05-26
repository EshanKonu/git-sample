from odoo import fields, models, api


class DRBBProductBrandType(models.Model):
    _name = "drbb.product.brand.type"
    _description = "Product Brand Type"

    name = fields.Char(string="Name", required=True)