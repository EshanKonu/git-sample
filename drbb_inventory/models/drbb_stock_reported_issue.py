from odoo import api, fields, models


TAG_SELECTION = [
    ("empty", "Empty Location"),
    ("wrong_product", "Wrong Product"),
    ("wrong_stock", "Wrong Stock"),
    ("other", "Other"),
]

class DRBBStockReportedIssue(models.Model):
    _name = "drbb.stock.reported.issue"
    _description = "Reported Stock Issue"
    _rec_name = "issue_type_id"
    _order = "create_date desc, id desc"

    @api.model
    def _default_issue_type_id(self):
        """Get default Issue Type"""
        return self.env["drbb.stock.reported.issue.type"].search([], limit=1)

    product_id = fields.Many2one("product.product", string="Product", index=True, ondelete="set null")
    location_id = fields.Many2one("stock.location", string="Location", index=True, ondelete="set null")
    issue_type_id = fields.Many2one("drbb.stock.reported.issue.type", string="Issue Type", required=True, index=True, ondelete="restrict", default=_default_issue_type_id)
    state = fields.Selection(selection=[("new", "New"), ("done", "Done")], string="Status", required=True, default="new", index=True)
    batch_id = fields.Many2one("stock.picking.batch", ondelete="cascade", string="Batch")
    picking_id = fields.Many2one("stock.picking", ondelete="cascade", string="Transfer")
    remark = fields.Text(string="Remarks")

    def action_mark_done(self):
        self.write({"state": "done"})

    def action_mark_new(self):
        self.write({"state": "new"})
