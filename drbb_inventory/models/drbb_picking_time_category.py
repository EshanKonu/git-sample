from odoo import fields, models, api
from odoo.exceptions import UserError, AccessError
from odoo.tools.translate import _


class DRBBPickingTimeCategory(models.Model):
    _name = "drbb.picking.time.category"
    _description = "Picking Time Category"

    name = fields.Char(string='Picking Time Category', required=True)
    description = fields.Char(string='Description')
    picking_time = fields.Float(string="Time (in s)")
