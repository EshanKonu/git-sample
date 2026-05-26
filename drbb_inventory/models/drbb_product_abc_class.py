from odoo import fields, models, api


class DRBBProductABCClass(models.Model):
    _name = "drbb.product.abc.class"
    _description = "Product ABC Class"

    name = fields.Char(string="Name", required=True)