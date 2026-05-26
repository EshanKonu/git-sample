from odoo import fields, models


class DRBBProductOtherColorVariant(models.Model):
    _name = "drbb.product.other.color.variant"
    _description = "Product Other Color (Variant)"
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
        string="Other Color Variant",
        required=True,
    )
    sequence = fields.Integer(default=10)
