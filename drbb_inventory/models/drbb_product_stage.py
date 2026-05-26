from odoo import models, fields, api, _


class DRBBProductStage(models.Model):
    _name = "drbb.product.stage"
    _description = "DRBB Product Stage"
    _order = 'sequence'

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence")