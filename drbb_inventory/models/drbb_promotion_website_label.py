from odoo import fields, models, api


class DRBBPromotionWebsiteLabel(models.Model):
    _name = "drbb.promotion.website.label"
    _description = "Promotion Website Label"

    name = fields.Char(string="Name", required=True, translate=True)
