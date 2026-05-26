from odoo import fields, models, api
from odoo.exceptions import UserError, AccessError
from odoo.tools.translate import _


class LoyaltyProgram(models.Model):
    _inherit = "loyalty.program"

    pick_to_clean = fields.Boolean(string="Pick to Clean")