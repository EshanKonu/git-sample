from odoo import fields, models, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_dc_warehouse = fields.Boolean(default=False, string="DC Warehouse", help="Indicates whether this warehouse is designated as a distribution center (DC). If is_dc_warehouse is set to true, the system includes this warehouse’s stock levels when calculating giftlist item availability status (Green, Orange, or Red)")
    is_xxl_warehouse = fields.Boolean(default=False, string="XXL Warehouse")
