from odoo import fields, models, api


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant'

    closest_circuit_location = fields.Many2one('stock.location', compute='_compute_closest_circuit_location', string="Closest Circuit Location")

    @api.depends('package_id', 'package_id.package_type_id')
    def _compute_closest_circuit_location(self):
        """Compute and assign to each stock.quant the nearest location containing "circuit", consider package’s storage category if product is not available in any circuit location"""
        for quant in self:
            if quant.package_id:
                closest_circuit_location = self.env['stock.location'].sudo()
                product_stock_quants = self.env['stock.quant'].sudo().search([('product_id', '=', quant.product_id.id)])
                for product_stock_quant in product_stock_quants:
                    complete_name = product_stock_quant.location_id.complete_name.lower()
                    if 'circuit' in complete_name and product_stock_quant.location_id:
                        closest_circuit_location = product_stock_quant.location_id
                        break
                if closest_circuit_location:
                    quant.closest_circuit_location = closest_circuit_location
                else:
                    if quant.package_id.package_type_id and quant.package_id.package_type_id.storage_category_capacity_ids:
                        storage_categories = quant.package_id.package_type_id.storage_category_capacity_ids.storage_category_id
                        for storage_category in storage_categories:
                            if 'circuit' in storage_category.name.lower():
                                location = self.env['stock.location'].sudo().search([('storage_category_id', '=', storage_category.id)], limit=1)
                                if location:
                                    closest_circuit_location = location
                                    break
                    if closest_circuit_location:
                        quant.closest_circuit_location = closest_circuit_location
                    else:
                        quant.closest_circuit_location = False
            else:
                quant.closest_circuit_location = False

    def get_stock_barcode_data_records(self):
        """Setting a condition to the barcode app"""
        res = super(StockQuantPackage, self).get_stock_barcode_data_records()
        access_group = self.env.user.has_group("stock_barcode.group_barcode_count_entire_location")
        res["count_entire_location"] = access_group and self.env.company.group_barcode_count_entire_location
        return res
