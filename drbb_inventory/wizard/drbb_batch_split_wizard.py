from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _name = 'drbb.batch.split.wizard'
    _description = 'Batch Split Wizard'

    max_time = fields.Float(string='Max Time (min)')
    scheduled_date = fields.Datetime(string='Scheduled Date', required=True)
    scheduled_date_part_two = fields.Datetime(string='Scheduled Date Part 2', required=True)

    def split_batch(self):
        self.ensure_one()
        batch = self.env['stock.picking.batch'].browse(self.env.context['active_id'])
        stock_moves = batch.move_ids.sorted('picking_weight')
        stock_move_ids = stock_moves.ids
        time_enough_stock_picking_ids = []
        total_picking_time = 0
        for stock_move in stock_moves:
            if stock_move.picking_id.id in time_enough_stock_picking_ids:
                continue
            else:
                stock_picking = stock_move.picking_id
                all_stock_moves = stock_moves.filtered(lambda move: move.picking_id.id == stock_picking.id)
                total_picking_time = total_picking_time + sum(all_stock_moves.mapped('picking_time'))
                if total_picking_time < self.max_time * 60:
                    time_enough_stock_picking_ids.append(stock_picking.id)

        pickings_for_new_batch = stock_moves.picking_id.filtered(lambda picking: picking.id not in time_enough_stock_picking_ids)
        company = pickings_for_new_batch.company_id
        if len(company) > 1:
            raise UserError(_("The selected pickings should belong to an unique company."))
        if len(pickings_for_new_batch.user_id) > 1:
            raise UserError(_("The selected pickings should belong to an unique Responsible Person."))
        batch = self.env['stock.picking.batch'].create({
            'user_id': pickings_for_new_batch.user_id.id,
            'company_id': company.id,
            'picking_type_id': pickings_for_new_batch[0].picking_type_id.id,
            'is_wave': batch.is_wave,
        })
        pickings_for_new_batch.write({'batch_id': batch.id})
        batch.action_confirm()





