from odoo import fields, models, api


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    drbb_stock_picking_batch_id = fields.Many2one('stock.picking.batch', readonly=True, ondelete='cascade', string='Batch')

    @api.onchange('drbb_stock_picking_batch_id')
    def _onchange_drbb_stock_picking_batch_id(self):
        if self.drbb_stock_picking_batch_id:
            self.start_datetime = self.drbb_stock_picking_batch_id.scheduled_date
            self.end_datetime = self.drbb_stock_picking_batch_id.scheduled_end_date

    def _display_name_fields(self):
        """ List of fields that can be displayed in the display_name """
        return super()._display_name_fields() + ['drbb_stock_picking_batch_id']