# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    code = fields.Char(string="Code")
    name = fields.Char(
        'Name',
        index='trigram',
        required=True,
        translate=True
    )  # Override - Enable translations
