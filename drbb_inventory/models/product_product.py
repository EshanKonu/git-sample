from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    item_status_id = fields.Many2one("drbb.product.item.status", string="Item Status", tracking=True)
    item_status_char = fields.Char(related='item_status_id.name', store=True, string="Item Status Char")
    recommended_retail_price = fields.Monetary(string="RRP", help="This field contains the recommended retail price (RRP)")
    current_pricelist_price = fields.Monetary(string="Current Pricelist Price", compute="_current_pricelist_price")
    drbb_other_color_variant_ids = fields.One2many(
        "drbb.product.other.color.variant",
        "product_id",
        string="Other Colors",
    )
    drbb_cross_sell_variant_ids = fields.One2many(
        "drbb.product.cross.sell.variant",
        "product_id",
        string="Cross-sell",
    )

    def _current_pricelist_price(self):
        """Computes current pricelist price of the product"""
        pricelist = self.env['product.pricelist'].search([], limit=1)
        for product in self:
            product.current_pricelist_price = pricelist._get_product_price(product=product, quantity=1.0, uom=None)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to copy each product's recommended retail price from its template upon creation"""
        products = super().create(vals_list)
        for product in products:
            if not product.default_code:
                product.default_code = f"DB{product.id}"
            product.write({'recommended_retail_price': product.product_tmpl_id.recommended_retail_price})
        return products
