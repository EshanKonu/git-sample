from odoo import models, fields, api, _


class DRBBLocationTag(models.Model):
    _name = "drbb.location.tag"
    _description = "DRBB Location Tag"

    name = fields.Char(string="Name", required=True)