from odoo import fields, models


class ProductTranslation(models.Model):
    _name = 'product.translation'
    _description = 'Product Translation'
    _rec_name = 'product_id'
    _order = 'product_id, id desc'

    product_id = fields.Many2one('product.template')
    translation_ids = fields.One2many('product.translation.item',
                                      'product_translation_id',
                                      "Translation Lines")
