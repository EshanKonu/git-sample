from odoo import fields, models, api


class StockWarehouseOrdederpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _get_orderpoint_locations(self):
        return self.env['stock.location'].search([
            ('replenish_location', '=', True),
            ('company_id', 'in', self.env.companies.ids)
        ])
