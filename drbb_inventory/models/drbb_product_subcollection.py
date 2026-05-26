from odoo import fields, models


class DRBBProductSubcollection(models.Model):
    _name = "drbb.product.subcollection"
    _description = "Product Subcollection"

    name = fields.Char(string="Name", required=True, translate=True)
