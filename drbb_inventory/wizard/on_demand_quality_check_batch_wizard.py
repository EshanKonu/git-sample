from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QualityCheckBatchOnDemand(models.TransientModel):
    _name = "quality.check.batch.on.demand"
    _description = "Wizard to select on-demand batch quality check points"

    batch_id = fields.Many2one("stock.picking.batch", string="Batch")
    picking_id = fields.Many2one("stock.picking", string="Picking", domain="[('id', 'in', allowed_picking_ids)]")
    product_id = fields.Many2one("product.product", string="Product", domain="[('id', 'in', allowed_product_ids)]")
    quality_point_id = fields.Many2one("quality.point", string="Quality Check Point",
                                       domain="[('id', 'in', allowed_quality_point_ids)]", required=True)
    lot_id = fields.Many2one("stock.lot", string="Lot/Serial Number",
                             help="If you want to specify a lot/serial number before the transfer validation,\
                                    create a new lot here from this field with the same exact lot name of the move line you want to add a check for.\
                                    If you want to create a check for all move lines, leave this field empty.",
                             domain="[('product_id', '=', product_id)]")
    allowed_picking_ids = fields.One2many("stock.picking", compute="_compute_allowed_picking_ids")
    allowed_product_ids = fields.One2many("product.product", compute="_compute_allowed_product_ids")
    allowed_quality_point_ids = fields.One2many("quality.point", compute="_compute_allowed_quality_point_ids")
    show_lot_number = fields.Boolean(compute="_compute_show_lot_number")
    measure_on = fields.Selection(related="quality_point_id.measure_on", readonly=True)

    @api.onchange("picking_id")
    def onchange_picking_id(self):
        """Remove selected values of product_id when picking_id is changed"""
        if self.picking_id:
            self.product_id = False

    @api.depends("batch_id")
    def _compute_allowed_picking_ids(self):
        """Computes the pickings that are linked to batch"""
        for wizard in self:
            wizard.allowed_picking_ids = wizard.batch_id.picking_ids

    @api.depends("picking_id", "picking_id.move_ids")
    def _compute_allowed_product_ids(self):
        """Computes the products that are linked to batch"""
        for wizard in self:
            wizard.allowed_product_ids = wizard.picking_id.move_ids.product_id

    @api.depends("picking_id", "product_id", "allowed_product_ids")
    def _compute_allowed_quality_point_ids(self):
        """Computes quality points that are linked to batch"""
        for wizard in self:
            domain = self.env["quality.point"]._get_domain(wizard.product_id or wizard.allowed_product_ids,
                                                           wizard.picking_id.picking_type_id, on_demand=True)
            wizard.allowed_quality_point_ids = self.env["quality.point"].search(domain)

    @api.depends("product_id", "quality_point_id")
    def _compute_show_lot_number(self):
        """Computes whether to show lot numbers"""
        for wizard in self:
            wizard.show_lot_number = wizard.quality_point_id and wizard.quality_point_id.measure_on == "move_line" and wizard.product_id and wizard.product_id.tracking != "none"

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """Remove selected values of quality_point_id when product_id is changed"""
        if self.quality_point_id not in self.allowed_quality_point_ids:
            self.quality_point_id = False

    def action_confirm(self):
        """Create QCs when confirming"""
        self.ensure_one()
        if self.picking_id and self.picking_id.state in ["draft", "done", "cancel"]:
            raise UserError(_("You can not create quality check for a draft, done or cancelled transfer."))
        self.env["quality.check"].sudo().create(self._get_check_values())

    def _get_check_values(self):
        """Creating values based on certain criterias to creat check points"""
        check_values_list = []
        check_value = {
            "point_id": self.quality_point_id.id,
            "measure_on": self.quality_point_id.measure_on,
            "team_id": self.quality_point_id.team_id.id,
            "picking_id": self.picking_id.id,
            "batch_id": self.batch_id.id,
        }
        if self.quality_point_id.measure_on != "operation":
            check_value["product_id"] = self.product_id.id
        if self.quality_point_id.measure_on == "move_line":
            if self.lot_id:
                ml = self.picking_id.move_line_ids.filtered(lambda ml: ml.product_id == self.product_id and (
                            ml.lot_name == self.lot_id.name or ml.lot_id == self.lot_id))
                if not ml:
                    raise UserError(_("The selected lot/serial number does not exist in the picking."))
                check_value["move_line_id"] = ml.id
            else:
                check_values_list = [{
                    **check_value,
                    "move_line_id": ml.id,
                } for ml in self.picking_id.move_line_ids.filtered(lambda ml: ml.product_id == self.product_id)]
        return check_values_list or [check_value]
