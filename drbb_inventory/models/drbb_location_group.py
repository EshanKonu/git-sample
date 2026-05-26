from odoo import models, fields, api, _


class DRBBProductStage(models.Model):
    _name = "drbb.location.group"
    _description = "DRBB Location Group"

    name = fields.Char(string="Name", required=True)
    location_ids = fields.Many2many('stock.location','location_group_stock_location_rel',
                                    'location_group_id', 'stock_location_id',
                                    domain="[('usage', '=', 'internal')]",
                                    string='Locations')
