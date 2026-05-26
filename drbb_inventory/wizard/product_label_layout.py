# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    print_format = fields.Selection(selection="_get_new_print_formats", default="zpl_discount_label")

    @api.model
    def _get_new_print_formats(self):
        """Selection values for print format."""
        selection = [("zpl_discount_label", "ZPL Discount")]
        return selection

    def _prepare_report_data(self):
        """
        Overrides the default report data preparation. If the selected print format is 'zpl_discount_label', it sets
        a custom report XML ID for generating the discount label in ZPL format.

        :return: Tuple (xml_id, data) used by the reporting engine.
        """
        xml_id, data = super()._prepare_report_data()
        if self.print_format == "zpl_discount_label":
            xml_id = "drbb_inventory.action_report_zpl_product_discount"
        return xml_id, data
