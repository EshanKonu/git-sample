from odoo import fields, models, api
from odoo.exceptions import UserError, AccessError
from odoo.tools.translate import _
from odoo.tools.sql import column_exists, create_column


class StockMove(models.Model):
    _inherit = "stock.move"

    def _auto_init(self):
        if not column_exists(self.env.cr, "stock_move", "volume"):
            # In case of a big database with a lot of stock moves, the RAM gets exhausted
            # To prevent a process from being killed We create the column 'volume' manually
            # Then we do the computation in a query by multiplying product volume with qty
            create_column(self.env.cr, "stock_move", "volume", "numeric")
            self.env.cr.execute("""
                UPDATE stock_move move
                SET volume = move.product_qty * product.volume
                FROM product_product product
                WHERE move.product_id = product.id
                AND move.state != 'cancel'
                """)
        return super()._auto_init()

    picking_weight = fields.Float(string="Picking Prio Weight", compute='_get_picking_weight', store=True, readonly=False)
    picking_time = fields.Float(string="Picking Time (min) based on category", compute='_compute_picking_time', store=True, readonly=True)
    picking_time_location = fields.Float(string="Picking Time (min) based on location", compute='_compute_picking_time_location', store=True, readonly=True)
    forecasted_qty_in_circuit = fields.Float(string='Circuit Forecasted Quantity', compute='_compute_forecasted_qty_in_circuit' , store=True)
    volume = fields.Float(compute='_cal_move_volume', digits='Stock Volume', store=True, compute_sudo=True)
    ilp_checkbox = fields.Boolean(string="ILP Checkbox")
    product_barcode = fields.Char(string="Barcode", related="product_id.barcode")

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_volume(self):
        """Calculate the volume"""
        moves_with_volume = self.filtered(lambda moves: moves.product_id.volume > 0.00)
        for move in moves_with_volume:
            move.volume = (move.product_qty * move.product_id.volume)
        (self - moves_with_volume).volume = 0

    @api.depends('product_id', 'product_id.drbb_picking_time_category_id.picking_time', 'quantity')
    def _compute_picking_time(self):
        """ Compute the picking time for each stock move based on the associated product's picking time category"""
        for stock_move in self:
            if stock_move.product_id.drbb_picking_time_category_id:
                stock_move.picking_time = stock_move.product_id.drbb_picking_time_category_id.picking_time / 60
            else:
                stock_move.picking_time = 0

    @api.depends('move_line_ids.location_dest_id',)
    def _compute_picking_time_location(self):
        """ Compute picking_time_location based on move lines """
        for stock_move in self:
            if stock_move.move_line_ids:
                stock_move.picking_time_location = sum(stock_move.move_line_ids.mapped('picking_time_location'))
            else:
                stock_move.picking_time = 0

    @api.depends('product_id', 'quantity', 'sale_line_id')
    def _get_picking_weight(self):
        """ Compute the picking weight for each record by retrieving the applicable picking priority rule """
        for record in self:
            rule = self.env['drbb.picking.priority.rule']._get_picking_priority_rule(record)
            record.picking_weight = rule.picking_weight

    @api.depends('product_id')
    def _compute_forecasted_qty_in_circuit(self):
        """Compute the forecasted qty in circuit location"""
        for move in self:
            circuit_location = self.env['stock.location'].search([('is_circuit', '=', True)], limit=1)
            if circuit_location:
                quants = self.env['stock.quant'].search([
                    ('location_id', 'child_of', circuit_location.id),
                    ('product_id', '=', move.product_id.id)
                ])
                move.forecasted_qty_in_circuit = sum(quants.mapped('quantity'))
            else:
                move.forecasted_qty_in_circuit = 0

    def _check_cousin_location_enabled(self, move_line_id):
        """
        @private - check if the cousin location option is enabled in the operation type 
        """
        return move_line_id.picking_type_id.bc_cousin_loc_scan

    def _assign_picking_values(self, picking):
        vals = super()._assign_picking_values(picking)
        # Recompute origin from the current moves only to avoid endlessly appending
        # to the picking's source document field.
        origins = self.filtered(lambda m: m.origin).mapped("origin")
        if origins:
            origins = list(dict.fromkeys(origins))
            vals["origin"] = ",".join(origins)
        else:
            vals["origin"] = False
        return vals

    def get_cousin_locations(self, move_line_id, barcode_data):
        """
        @public - get assigned cousin locations for the assigned rule
        Check if the scanned location is a child (or equal to) any of the cousin destination locations
        from other rules in the same route.
        """
        move_line_id_val = move_line_id.get('id') if isinstance(move_line_id, dict) else move_line_id
        if not move_line_id_val:
            return False

        move_line = self.env['stock.move.line'].browse(move_line_id_val)
        # Check the picking type configuration
        if not self._check_cousin_location_enabled(move_line):
            return False
        rule = getattr(move_line.move_id, 'rule_id', None)
        route = getattr(rule, 'route_id', None)
        if not rule or not route:
            return False

        # Get all cousin destination locations (sibling rules' destination locations)
        cousin_dest_locations = route.rule_ids.filtered(lambda x: x.id != rule.id).mapped('location_dest_id')

        # Normalize target location to recordset
        target_location_data = barcode_data.get('destLocation', {})
        target_location = None
        if isinstance(target_location_data, dict) and target_location_data.get('id'):
            target_location = self.env['stock.location'].browse(target_location_data['id'])
        elif isinstance(target_location_data, int):
            target_location = self.env['stock.location'].browse(target_location_data)
        elif hasattr(target_location_data, 'id'):
            target_location = target_location_data

        if not target_location or not cousin_dest_locations:
            return False

        # Check if target_location is a child of any cousin destination location
        # The 'child_of' operator includes the location itself, so we check if the target
        # location is under any of the cousin destination locations
        for cousin_loc in cousin_dest_locations:
            if target_location._child_of(cousin_loc):
                return True
        
        return False
