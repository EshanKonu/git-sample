from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    group_barcode_count_entire_location = fields.Boolean("Count Entire Locations")

