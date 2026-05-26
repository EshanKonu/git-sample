from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_barcode_count_entire_location = fields.Boolean("Count Entire Locations", readonly=False,
                                                         related="company_id.group_barcode_count_entire_location")

    @api.model
    def get_values(self):
        """setting value to the company"""
        res = super(ResConfigSettings, self).get_values()
        group_barcode_count_entire_location = self.env.company.group_barcode_count_entire_location
        res.update(group_barcode_count_entire_location=group_barcode_count_entire_location)
        return res

    def set_values(self):
        """getting the value from company"""
        res = super(ResConfigSettings, self).set_values()
        self.company_id.group_barcode_count_entire_location = self.group_barcode_count_entire_location
        return res
