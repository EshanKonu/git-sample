from odoo import fields, models, api, _
import re

Model_List = [
        'product.template', 'product.attribute',
        'product.attribute.value', 'product.public.category',
        'pos.category',
    ]


class BaseLanguageInstall(models.TransientModel):
    _inherit = "base.language.install"

    def lang_install(self):
        self.ensure_one()
        lang_obj = self.env['res.lang']
        translation_obj = self.env['translation.term']
        res = super().lang_install()
        lng = lang_obj.search([('active', '=', True)], order='id ASC', limit=1)
        for lang in self.lang_ids:
            translation = translation_obj.search([('lang_id', '=', lng.id)])
            for tran in translation:
                vals = {
                        'model_id': tran.model_id.id,
                        'res_id': tran.res_id,
                        'field_id': tran.field_id.id,
                        'original': tran.original,
                        'value': tran.original,
                        'old_value': tran.original,
                        'lang_id': lang.id
                    }
                tra = translation_obj.create(vals)
        return res


class BaseLanguageInstall(models.TransientModel):
    _name = "base.model.language"
    _description = "Translator Word Genrator"


    def get_domain(self):
        return [('transient', '=', False), ('model','in', Model_List)]

    model_id = fields.Many2one('ir.model', string='Models', domain=lambda self: self.get_domain())
    field_ids = fields.Many2many('ir.model.fields', string='Fields', domain="[('model_id', '=', model_id),('translate', '=', True)]")

    def action_generate(self):
        for rec in self:
            ln_dom = []#[('code', '!=', 'en_US')]
            #Project Data
            translationObj = self.env['translation.term']
            langObj = self.env['res.lang']

            lngs = langObj.search(ln_dom)
            list_record = []
            for record in self.env[rec.model_id.model].search([]):
                for f in rec.field_ids:
                    langs = translationObj.mapped('lang_id')
                    for l in lngs:
                        if not translationObj.\
                            search([('field_id', '=', f.id),
                                    ('model_id', '=', rec.model_id.id),
                                    ('res_id', '=', record.id),
                                    ('lang_id', '=', l.id)]):
                            model = rec.model_id.model.replace('.', '_')
                            value = self.env[rec.model_id.model].search_read([('id', '=', record.id)], [f.name])
                            clean = re.compile('<.*?>')
                            if value and value[0].get(f.name):
                                value = re.sub(clean, '', value[0][f.name])
                                vals = {
                                    'model_id': rec.model_id.id,
                                    'res_id': record.id,
                                    'field_id': f.id,
                                    'original': value,
                                    'value': value,
                                    'old_value': value,
                                    'lang_id': l.id
                                }
                                tra =translationObj.create(vals)
                                list_record.append(tra.id)
            if list_record:
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "translation.term",
                    'view_mode': 'list',
                    "domain": [('id', 'in', list_record)],
                    "name": _("New Added Translation Term"),
                }
