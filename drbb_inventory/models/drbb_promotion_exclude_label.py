from odoo import fields, models, api


class DRBBPromotionExcludeLabel(models.Model):
    _name = "drbb.promotion.exclude.label"
    _description = "Promotion Exclude Label"

    name = fields.Char(string="Name", required=True)