from odoo import fields, models


class DRBBStockReportedIssueType(models.Model):
    _name = "drbb.stock.reported.issue.type"
    _description = "Reported Issue Type"
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer(string="Sequence", copy=False)