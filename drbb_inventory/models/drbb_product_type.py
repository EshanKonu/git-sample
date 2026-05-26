from odoo import fields, models


class DRBBArticleGroup(models.Model):
    _name = "drbb.article.group"
    _description = "Product Article Group"

    name = fields.Char(string="Name", required=True, translate=True)
