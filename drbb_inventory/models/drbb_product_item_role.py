from odoo import fields, models, api


class DRBBProductItemRole(models.Model):
    _name = "drbb.product.item.role"
    _description = "Product Item Role"

    name = fields.Char(string="Name", required=True)