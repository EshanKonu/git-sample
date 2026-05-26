from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.web.controllers.utils import clean_action


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _order = 'removal_prio DESC, name'

    package_zone_ids = fields.Many2many(comodel_name="package.zone", string="Package Zone(s)", copy=False,
                                        compute="_compute_package_zone_ids", store=True)
    volume = fields.Float(compute="_cal_volume", digits="Stock Volume", store=True, help="Total volume of the products in the picking.", compute_sudo=True)
    removal_prio = fields.Integer(string="Removal Priority", related="location_id.removal_prio", store=True)
    hide_header_footer_in_barcode = fields.Boolean(string="Hide Header & Footer in Barcode", related="picking_type_id.hide_header_footer_in_barcode", store=True)
    warn_assigned_user_in_barcode = fields.Boolean(
        string="Warn on assigned user in Barcode",
        related="picking_type_id.warn_assigned_user_in_barcode",
    )
    split_source_picking_id = fields.Many2one("stock.picking", string="Split Source Transfer", copy=False)
    show_split_transfer_action_button = fields.Boolean(compute="_compute_show_split_transfer_action_button")
    total_products_in_sale = fields.Float(string="Total Products in Sale", compute="_compute_total_products_in_sale", store=True)
    total_products_in_transfers = fields.Float(string="Total Products in Transfer", compute="_compute_total_products_in_transfers", store=True)
    stock_picking_label_ids = fields.Many2many("drbb.stock.picking.label", string="Labels")

    @api.depends("sale_id", "sale_id.order_line")
    def _compute_total_products_in_sale(self):
        """Compute products in sale order (only storable) and show the count"""
        for record in self:
            product_lines = record.sale_id.order_line.filtered(lambda x: x.product_id.type == "consu")
            record.total_products_in_sale = len(product_lines.mapped("product_id"))

    @api.depends("move_ids")
    def _compute_total_products_in_transfers(self):
        """Compute products in each picking and show the count"""
        for record in self:
            record.total_products_in_transfers = len(record.move_ids.mapped("product_id"))

    def _compute_show_split_transfer_action_button(self):
        """
        Computes whether the 'Split Transfer' action button should be shown, based on whether this picking has any
        child pickings split from it.
        """
        for record in self:
            split_pickings = self.env["stock.picking"].search([
                ("split_source_picking_id", "=", record.id)
            ])
            record.show_split_transfer_action_button = True if split_pickings else False

    @api.depends('move_ids.volume')
    def _cal_volume(self):
        """Calculate the volume"""
        for picking in self:
            picking.volume = sum(move.volume for move in picking.move_ids if move.state != 'cancel')

    @api.depends(
        'move_line_ids_without_package',
        'move_line_ids_without_package.package_id',
        'move_line_ids_without_package.package_id.package_zone_id',
        'note'
    )
    def _compute_package_zone_ids(self):
        for picking in self:
            package_zone_ids = picking.move_line_ids_without_package.filtered(
                lambda x: x.package_id and x.package_id.package_zone_id).mapped('package_id').mapped(
                'package_zone_id')
            picking.package_zone_ids = package_zone_ids

    def _put_in_specific_pack(self, move_line_ids, package):
        for pick in self:
            move_lines_to_pack = self.env['stock.move.line']

            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_is_zero(move_line_ids[0].qty_done, precision_digits=precision_digits):
                for line in move_line_ids:
                    line.qty_done = line.quantity_product_uom

            for ml in move_line_ids:
                if float_compare(ml.qty_done, ml.quantity_product_uom,
                                 precision_rounding=ml.product_uom_id.rounding) >= 0:
                    move_lines_to_pack |= ml
                else:
                    quantity_left_todo = float_round(
                        ml.quantity_product_uom - ml.qty_done,
                        precision_rounding=ml.product_uom_id.rounding,
                        rounding_method='HALF-UP')
                    done_to_keep = ml.qty_done
                    new_move_line = ml.copy(
                        default={'quantity_product_uom': 0, 'qty_done': ml.qty_done})
                    vals = {'quantity_product_uom': quantity_left_todo, 'qty_done': 0.0}
                    if pick.picking_type_id.code == 'incoming':
                        if ml.lot_id:
                            vals['lot_id'] = False
                        if ml.lot_name:
                            vals['lot_name'] = False
                    ml.write(vals)
                    new_move_line.write({'quantity_product_uom': done_to_keep})
                    move_lines_to_pack |= new_move_line
            if len(move_lines_to_pack) == 1:
                default_dest_location = move_lines_to_pack._get_default_dest_location()
                move_lines_to_pack.location_dest_id = default_dest_location._get_putaway_strategy(
                    product=move_lines_to_pack.product_id,
                    quantity=move_lines_to_pack.quantity_product_uom,
                    package=package)
            move_lines_to_pack.write({
                'result_package_id': package.id,
            })

        return package

    def _pre_put_in_pack_hook(self, move_line_ids):
        """
        Override hook before putting move lines into a package.
        Applies a custom packaging logic when the picking type is:
        - of type 'internal', and
        - the pick-pack-ship strategy is set to 'pack' or 'pick'.

        Otherwise, it falls back to the default behavior.
        :param move_line_ids: recordset of stock.move.line to be packaged
        :return: result of the custom or inherited packaging logic
        """
        # Check if the picking is of type 'internal' and requires a 'pack' operation in the pick-pack-ship flow
        if self.picking_type_id.code == "internal" and self.picking_type_id.pick_pack_ship == "pack":
            # Apply custom logic for setting the delivery package
            res = self._set_delivery_package(move_line_ids)
        # Internal picking with 'pick' step only → calls the default odoo packing
        elif self.picking_type_id.code == "internal" and self.picking_type_id.pick_pack_ship == "pick":
            res = {}
        else:
            # Fall back to the standard behavior from the parent class
            res = super(StockPicking, self)._pre_put_in_pack_hook(move_line_ids)
        return res

    def _set_delivery_package(self, move_line_ids):
        """ This method returns an action allowing to set the destination package
        on the stock.quant.package.
        """
        self.ensure_one()
        view_id = self.env.ref('drbb_inventory.choose_pack_package_view_form').id
        context = self.env.context.copy()
        context['move_line_ids'] = move_line_ids.ids

        return {
            'name': _('Package Details'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.pack.package',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': context,
        }

    def _get_fields_stock_barcode(self):
        """
        Returns the list of fields from the stock.picking model needed by the barcode client action.
        This method is intended to be overridden to extend the fields sent to the barcode interface.

        :return: List of field names required by the barcode client.
        """
        res = super()._get_fields_stock_barcode()
        res.append('hide_header_footer_in_barcode')
        res.append('warn_assigned_user_in_barcode')
        return res

    @api.model
    def filter_on_barcode(self, barcode):
        res = super(StockPicking, self).filter_on_barcode(barcode)
        if 'action' not in res:
            return res
        additional_context = {}
        action = res['action']
        user = self.env.user
        picking_type = self.env['stock.picking.type'].browse(self.env.context.get('active_id'))
        if user.package_zone_id and picking_type.filter_by_zone:
            additional_context['search_default_package_zone_ids'] = user.package_zone_id.name
        action['context'].update(additional_context)

        # Remove To DO Filter
        action['context'].pop('search_default_to_do_transfers', None)
        return {'action': action}

    def _create_shipping_labels(self):
        """
        Creates shipping labels for the current stock picking record.
        """
        tracking_ref_items = [item.strip() for item in self.carrier_tracking_ref.split(',')]
        domain = ['|'] * (len(tracking_ref_items) - 1)
        for ref in tracking_ref_items:
            domain.extend([('body', 'ilike', ref)])
        domain.extend([('model', '=', 'stock.picking'),
                       ('res_id', '=', self.id),
                       ('message_type', '=', 'notification')])

        messages_to_parse = self.env['mail.message'].search(domain, order='create_date asc')
        messages_to_parse = messages_to_parse.filtered('attachment_ids')

        # Get return shipping labels
        return_label_prefix = self.carrier_id.get_return_label_prefix()

        for i, message in enumerate(messages_to_parse):
            # Skip the message if it's a return label message
            if self._is_return_label_message(message, return_label_prefix):
                continue

            label_attachments = self._get_label_attachments(message)
            return_label_attachments = []

            next_message = messages_to_parse[i + 1] if i + 1 < len(messages_to_parse) else None
            if next_message:
                return_label_attachments = self._get_return_label_attachments(
                    next_message, return_label_prefix
                )

            shipping_label_vals = {
                'carrier_id': self.carrier_id.id,
                'picking_id': self.id,
                'tracking_numbers': self.carrier_tracking_ref,
                'label_ids': label_attachments,
                'return_label_ids': return_label_attachments,
                'label_status': 'active',
            }
            self.env['shipping.label'].create(shipping_label_vals)

    def _is_auto_batchable(self, picking=None):
        """ Verifies if a picking can be put in a batch with another picking without violating auto_batch constrains."""
        res = super()._is_auto_batchable(picking)
        if not picking:
            picking = self.env['stock.picking']
        if self.picking_type_id.batch_max_volume:
            res = res and (self.volume + picking.volume <= self.picking_type_id.batch_max_volume)
        return res

    def _check_entire_pack(self):
        """Overding a core funtion to make sure that destination package id is updated based on the condition."""
        res = super()._check_entire_pack()
        for picking in self:
            if picking.picking_type_id.force_destination_package:
                moves_without_dest_packages = picking.move_line_ids.filtered(
                    lambda ml: ml.package_id.package_use == 'disposable' and not ml.result_package_id)
                for package in moves_without_dest_packages.package_id:
                    package_moves = moves_without_dest_packages.filtered(lambda x: x.package_id == package)
                    package_moves.write({'result_package_id': package.id})
        return res

    def action_put_in_pack(self, move_lines_to_pack=False):
        """
        Handles packaging of stock move lines, customized for incoming pickings.

        For incoming pickings:
        - Automatically splits quantities using package configuration.
        - Applies packaging logic and optionally prints labels.
        - Raises an error if no items are packable.

        For other picking types:
        - Falls back to the default superclass method.

        :param move_lines_to_pack: Optional filter for move lines to pack.
        :return: Result of packaging logic or a label-printing action.
        """
        self.ensure_one()
        if self.picking_type_code == "incoming" and self.state not in ("done", "cancel"):
            # Automatically determine how to split items into packages
            move_line_ids, packages = self._set_package_quantity(move_lines_to_pack)
            if move_line_ids:
                # According to the native Odoo flow this should be sent to the "_pre_put_in_pack_hook" but
                # decide not to, since it is not necessary for a wizard popup
                if packages:
                    return self.print_package_labels(packages)
            raise UserError(
                _("There is nothing eligible to put in a pack. Either there are no quantities to put in a pack or all products are already in a pack."))
        else:
            return super().action_put_in_pack(move_lines_to_pack)

    def _set_package_quantity(self, move_lines_to_pack=False):
        """
        Auto-creates stock.quant.package records based on packaging configuration per move line.
        For each move:
            - Deletes existing move lines.
            - Splits demand quantity into packages based on packaging qty.
            - Recreates move lines accordingly.

        :param move_lines_to_pack: Optional flag to control filtering of move lines.
        :return: move_line_ids, all_packages
        """
        # prepare an empty recordset to accumulate all created packages
        all_packages = self.env['stock.quant.package'].sudo().browse([])
        move_line_ids = self._package_move_lines(move_lines_to_pack=move_lines_to_pack)
        fulfilled_move_line_ids = move_line_ids.filtered(lambda x: x.move_id.product_qty == x.qty_done)
        not_fulfilled_move_line_ids = move_line_ids.filtered(lambda x: x.move_id.product_qty != x.qty_done)
        for move_line in not_fulfilled_move_line_ids:
            all_packages |= self._put_in_pack(move_line)
        for move in fulfilled_move_line_ids.mapped("move_id"):
            # Clear existing move lines before re-packing
            move.move_line_ids.unlink()
            demand_quantity = move.product_uom_qty
            packaging = move.product_packaging_id
            package_qty = packaging.qty if packaging else demand_quantity
            package_type_id = packaging.package_type_id.id if packaging else False

            result = []
            # Generate packages until all quantity is packed
            while demand_quantity > 0:
                package_size = min(package_qty, demand_quantity)
                package = self.env['stock.quant.package'].create({
                    "package_type_id": package_type_id
                })
                result.append((0, 0, {
                    "product_id": move.product_id.id,
                    "result_package_id": package.id,
                    "quantity": package_size,
                    "picking_id": self.id,
                }))
                demand_quantity -= package_size
                all_packages |= package
            # Apply new move lines to the move
            move.write({
                "move_line_ids": result
            })

        return move_line_ids, all_packages

    def print_package_labels(self, packages):
        """Auto-print package labels in the configured format (PDF or ZPL), returning the print action if generated or the original packages otherwise."""
        if packages and self.picking_type_id.auto_print_package_label:
            if self.picking_type_id.package_label_to_print == 'pdf':
                action = self.env.ref("stock.action_report_quant_package_barcode_small").report_action(packages.ids, config=False)
            elif self.picking_type_id.package_label_to_print == 'zpl':
                action = self.env.ref("stock.label_package_template").report_action(packages.ids, config=False)
            if action:
                action.update({'close_on_report_download': True})
                clean_action(action, self.env)
                return action
        return packages

    def action_check_quality_line(self, line):
        """
        Triggers the quality check wizard for a given move line if checks are pending.

        :param line: dict with at least an 'id' key representing a stock.move.line
        :return: dict action to open the quality check wizard, or False
        """
        if not line:
            return False
        move_line = self.env["stock.move.line"].browse(line)
        if move_line.exists():
            checkable_products = move_line.product_id
            checks = self.check_ids.filtered(lambda check: check.quality_state == 'none' and (
                    check.product_id in checkable_products or check.measure_on == 'operation'))
            return checks.action_open_quality_check_wizard() if checks else False
        else:
            return False

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
            # Create a new picking
            new_picking = self.copy({
                "move_ids": [],
                "move_line_ids": [],
                "split_source_picking_id": self.id
            })
            for move_line in unpicked_move_line_ids:
                old_move_id = move_line.move_id
                # copy the move with only the remaining qty
                new_move_id = old_move_id.copy({
                    "picking_id": new_picking.id,
                    "product_uom_qty": move_line.quantity
                })
                # Reassign move line to the new picking and new move
                unpicked_move_line_ids.write({
                    "picking_id": new_picking.id,
                    "move_id": new_move_id.id,
                })
                # Adjust original move quantity
                old_move_id.product_uom_qty -= move_line.quantity
            new_picking.action_confirm()
            return {}
        raise UserError(_("There is nothing eligible to split in to another transfer."))

    def action_show_split_pickings(self):
        """
        Opens a window showing the pickings that were split from this picking.
        """
        self.ensure_one()
        return {
            "name": _("Split Transfers"),
            "res_model": "stock.picking",
            "type": "ir.actions.act_window",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("split_source_picking_id", "=", self.id)]
        }

