from odoo import fields, models, api


class StockStorageCategory(models.Model):
    _inherit = "stock.storage.category"

    max_volume = fields.Float('Max Volume', help='Maximum volume shippable in this packaging')
    volume_uom_name = fields.Char(string='Weight unit', compute='_compute_volume_uom_name')

    _sql_constraints = [
        ('positive_max_volume', 'CHECK(max_volume >= 0)', 'Max volume should be a positive number.'),
    ]

    def _compute_volume_uom_name(self):
        """Returns volume name"""
        self.volume_uom_name = self.env['product.template']._get_volume_uom_name_from_ir_config_parameter()


