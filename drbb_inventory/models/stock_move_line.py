from collections import defaultdict

from odoo import fields, models, api
from odoo.osv import expression
from odoo.tools.misc import OrderedSet
from odoo.tools.float_utils import float_is_zero


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    picking_weight = fields.Float(string="Picking Prio Weight", compute='_get_picking_weight', store=True, readonly=False)
    picking_time = fields.Float(string="Picking Time (min) based on category", compute='_compute_picking_time', store=True, readonly=False)
    picking_time_location = fields.Float(string="Picking Time (min) based on location", compute='_compute_picking_time_location', store=True, readonly=False)

    @api.depends('product_id', 'product_id.drbb_picking_time_category_id.picking_time', 'quantity')
    def _compute_picking_time(self):
        """ Compute picking time based on picking time category """
        for stock_move_line in self:
            if stock_move_line.product_id.drbb_picking_time_category_id:
                stock_move_line.picking_time = stock_move_line.product_id.drbb_picking_time_category_id.picking_time / 60
            else:
                stock_move_line.picking_time = 0

    @api.depends('location_id', 'location_id.avg_picking_time')
    def _compute_picking_time_location(self):
        """ Compute picking time based on from location """
        for stock_move_line in self:
            if stock_move_line.location_id:
                stock_move_line.picking_time_location = stock_move_line.location_id.avg_picking_time
            else:
                stock_move_line.picking_time = 0

    @api.depends('product_id', 'quantity', 'move_id.sale_line_id')
    def _get_picking_weight(self):
        for record in self:
            rule = self.env['drbb.picking.priority.rule']._get_picking_priority_rule_stock_move_line(record)
            record.picking_weight = rule.picking_weight

    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + ['picking_weight'] + ['picking_time']

    def _is_auto_waveable(self):
        """Function copied from core to add a new or Condition for packages."""
        self.ensure_one()
        if not self.picking_id \
           or (self.picking_id.state != 'assigned' or float_is_zero(self.quantity, precision_rounding=self.product_uom_id.rounding)) and not self.env.context.get('skip_auto_waveable')  \
           or self.batch_id.is_wave \
           or not self.picking_type_id._is_auto_wave_grouped() \
           or (self.picking_type_id.wave_group_by_package and not self.package_id) \
           or (self.picking_type_id.wave_group_by_category and self.product_id.categ_id not in self.picking_type_id.wave_category_ids):  # noqa: SIM103
            return False
        return True

    def _auto_wave(self):
        """
        Try to find compatible waves to attach the move lines to, otherwise create new
        waves when possible/appropriate.
        """
        wave_locs_by_picking_type = {}
        for picking_type in self.picking_type_id:
            if not picking_type.wave_group_by_location and not picking_type.wave_group_by_location_group:
                continue
            if picking_type in wave_locs_by_picking_type:
                continue
            wave_locs_by_picking_type[picking_type] = set(picking_type.wave_location_ids.ids)
            if picking_type.wave_group_by_location_group:
                wave_locs_by_picking_type[picking_type] = set(picking_type.wave_location_group_ids.location_ids.ids)
        lines_nearest_parent_locations = defaultdict(lambda: self.env['stock.location'])
        batchable_line_ids = OrderedSet()
        for line in self:
            if not line._is_auto_waveable():
                continue
            if not line.picking_type_id.wave_group_by_location and not picking_type.wave_group_by_location_group:
                batchable_line_ids.add(line.id)
                continue
            # We want to find the most descendant location in the wave locations list that is a parent of the line
            # location. Since the wave locations are ordered by complete_name (from the most descendant to the most
            # ancestor), we can iterate in reverse order.
            wave_locs_set = wave_locs_by_picking_type[line.picking_type_id]
            loc = line.location_id
            while (loc):
                if loc.id in wave_locs_set:
                    lines_nearest_parent_locations[line] = loc
                    batchable_line_ids.add(line.id)
                    break
                loc = loc.location_id
        batchable_lines = self.env['stock.move.line'].browse(batchable_line_ids)

        remaining_line_ids = batchable_lines._auto_wave_lines_into_existing_waves(
            nearest_parent_locations=lines_nearest_parent_locations)
        remaining_lines = self.env['stock.move.line'].browse(remaining_line_ids)
        if remaining_lines:
            remaining_lines._auto_wave_lines_into_new_waves(nearest_parent_locations=lines_nearest_parent_locations)

    def _auto_wave_lines_into_existing_waves(self, nearest_parent_locations=False):
        """
        Try to add move lines to existing waves if possible, return move lines of which no appropriate waves were
        found to link to

        :param nearest_parent_locations (defaultdict): the key is the move line and the value is the nearest parent
        location in the wave locations list
        """
        remaining_lines = OrderedSet()
        for (picking_type, lines) in self.grouped(lambda l: l.picking_type_id).items():
            if lines:
                domain = [
                    ('picking_type_id', '=', picking_type.id),
                    ('company_id', 'in', lines.mapped('company_id').ids),
                    ('is_wave', '=', True),
                    ('state', 'in', ['draft', 'in_progress']),
                    ('move_ids.picked', '=', False),
                ]
                if picking_type.prevent_wave_addition_user == True:
                    domain = expression.AND([domain, [('user_id', '=', False)]])
                if picking_type.batch_auto_confirm:
                    domain = expression.AND([domain, [('state', 'not in', ['done', 'cancel'])]])
                else:
                    domain = expression.AND([domain, [('state', '=', 'draft')]])
                if picking_type.batch_group_by_partner:
                    domain = expression.AND([domain, [('picking_ids.partner_id', 'in', lines.move_id.partner_id.ids)]])
                if picking_type.batch_group_by_destination:
                    domain = expression.AND([domain, [
                        ('picking_ids.partner_id.country_id', 'in', lines.move_id.partner_id.country_id.ids)]])
                if picking_type.batch_group_by_src_loc:
                    domain = expression.AND([domain, [('picking_ids.location_id', 'in', lines.location_id.ids)]])
                if picking_type.batch_group_by_dest_loc:
                    domain = expression.AND(
                        [domain, [('picking_ids.location_dest_id', 'in', lines.location_dest_id.ids)]])

                potential_waves = self.env['stock.picking.batch'].search(domain)
                wave_to_new_lines = defaultdict(set)

                # These dictionaries are used to enforce batch max lines/transfers/weight limits
                # Each time a line is matched to a wave, we update the corresponding values
                wave_to_new_moves = defaultdict(set)
                waves_to_new_pickings = defaultdict(set)
                waves_new_extra_weight = defaultdict(float)
                waves_new_extra_volume = defaultdict(float)

                waves_nearest_parent_locations = defaultdict(int)
                if picking_type.wave_group_by_location:
                    valid_wave_ids = set()
                    # We want to find the most descendant location in the wave locations list that is a parent of all
                    # the lines in each wave. # We also want to exclude waves that have lines that are not in these
                    # locations.
                    for wave in potential_waves:
                        for wave_location in reversed(picking_type.wave_location_ids):
                            if all(loc._child_of(wave_location) for loc in wave.move_line_ids.location_id):
                                waves_nearest_parent_locations[wave] = wave_location.id
                                valid_wave_ids.add(wave.id)
                                break
                    potential_waves = self.env['stock.picking.batch'].browse(valid_wave_ids)

                # Add potential waves for wave_group_by_location_group
                if picking_type.wave_group_by_location_group:
                    valid_wave_ids = set()
                    # We want to find the most descendant location in the wave locations list that is a parent of all
                    # the lines in each wave. We also want to exclude waves that have lines that are not in these
                    # locations.
                    for wave in potential_waves:
                        wave_parent_locations_ids = wave.move_line_ids.location_id.location_id.ids
                        all_locations_in_group = picking_type.wave_location_group_ids.location_ids.ids
                        if wave_parent_locations_ids and set(wave_parent_locations_ids).issubset(set(all_locations_in_group)):
                            waves_nearest_parent_locations[wave] = wave.move_line_ids.location_id.location_id[0]
                            valid_wave_ids.add(wave.id)
                    potential_waves = self.env['stock.picking.batch'].browse(valid_wave_ids)

                for line in lines:
                    wave_found = False
                    for wave in potential_waves:
                        if line.company_id != wave.company_id \
                                or (
                                picking_type.batch_group_by_partner and line.move_id.partner_id != wave.picking_ids.partner_id) \
                                or (
                                picking_type.batch_group_by_destination and line.move_id.partner_id.country_id != wave.picking_ids.partner_id.country_id) \
                                or (
                                picking_type.batch_group_by_src_loc and line.location_id != wave.picking_ids.location_id) \
                                or (
                                picking_type.batch_group_by_dest_loc and line.location_dest_id != wave.picking_ids.location_dest_id) \
                                or (
                                picking_type.wave_group_by_product and line.product_id != wave.move_line_ids.product_id) \
                                or (
                                picking_type.wave_group_by_package and line.package_id != wave.move_line_ids.package_id) \
                                or (
                                picking_type.wave_group_by_category and line.product_id.categ_id != wave.move_line_ids.product_id.categ_id) \
                                or (picking_type.wave_group_by_location and waves_nearest_parent_locations[wave] !=
                                    nearest_parent_locations[line].id) \
                                or picking_type.wave_group_by_location_group:
                            if picking_type.wave_group_by_location_group:
                                wave_can_be_found = False
                                nearest_parent_location = nearest_parent_locations[line].id
                                picking_type_wave_location_groups = picking_type.wave_location_group_ids
                                for picking_type_wave_location_group in picking_type_wave_location_groups:
                                    wave_parent_locations = wave.move_line_ids.location_id.location_id
                                    if wave_parent_locations and set(wave_parent_locations.ids).issubset(
                                            set(picking_type_wave_location_group.location_ids.ids)):
                                        if nearest_parent_location in picking_type_wave_location_group.location_ids.ids:
                                            wave_can_be_found = True
                                            break
                                if not wave_can_be_found:
                                    continue
                            else:
                                continue

                        wave_new_move_ids = wave_to_new_moves[wave]
                        wave_new_picking_ids = waves_to_new_pickings[wave]
                        wave_move_ids = set(wave.move_line_ids.mapped('move_id.id'))
                        wave_picking_ids = set(wave.move_line_ids.mapped('picking_id.id'))
                        # `is_line_auto_mergeable` is a method that checks if the line can be added to the wave without
                        # exceeding the limits. It takes as arguments the number of new moves that will be added to
                        # the wave, the number of new pickings that will be added to the wave and the extra weight that
                        # will be added to the wave. So we need to check that the move/picking of the line is not
                        # already in the wave so that we don't count them as new moves/pickings.
                        if not wave._is_line_auto_mergeable(
                                line.move_id.id not in wave_move_ids and line.move_id.id not in wave_new_move_ids and len(
                                    wave_new_move_ids) + 1,
                                line.picking_id.id not in wave_picking_ids and line.picking_id.id not in wave_new_picking_ids and len(
                                    wave_new_picking_ids) + 1,
                                waves_new_extra_weight[wave] + line.product_id.weight * line.quantity_product_uom,
                                waves_new_extra_volume[wave] + line.product_id.volume * line.quantity_product_uom,
                        ):
                            continue

                        if line.move_id.id not in wave_move_ids:
                            wave_to_new_moves[wave].add(line.move_id.id)
                        if line.picking_id.id not in wave_picking_ids:
                            waves_to_new_pickings[wave].add(line.picking_id.id)
                        waves_new_extra_weight[wave] += line.product_id.weight * line.quantity_product_uom
                        waves_new_extra_volume[wave] += line.product_id.volume * line.quantity_product_uom
                        wave_to_new_lines[wave].add(line.id)
                        wave_found = True
                        break
                    if not wave_found:
                        remaining_lines.add(line.id)
                for wave, line_ids in wave_to_new_lines.items():
                    lines = self.env['stock.move.line'].browse(line_ids)
                    lines._add_to_wave(wave)
        return list(remaining_lines)

    def _auto_wave_lines_into_new_waves(self, nearest_parent_locations=False):
        """ Create new waves for the move lines that could not be added to existing waves. """
        picking_types = self.picking_type_id
        for picking_type in picking_types:
            lines = self.filtered(lambda l: l.picking_type_id == picking_type)
            domain = [
                ('id', 'in', lines.ids),
                ('company_id', 'in', self.company_id.ids),
                ('picking_id.state', '=', 'assigned'),
                ('picking_type_id', '=', picking_type.id),
                '|',
                ('batch_id', '=', False),
                ('batch_id.is_wave', '=', False)
            ]
            if picking_type.batch_group_by_partner:
                domain = expression.AND([domain, [('move_id.partner_id', 'in', lines.move_id.partner_id.ids)]])
            if picking_type.batch_group_by_destination:
                domain = expression.AND(
                    [domain, [('move_id.partner_id.country_id', 'in', lines.move_id.partner_id.country_id.ids)]])
            if picking_type.batch_group_by_src_loc:
                domain = expression.AND([domain, [('location_id', 'in', lines.location_id.ids)]])
            if picking_type.batch_group_by_dest_loc:
                domain = expression.AND([domain, [('location_dest_id', 'in', lines.location_dest_id.ids)]])
            if picking_type.wave_group_by_product:
                domain = expression.AND([domain, [('product_id', 'in', lines.product_id.ids)]])
            if picking_type.wave_group_by_package and lines.package_id.ids:
                domain = expression.AND([domain, [('package_id', 'in', lines.package_id.ids)]])
            if picking_type.wave_group_by_category:
                domain = expression.AND([domain, [('product_id.categ_id', 'in', lines.product_id.categ_id.ids)]])
            if picking_type.wave_group_by_location:
                domain = expression.AND([domain, [('location_id', 'child_of', picking_type.wave_location_ids.ids)]])
            if picking_type.wave_group_by_location_group:
                domain = expression.AND(
                    [domain, [('location_id', 'child_of', picking_type.wave_location_group_ids.location_ids.ids)]])

            potential_lines = self.env['stock.move.line'].search(domain)
            lines_nearest_parent_locations = defaultdict(int)
            if picking_type.wave_group_by_location:
                for line in potential_lines:
                    for location in reversed(picking_type.wave_location_ids):
                        if line.location_id._child_of(location):
                            lines_nearest_parent_locations[line] = location.id
                            break
            if picking_type.wave_group_by_location_group:
                for line in potential_lines:
                    for location_group in picking_type.wave_location_group_ids:
                        if line.location_id.location_id.id in location_group.location_ids.ids:
                            lines_nearest_parent_locations[line] = location_group.location_ids[0].id
            line_to_lines = defaultdict(set)
            matched_lines = set()
            remaining_line_ids = OrderedSet()
            for line in lines:
                lines_found = False
                if line.id in matched_lines:
                    continue
                for potential_line in potential_lines:
                    if line.id == potential_line.id \
                            or line.company_id != potential_line.company_id \
                            or (
                            picking_type.batch_group_by_partner and line.move_id.partner_id != potential_line.move_id.partner_id) \
                            or (
                            picking_type.batch_group_by_destination and line.move_id.partner_id.country_id != potential_line.move_id.partner_id.country_id) \
                            or (picking_type.batch_group_by_src_loc and line.location_id != potential_line.location_id) \
                            or (
                            picking_type.batch_group_by_dest_loc and line.location_dest_id != potential_line.location_dest_id) \
                            or (picking_type.wave_group_by_product and line.product_id != potential_line.product_id) \
                            or (picking_type.wave_group_by_package and line.package_id != potential_line.package_id) \
                            or (
                            picking_type.wave_group_by_category and line.product_id.categ_id != potential_line.product_id.categ_id) \
                            or (
                            picking_type.wave_group_by_location and lines_nearest_parent_locations[potential_line] !=
                            nearest_parent_locations[line].id) \
                            or (picking_type.wave_group_by_location_group and lines_nearest_parent_locations[potential_line] != nearest_parent_locations[line].id):
                        continue

                    line_to_lines[line].add(potential_line.id)
                    matched_lines.add(potential_line.id)
                    lines_found = True
                if not lines_found:
                    remaining_line_ids.add(line.id)

            for line, potential_line_ids in line_to_lines.items():
                if line.batch_id.is_wave:
                    continue

                potential_lines = self.env['stock.move.line'].browse(potential_line_ids | {line.id})

                # We want to make sure that batch/wave limits specified in the picking type are respected.
                # We want also to reduce picking splits as much as possible. So we try to group as much as
                # possible by sorting the lines by picking and move.
                potential_lines = potential_lines.sorted(key=lambda l: (l.picking_id.id, l.move_id.id))

                while potential_lines:
                    new_wave = self.env['stock.picking.batch'].create({
                        'is_wave': True,
                        'picking_type_id': picking_type.id,
                        'description': line._get_auto_wave_description(nearest_parent_locations[line]),
                    })
                    wave_move_ids = set()
                    wave_picking_ids = set()
                    wave_weight = 0
                    wave_volume = 0

                    wave_line_ids = set()

                    for potential_line in potential_lines:
                        if potential_line.batch_id.is_wave:
                            continue
                        wave_move_ids.add(potential_line.move_id.id)
                        wave_picking_ids.add(potential_line.picking_id.id)
                        wave_weight += potential_line.product_id.weight * potential_line.quantity_product_uom
                        wave_volume += potential_line.product_id.volume * potential_line.quantity_product_uom
                        if new_wave._is_line_auto_mergeable(
                                len(wave_move_ids),
                                len(wave_picking_ids),
                                wave_weight,
                                wave_volume
                        ):
                            wave_line_ids.add(potential_line.id)
                        else:
                            break
                    wave_lines = self.env['stock.move.line'].browse(wave_line_ids)
                    wave_lines._add_to_wave(new_wave)
                    potential_lines -= wave_lines

            remaining_lines = self.env['stock.move.line'].browse(remaining_line_ids)
            remaining_waves = self.env['stock.picking.batch'].create([{
                'is_wave': True,
                'picking_type_id': picking_type.id,
                'description': remaining_line._get_auto_wave_description(nearest_parent_locations[remaining_line]),
            } for remaining_line in remaining_lines])
            for (line, wave) in zip(remaining_lines, remaining_waves):
                line._add_to_wave(wave)

    def _get_auto_wave_description(self, nearest_parent_location=False):
        """Generates the description for the wave"""
        self.ensure_one()
        description = super()._get_auto_wave_description(nearest_parent_location)
        if self.picking_type_id.wave_group_by_location_group:
            if nearest_parent_location and nearest_parent_location.complete_name not in description:
                description = f"{description}, {nearest_parent_location.complete_name}" if description else nearest_parent_location.complete_name
        if self.picking_type_id.wave_group_by_package:
            description = "%s - %s" % (str(self.picking_type_id.barcode), str(self.product_id.display_name))
        return description

    def check_record_exist(self):
        """Function to check whether if the record exist or not."""
        return True if self.exists() else False
