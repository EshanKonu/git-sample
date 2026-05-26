from odoo import fields, models


class DRBBProductCrossSellVariant(models.Model):
    _name = "drbb.product.cross.sell.variant"
    _description = "Product Cross-sell (Variant)"
    _order = "sequence, id"

    product_id = fields.Many2one(
        "product.product",
        string="Variant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    related_product_id = fields.Many2one(
        "product.product",
        string="Cross-sell Variant",
        required=True,
    )
    sequence = fields.Integer(default=10)
