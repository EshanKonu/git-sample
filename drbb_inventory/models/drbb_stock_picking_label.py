from odoo import fields, models, api


class DRBBStockPickingLabel(models.Model):
    _name = "drbb.stock.picking.label"
    _description = "Stock Picking Label"

    name = fields.Char(string="Name", required=True)