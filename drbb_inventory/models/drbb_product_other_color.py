from odoo import fields, models


class DRBBProductOtherColor(models.Model):
    _name = "drbb.product.other.color"
    _description = "Product Other Color"
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
        string="Other Color",
        required=True,
    )
    sequence = fields.Integer(default=10)
