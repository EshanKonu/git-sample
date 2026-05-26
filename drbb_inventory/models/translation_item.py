from odoo import fields, models, api

class TranslationTerm(models.Model):
    _name = 'translation.term'
    _description = 'Translation Term'

    name = fields.Char(compute='_compute_name', string='Name')
    model_id = fields.Many2one('ir.model', 'Models')
    field_id = fields.Many2one('ir.model.fields', string='Fields', domain="[('model_id', '=', model_id),('translate', '=', True)]")
    res_id = fields.Char('Res ID')
    original = fields.Char('Original Translated')
    value = fields.Char('Translated Term')
    old_value = fields.Char('Old Value')
    lang_id = fields.Many2one('res.lang', 'Languages')

    def _compute_name(self):
        for rec in self:
            rec.name = rec.model_id.model + ',' + rec.field_id.name + ','+ rec.res_id

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        return res

    def write(self, vals):
        new_value = vals.get('value')
        vals.update({'old_value': new_value})
        self.update_translations(new_value)
        res = super().write(vals)
        return res

    def update_translations(self, new_value):
        for rec in self:
            model_record_id = self.env[self.model_id.model].browse(int(rec.res_id))
            fields_name = str(rec.model_id.model) +'.'+ str(rec.field_id.name)
            translations, context =\
                model_record_id.get_field_translations(rec.field_id.name)
            fr_value = {rec.lang_id.code: new_value}
            model_record_id.\
                _update_field_translations(rec.field_id.name, fr_value)

    def get_syn_value(self, res_id):
        ln_dom = []
        translationObj = self.env['translation.term'].sudo()
        modelObj = self.env['ir.model'].sudo()
        langObj = self.env['res.lang'].sudo()

        lngs = langObj.search(ln_dom)
        model_id = modelObj.search([('model', '=', res_id._name)])
        field_id = model_id.field_id.filtered(lambda x: x.name in ['name'])
        for l in lngs:
            vals = {
                'model_id': model_id.id,
                'res_id': res_id.id,
                'field_id': field_id.id,
                'original': res_id.name,
                'value': res_id.name,
                'old_value': res_id.name,
                'lang_id': l.id
            }
            translationObj.create(vals)
