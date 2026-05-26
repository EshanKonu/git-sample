from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    order_day = fields.Selection([
        ("0", "Monday"),
        ("1", "Tuesday"),
        ("2", "Wednesday"),
        ("3", "Thursday"),
        ("4", "Friday"),
        ("5", "Saturday"),
        ("6", "Sunday")
    ], "Order Day", required=True, index=True, default="0")
