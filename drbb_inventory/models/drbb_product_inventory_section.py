from odoo import models, fields, api, _


class DRBBProductInventorySection(models.Model):
    _name = "drbb.product.inventory.section"
    _description = "DRBB Product Inventory Section"

    name = fields.Char(string="Name", required=True)
