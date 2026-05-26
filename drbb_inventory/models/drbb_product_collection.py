from odoo import fields, models


class DRBBProductCollection(models.Model):
    _name = "drbb.product.collection"
    _description = "Product Collection"

    name = fields.Char(string="Name", required=True)
