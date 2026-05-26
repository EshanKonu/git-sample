from odoo import fields, models


class DRBBProductCrossSell(models.Model):
    _name = "drbb.product.cross.sell"
    _description = "Product Cross-sell"
    _order = "sequence, id"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    related_product_tmpl_id = fields.Many2one(
        "product.template",
        string="Cross-sell Product",
        required=True,
    )
    sequence = fields.Integer(default=10)
