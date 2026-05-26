from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    package_zone_id = fields.Many2one('package.zone', 'Package Zone', index=True, copy=False)
    allowed_warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        string='Allowed Warehouses',
        help='List of all warehouses user has access to',
    )
