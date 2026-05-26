from odoo import fields, models, api


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    package_zone_id = fields.Many2one('package.zone', 'Package Zone', index=True, copy=False)
    move_line_ids = fields.One2many('stock.move.line', 'result_package_id', string='Move Lines in Package')
    qty_in_package = fields.Float(string="Quantity in Package", compute="_get_qty_in_package")
    source_location_barcode = fields.Char(string="Source Location Barcode", related="move_line_ids.picking_location_id.barcode")
    dest_location_barcode = fields.Char(string="Destination Location Barcode", related="move_line_ids.picking_location_dest_id.barcode")

    @api.depends("quant_ids", "quant_ids.quantity")
    def _get_qty_in_package(self):
        """Computing the total number of quantity from quant_ids"""
        for package in self:
            package.qty_in_package = sum(package.quant_ids.mapped("quantity"))

