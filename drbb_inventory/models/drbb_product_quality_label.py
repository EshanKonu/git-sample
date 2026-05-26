from odoo import fields, models, api


class DRBBProductQualityLabel(models.Model):
    _name = "drbb.product.quality.label"
    _description = "Product Quality Label"

    name = fields.Char(string="Name", required=True)