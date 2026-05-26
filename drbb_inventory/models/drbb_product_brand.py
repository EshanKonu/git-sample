from odoo import api, fields, models


class ProductBrand(models.Model):
    _name = "drbb.product.brand"
    _description = "Product Brand"
    _order = "name"

    name = fields.Char("Brand Name", required=True)