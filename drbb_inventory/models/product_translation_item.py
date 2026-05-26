from odoo import fields, models


class ProductTranslationItem(models.Model):
    _name = 'product.translation.item'
    _description = 'Product Translation Line'
    _rec_name = 'product_translation_id'
    _order = 'product_translation_id, id desc'

    product_translation_id = fields.Many2one('product.translation',
                                             ondelete='cascade')
    language_id = fields.Many2one('res.lang', 'Language')
    value = fields.Char("Translated Term")
    model_id = fields.Many2one('ir.model', 'Models')
    product_attrib_id = fields.Many2one('product.attribute',
                                        'Product Attributes')
    product_attrib_val_id = fields.Many2one('product.attribute.value',
                                            'Product Attribute Value')
    website_category_id = fields.Many2one('product.public.category',
                                          'eComm Category')
    pos_category_id = fields.Many2one('pos.category',
                                      'POS Category')
    sale_desc = fields.Char('Sales Description')
    web_desc = fields.Char('Web description')
    stock_out_msg = fields.Char('out-of-stock message')
