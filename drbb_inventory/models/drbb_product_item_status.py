from odoo import fields, models, api


class DRBBProductItemStatus(models.Model):
    _name = "drbb.product.item.status"
    _description = "Product Item Status"

    name = fields.Char(string="Name", required=True)