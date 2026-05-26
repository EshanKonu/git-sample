from odoo import fields, models, api


class DRBBProductItemType(models.Model):
    _name = "drbb.product.item.type"
    _description = "Product Item Type"

    name = fields.Char(string="Name", required=True)