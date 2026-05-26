from odoo import models
from odoo.osv import expression


class StockRequestCount(models.TransientModel):
    _inherit = 'stock.request.count'

    def _get_quants_to_count(self):
        """Checks if user has access to count all locations and company is set group_barcode_count_entire_location"""
        quants_to_count = super()._get_quants_to_count()
        if self.env.user.has_group('stock_barcode.group_barcode_count_entire_location') and self.env.company.group_barcode_count_entire_location:
            location_ids = self.quant_ids.location_id.ids
            quants_to_count = self.env['stock.quant'].search([('location_id', 'in', location_ids)])
        return quants_to_count
