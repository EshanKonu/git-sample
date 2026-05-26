from odoo import fields, models


class PackageZone(models.Model):
    _name = 'package.zone'
    _description = 'Package Zone'

    name = fields.Char()
    code = fields.Char()
