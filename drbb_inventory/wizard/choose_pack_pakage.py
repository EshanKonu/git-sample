from odoo import fields, models
from odoo.tools.float_utils import float_compare


class ChoosePackPackage(models.TransientModel):
    _name = 'choose.pack.package'
    _description = 'Delivery Package Selection Wizard'

    package_id = fields.Many2one('stock.quant.package', 'Destination Package',
                                 domain="[('package_use', '=', 'reusable')]")

    def action_put_in_pack(self):
        package = self.package_id
        move_line_ids = self.env['stock.move.line'].browse(self.env.context.get("move_line_ids"))
        picking_move_lines = move_line_ids

        move_line_ids = picking_move_lines.filtered(
            lambda ml: float_compare(
                ml.qty_done, 0.0, precision_rounding=ml.product_uom_id.rounding) > 0 and not ml.result_package_id)
        if not move_line_ids:
            move_line_ids = picking_move_lines.filtered(
                lambda ml: float_compare(
                    ml.quantity_product_uom, 0.0,
                    precision_rounding=ml.product_uom_id.rounding) > 0 and float_compare(
                    ml.qty_done, 0.0, precision_rounding=ml.product_uom_id.rounding) == 0)
        if package:
            move_line_ids.picking_id._put_in_specific_pack(move_line_ids, package)
        else:
            move_line_ids.picking_id._put_in_pack(move_line_ids)
