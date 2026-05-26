from odoo import fields, models, api
from collections import defaultdict
from odoo.osv import expression


class StockLocation(models.Model):
    _inherit = "stock.location"

    avg_picking_time = fields.Float('Average Picking Time (min)')
    net_volume = fields.Float('Net Weight', compute="_compute_volume")
    forecast_volume = fields.Float('Forecasted Weight', compute="_compute_volume")
    location_tag_ids = fields.Many2many('drbb.location.tag', string="Tags")
    partner_id = fields.Many2one('res.partner', related='warehouse_id.partner_id')
    is_circuit = fields.Boolean('Is a Circuit Location')
    is_reserve = fields.Boolean('Is a Reserve Location')
    removal_prio = fields.Integer(string='Removal Priority', default=0)

    def _check_can_be_used(self, product, quantity=0, package=None, location_qty=0):
        """Inheriting Core function to add max_volume feature"""
        return_obj = super(StockLocation, self)._check_can_be_used(product, quantity=quantity, package=package, location_qty=location_qty)
        if self.storage_category_id:
            forecast_volume = self._get_volume(self.env.context.get('exclude_sml_ids', set()))[self]['forecast_volume']
            # check if enough space
            if package and package.package_type_id:
                # check volume
                package_smls = self.env['stock.move.line'].search([('result_package_id', '=', package.id), ('state', 'not in', ['done', 'cancel'])])
                if self.storage_category_id.max_volume < forecast_volume + sum(package_smls.mapped(lambda sml: sml.quantity_product_uom * sml.product_id.volume)):
                    return False
            else:
                # check volume
                if self.storage_category_id.max_volume < forecast_volume + product.volume * quantity:
                    return False
        return return_obj

    def _get_volume(self, excluded_sml_ids=False):
        """Returns a dictionary with the net and forecasted volume of the location.
        param excluded_sml_ids: set of stock.move.line ids to exclude from the computation
        """
        result = defaultdict(lambda: defaultdict(float))
        if not excluded_sml_ids:
            excluded_sml_ids = set()
        Product = self.env['product.product']
        StockMoveLine = self.env['stock.move.line']

        quants = self.env['stock.quant'].read_group([('location_id', 'in', self.ids)], ['quantity'], ['location_id', 'product_id'], lazy=False)
        base_domain = [('state', 'not in', ['draft', 'done', 'cancel']), ('id', 'not in', tuple(excluded_sml_ids))]
        outgoing_move_lines = StockMoveLine.read_group(expression.AND([[('location_id', 'in', self.ids)], base_domain]), ['quantity_product_uom'], ['location_id', 'product_id'], lazy=False)
        incoming_move_lines = StockMoveLine.read_group(expression.AND([[('location_dest_id', 'in', self.ids)], base_domain]), ['quantity_product_uom'], ['location_dest_id', 'product_id'], lazy=False)

        product_ids = {record['product_id'][0] for record in quants + outgoing_move_lines + incoming_move_lines}
        volume_per_product = {volume['id']: volume['volume'] for volume in Product.browse(product_ids).read(['volume'])}

        for quant in quants:
            volume = quant['quantity'] * volume_per_product[quant['product_id'][0]]
            result[self.browse(quant['location_id'][0])]['net_volume'] += volume
            result[self.browse(quant['location_id'][0])]['forecast_volume'] += volume

        for line in outgoing_move_lines:
            result[self.browse(line['location_id'][0])]['forecast_volume'] -= line['quantity_product_uom'] * volume_per_product[line['product_id'][0]]

        for line in incoming_move_lines:
            result[self.browse(line['location_dest_id'][0])]['forecast_volume'] += line['quantity_product_uom'] * volume_per_product[line['product_id'][0]]

        return result

    @api.depends('outgoing_move_line_ids.quantity_product_uom', 'incoming_move_line_ids.quantity_product_uom',
                 'outgoing_move_line_ids.state', 'incoming_move_line_ids.state',
                 'outgoing_move_line_ids.product_id.volume', 'outgoing_move_line_ids.product_id.volume',
                 'quant_ids.quantity', 'quant_ids.product_id.volume')
    def _compute_volume(self):
        """Computes the volume"""
        volume_by_location = self._get_volume()
        for location in self:
            location.net_volume = volume_by_location[location]['net_volume']
            location.forecast_volume = volume_by_location[location]['forecast_volume']

    def _get_fields_stock_barcode(self):
        """
        @override - adding removal_prio to the stock barcode loading screen
        """
        return super()._get_fields_stock_barcode() + ['removal_prio']
