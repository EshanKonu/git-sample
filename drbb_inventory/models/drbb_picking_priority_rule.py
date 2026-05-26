from odoo import fields, models, api
from odoo.exceptions import UserError, AccessError
from odoo.tools.translate import _


class DRBBPickingPriorityRule(models.Model):
    _name = "drbb.picking.priority.rule"
    _description = "Picking Priority Rule"
    _order = 'sequence'

    name = fields.Char(string='Picking Rule', required=True)
    description = fields.Char(string='Description')
    sequence = fields.Integer(string="Sequence")
    picking_weight = fields.Float(string="Prio Weight")
    source_sale_order = fields.Boolean(string="Source in Sales Order")
    pick_to_clean = fields.Boolean(string="Pick to Clean")
    promotion = fields.Boolean(string="Promotion")
    product_category_ids = fields.Many2many('product.category', string="Product Category(s)")

    def _get_picking_priority_rule(self, stock_move):
        for rule in self.search([]):
            if rule.source_sale_order:
                if not self._check_source_sale_order(stock_move):
                    continue
            if rule.pick_to_clean:
                if not self._check_promotion(stock_move, pick_to_clean=True):
                    continue
            if rule.promotion:
                if not self._check_promotion(stock_move, pick_to_clean=False):
                    continue
            if rule.product_category_ids:
                if stock_move.product_id.categ_id.id not in rule.product_category_ids.ids:
                    continue
            return rule
        return self.search([])[:1]

    def _check_source_sale_order(self, stock_move):
        if stock_move.sale_line_id:
            return True
        return False

    def _check_promotion(self, stock_move, pick_to_clean=False):
        if stock_move.product_id:
            programmes = self.env['loyalty.program'].search([('pick_to_clean', '=', pick_to_clean)])
            for program in programmes:
                products = program._get_valid_products(stock_move.product_id)
                for rule in program.rule_ids:
                    product = products.get(rule)
                    if product:
                        return True
        return False

    def _get_picking_priority_rule_stock_move_line(self, stock_move_line):
        for rule in self.search([]):
            if rule.source_sale_order:
                if not self._check_source_sale_order_stock_move_line(stock_move_line):
                    continue
            if rule.pick_to_clean:
                if not self._check_promotion_stock_move_line(stock_move_line, pick_to_clean=True):
                    continue
            if rule.promotion:
                if not self._check_promotion_stock_move_line(stock_move_line, pick_to_clean=False):
                    continue
            if rule.product_category_ids:
                if stock_move_line.product_id.categ_id.id not in rule.product_category_ids.ids:
                    continue
            return rule
        return self.search([])[:1]

    def _check_source_sale_order_stock_move_line(self, stock_move_line):
        if stock_move_line.move_id.sale_line_id:
            return True
        return False

    def _check_promotion_stock_move_line(self, stock_move_line, pick_to_clean=False):
        if stock_move_line.product_id:
            programmes = self.env['loyalty.program'].search([('pick_to_clean', '=', pick_to_clean)])
            for program in programmes:
                products = program._get_valid_products(stock_move_line.product_id)
                for rule in program.rule_ids:
                    product = products.get(rule)
                    if product:
                        return True
        return False





