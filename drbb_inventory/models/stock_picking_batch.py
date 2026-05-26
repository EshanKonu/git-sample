from datetime import timedelta
from collections import defaultdict
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

from odoo.addons.resource.models.utils import Intervals, sum_intervals, string_to_datetime
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"
    _order = "priority desc, name desc"

    scheduled_end_date = fields.Datetime(string='Scheduled End Date', compute='_compute_scheduled_end_date')
    estimated_picking_time = fields.Float(string="Estimated Picking Time (min) based on category",
                                          compute='_compute_estimated_picking_time', store=True)
    estimated_picking_time_location = fields.Float(string="Estimated Picking Time (min) based on location",
                                                   compute='_compute_estimated_picking_time_location', store=True)
    product_ids = fields.Many2many(comodel_name='product.product', compute='_compute_product_ids', store=True)
    hide_header_footer_in_barcode = fields.Boolean(string="Hide Header & Footer in Barcode", related="picking_type_id.hide_header_footer_in_barcode", store=True)
    warn_assigned_user_in_barcode = fields.Boolean(string="Warn on assigned user in Barcode", related="picking_type_id.warn_assigned_user_in_barcode")
    split_source_picking_batch_id = fields.Many2one("stock.picking.batch", string="Split Source Batch Picking", copy=False)
    show_split_batch_transfer_action_button = fields.Boolean(compute="_compute_show_split_batch_transfer_action_button")
    product_id = fields.Many2one('product.product', 'Product', related='picking_ids.move_ids.product_id', readonly=True)
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number', related='picking_ids.move_line_ids.lot_id', readonly=True)
    bypass_state_sanity_check = fields.Boolean(
        string="Bypass State Sanity Check",
        tracking=True,
        help="If enabled, the batch sanity check will ignore picking state restrictions.\n"
             "Company and Operation Type consistency are still enforced."
    )
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES,
        string="Priority",
        compute="_compute_priority",
        inverse="_inverse_priority",
        readonly=False,
        store=True,
        help="Batches and waves with higher priority are shown first.",
    )

    @api.depends('picking_ids', 'picking_ids.priority', 'picking_ids.sale_id')
    def _compute_priority(self):
        """Autofill batch/wave priority from linked transfers.

        - urgent if any transfer is urgent OR linked to a sales order
        - normal otherwise
        """
        for batch in self:
            if any(picking.priority == '1' or picking.sale_id for picking in batch.picking_ids):
                batch.priority = '1'
            else:
                batch.priority = '0'

    def _inverse_priority(self):
        """Allow manual edits in the UI; value is recomputed when dependencies change."""
        # Intentionally empty.
        return

    def _compute_show_split_batch_transfer_action_button(self):
        """
        Computes whether the 'Split Batch Transfer' action button should be shown, based on whether this picking has any
        child pickings split from it.
        """
        for record in self:
            split_batch_pickings = self.env["stock.picking.batch"].search([
                ("split_source_picking_batch_id", "=", record.id)
            ])
            record.show_split_batch_transfer_action_button = True if split_batch_pickings else False

    @api.depends('move_ids')
    def _compute_product_ids(self):
        """ Calculates products for batch picking to update picking time when the product's picking time category
        changes """
        for rec in self:
            if rec.move_line_ids:
                products = self.env['product.product'].sudo()
                for line in rec.move_line_ids:
                    products |= line.product_id
                rec.product_ids = products
            else:
                rec.product_ids = False

    @api.depends('product_ids', 'product_ids.drbb_picking_time_category_id.picking_time')
    def _compute_estimated_picking_time(self):
        for stock_picking_batch in self:
            if stock_picking_batch.move_ids:
                stock_picking_batch.estimated_picking_time = sum(stock_picking_batch.move_ids.mapped('picking_time'))
            else:
                stock_picking_batch.estimated_picking_time = 0

    @api.depends('move_line_ids', 'move_line_ids.picking_time_location')
    def _compute_estimated_picking_time_location(self):
        """ Compute estimated picking time based on destination """
        for stock_picking_batch in self:
            if stock_picking_batch.move_line_ids:
                stock_picking_batch.estimated_picking_time_location = sum(
                    stock_picking_batch.move_line_ids.mapped('picking_time_location'))
            else:
                stock_picking_batch.estimated_picking_time_location = 0

    @api.depends('move_ids', 'scheduled_date')
    def _compute_scheduled_end_date(self):
        for stock_picking_batch in self:
            if stock_picking_batch.scheduled_date:
                stock_picking_batch.scheduled_end_date = stock_picking_batch.scheduled_date + timedelta(
                    seconds=stock_picking_batch.estimated_picking_time * 60)
            else:
                stock_picking_batch.scheduled_end_date = False

    def _get_scheduled_end_date(self):
        self.ensure_one()
        if self.scheduled_date:
            estimated_picking_time_in_seconds = sum(self.move_ids.mapped('picking_time'))
            scheduled_end_date = self.scheduled_date + timedelta(
                seconds=estimated_picking_time_in_seconds)
        else:
            scheduled_end_date = False
        return scheduled_end_date

    # def unlink(self):
    #     for batch in self:
    #         if batch.drbb_planning_slot_id:
    #             batch.drbb_planning_slot_id.unlink()
    #     return super().unlink()

    def open_split_batch_wave(self):
        view = self.env.ref('drbb_inventory.drbb_batch_split_wizard_view_form')
        return {
            'name': _('Batch Split'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'drbb.batch.split.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': {
                'default_scheduled_date': self.scheduled_date,
                'default_scheduled_date_part_two': self.scheduled_date + timedelta(days=1),
            },
        }

    def _gantt_progress_bar_user_id(self, res_ids, start, stop):
        res_users = self.env['res.users'].browse(res_ids)

        # Implement resource time calculation logic
        start_naive, stop_naive = start.replace(tzinfo=None), stop.replace(tzinfo=None)

        resources = self.env['resource.resource'].with_context(active_test=False).search(
            [('id', 'in', res_users.employee_id.resource_id.ids)])
        planning_slots = self.env['planning.slot'].search([
            ('resource_id', 'in', res_users.employee_id.resource_id.ids),
            ('start_datetime', '<=', stop_naive),
            ('end_datetime', '>=', start_naive),
        ])
        planned_hours_mapped = defaultdict(float)
        resource_work_intervals, calendar_work_intervals = resources.sudo()._get_valid_work_intervals(start, stop)
        for slot in planning_slots:
            planned_hours_mapped[slot.resource_id.id] += slot._get_duration_over_period(
                start, stop, resource_work_intervals, calendar_work_intervals
            )
        # Compute employee work hours based on its work intervals.
        work_hours = {
            resource_id: sum_intervals(work_intervals)
            for resource_id, work_intervals in resource_work_intervals.items()
        }

        values = {}
        for res_user in res_users:
            resource = res_user.employee_id.resource_id
            values[res_user.id] = {
                'is_material_resource': resource.resource_type == 'material',
                'resource_color': resource.color,
                'value': planned_hours_mapped[resource.id],
                'max_value': work_hours.get(resource.id, 0.0),
                'employee_id': resource.employee_id.id,
                'employee_model': 'hr.employee' if self.env.user.has_group(
                    'hr.group_hr_user') else 'hr.employee.public',
                'remaining_time': round((work_hours.get(resource.id, 0.0) - planned_hours_mapped[resource.id]) * 60, 2),
            }
        return values

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'user_id':
            start, stop = pytz.utc.localize(start), pytz.utc.localize(stop)
            return dict(
                self._gantt_progress_bar_user_id(res_ids, start, stop),
                warning=_("As there is no running contract during this period, this resource is not expected to work a shift. Planned hours:")
            )
        raise NotImplementedError(_("This Progress Bar is not implemented."))

    @api.model
    def _get_fields_stock_barcode(self):
        """
        Returns the list of fields from the stock.picking.batch model needed by the barcode client action.
        This method is intended to be overridden to extend the fields sent to the barcode interface.

        :return: List of field names required by the barcode client.
        """
        res = super()._get_fields_stock_barcode()
        res.append('priority')
        res.append('hide_header_footer_in_barcode')
        res.append('warn_assigned_user_in_barcode')
        return res

    def _sanity_check(self):
        """
        Default behavior: ensure batch.picking_ids is a subset of batch.allowed_picking_ids
        (which includes allowed picking states).

        When bypass_state_sanity_check is enabled:
        - still enforce company consistency
        - still enforce picking_type_id consistency (if set on the batch)
        - do NOT enforce allowed state restrictions
        """
        forced = self.filtered("bypass_state_sanity_check")
        normal = self - forced

        if normal:
            super(StockPickingBatch, normal)._sanity_check()

        for batch in forced:
            if not batch.picking_ids:
                continue

            wrong_company = batch.picking_ids.filtered(lambda p: p.company_id != batch.company_id)
            if wrong_company:
                raise UserError(_(
                    "You cannot bypass the batch sanity check to mix companies.\n\n"
                    "Incompatible transfers: %s",
                    ", ".join(wrong_company.mapped("name")),
                ))

            if batch.picking_type_id:
                wrong_type = batch.picking_ids.filtered(lambda p: p.picking_type_id != batch.picking_type_id)
                if wrong_type:
                    raise UserError(_(
                        "You cannot bypass the batch sanity check to mix operation types.\n\n"
                        "Incompatible transfers: %s",
                        ", ".join(wrong_type.mapped("name")),
                    ))
        if forced:
            self.message_post(
                body=_(
                    "Batch was validated with <b>Bypass State Sanity Check</b> enabled by %(user)s. Source - %(batch)s",
                    user=self.env.user.display_name, batch=self.display_name
                )
            )
        return

    @api.model
    def gantt_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        if not self.user_has_groups("base.group_user"):
            return {field: {} for field in fields}

        start_utc, stop_utc = string_to_datetime(date_start_str), string_to_datetime(date_stop_str)

        progress_bars = {}
        for field in fields:
            progress_bars[field] = self._gantt_progress_bar(field, res_ids[field], start_utc, stop_utc)

        return progress_bars

    def _is_picking_auto_mergeable(self, picking):
        """ Verifies if a picking can be safely inserted into the batch without violating auto_batch_constrains.
        """
        res = super()._is_picking_auto_mergeable(picking)
        if self.picking_type_id.batch_max_volume:
            batch_volume = sum(self.picking_ids.mapped('volume'))
            res = res and (batch_volume + picking.volume <= self.picking_type_id.batch_max_volume)
        return res

    def _is_line_auto_mergeable(self, num_of_moves=False, num_of_pickings=False, weight=False, volume=False):
        res = super()._is_line_auto_mergeable(num_of_moves, num_of_pickings, weight)
        if self.picking_type_id.batch_max_volume:
            wave_volume = sum(self.move_ids.mapped('volume'))
            res = res and (wave_volume + volume <= self.picking_type_id.batch_max_volume)
        return res

    def action_split_batch(self):
        """
        Splits unpicked move lines into a new picking. Requires at least one picked line to proceed.
        """
        self.ensure_one()
        unpacked_quantity_move_line_ids = self.move_line_ids.filtered(lambda ml: float_compare(ml.quantity, 0.0, precision_rounding=ml.product_uom_id.rounding) > 0 and not ml.result_package_id)
        packed_quantity_move_line_ids = self.move_line_ids.filtered(lambda ml: float_compare(ml.quantity, 0.0, precision_rounding=ml.product_uom_id.rounding) > 0 and ml.result_package_id)
        picked_move_line_ids = unpacked_quantity_move_line_ids.filtered(lambda ml: ml.picked)
        if not picked_move_line_ids and not packed_quantity_move_line_ids:
            raise UserError(_("You need to at least put in pack one item."))
        unpicked_move_line_ids = unpacked_quantity_move_line_ids.filtered(lambda ml: not ml.picked)
        if unpicked_move_line_ids:
            new_picking_batch = self.copy({
                "move_ids": [],
                "move_line_ids": [],
                "picking_ids": [],
                "split_source_picking_batch_id": self.id
            })
            for picking in unpicked_move_line_ids.mapped("picking_id"):
                new_picking = picking.copy({
                    "move_ids": [],
                    "move_line_ids": [],
                    "split_source_picking_id": picking.id,
                    "batch_id": new_picking_batch.id
                })
                for move_line in unpicked_move_line_ids.filtered(lambda x: x.picking_id == picking):
                    old_move_id = move_line.move_id
                    # copy the move with only the remaining qty
                    new_move_id = old_move_id.copy({
                        "picking_id": new_picking.id,
                        "product_uom_qty": move_line.quantity
                    })
                    # Reassign move line to the new picking and new move
                    move_line.write({
                        "picking_id": new_picking.id,
                        "move_id": new_move_id.id,
                    })
                    # Adjust original move quantity
                    old_move_id.product_uom_qty -= move_line.quantity
            new_picking_batch.action_confirm()
            return {}
        raise UserError(_("There is nothing eligible to split in to another transfer."))

    def action_show_split_batch_pickings(self):
        """
        Opens a window showing the pickings that were split from this picking.
        """
        self.ensure_one()
        return {
            "name": _("Split Batch Pickings"),
            "res_model": "stock.picking.batch",
            "type": "ir.actions.act_window",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("split_source_picking_batch_id", "=", self.id)]
        }

    def action_check_quality_line(self, line):
        """
        Triggers the quality check wizard for a given stock move line if any pending checks exist.

        :param line: dict with an 'id' key referring to a stock.move.line
        :return: action dict to open quality check wizard or False
        """
        if not line:
            return False
        move_line = self.env["stock.move.line"].browse(int(line))
        if move_line.exists():
            checkable_products = move_line.product_id
            checks = move_line.picking_id.check_ids.filtered(lambda check: check.quality_state == 'none' and (
                    check.product_id in checkable_products or check.measure_on == 'operation'))
            return checks.action_open_quality_check_wizard() if checks else False
        else:
            return False

    def action_report_picking_all_batches_transfers(self):
        self.ensure_one()
        return self.env.ref('drbb_inventory.action_report_picking_batch').report_action(self)

    def action_open_on_demand_quality_check(self):
        """Returns a wizard to initiate QC"""
        self.ensure_one()
        if self.state in ['draft', 'done', 'cancel']:
            raise UserError(_('You can not create quality check for a draft, done or cancelled transfer.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('On-Demand Quality Check'),
            'res_model': 'quality.check.batch.on.demand',
            'views': [(self.env.ref('drbb_inventory.quality_check_batch_on_demand_view_form').id, 'form')],
            'target': 'new',
            'context': {
                'default_batch_id': self.id,
                'on_demand_wizard': True,
            }
        }

    def _compute_estimated_shipping_capacity(self):
        """ToDO - This is function that was copied from Odoo as there is a bug in odoo source code as it was not fixed
        till now 22/08/2025. The issue is that it uses self instead of batch in the for loop line."""
        for batch in self:
            estimated_shipping_weight = 0
            estimated_shipping_volume = 0
            # packs
            for pack in batch.move_line_ids.result_package_id:
                p_type = pack.package_type_id
                estimated_shipping_weight += pack.shipping_weight
                if p_type:
                    estimated_shipping_weight += p_type.base_weight or 0
                    estimated_shipping_volume += (p_type.packaging_length * p_type.width * p_type.height) / 1000.0**3
            # move without packs
            for move in batch.picking_ids.move_ids_without_package:
                estimated_shipping_weight += move.product_id.weight * move.product_qty
                estimated_shipping_volume += move.product_id.volume * move.product_qty
            batch.estimated_shipping_weight = estimated_shipping_weight
            batch.estimated_shipping_volume = estimated_shipping_volume
