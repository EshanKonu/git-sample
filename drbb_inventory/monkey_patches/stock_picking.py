
from odoo import models
from odoo.tools.float_utils import float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _create_backorder(self, backorder_moves=None):
        """ Replace quality_control _create_backorder function.
        Original: odoo/addons/quality_control/models/stock_picking.py
        """
        res = super(StockPicking, self)._create_backorder(backorder_moves=backorder_moves)
        if self.env.context.get('skip_check'):
            return res
        for backorder in res:
            # Do not link the QC of move lines with quantity of 0 in backorder.
            backorder.move_line_ids.filtered(lambda ml: not float_is_zero(ml.quantity, precision_rounding=ml.product_uom_id.rounding)).check_ids.picking_id = backorder
            backorder.backorder_id.check_ids.filtered(lambda qc: qc.quality_state == 'none').sudo().unlink()
            if backorder.backorder_id.state in ('done', 'cancel'):
                backorder.backorder_id.check_ids.filtered(lambda qc: qc.quality_state == 'none').sudo().unlink()
            backorder.move_ids._create_quality_checks()
        return res
