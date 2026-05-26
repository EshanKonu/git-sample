# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID, Command


def migrate(cr, version):
    """
    @public - Check and update the existing valuation fields and standard price to all companies
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['product.category'].with_user(SUPERUSER_ID).search([])._inverse_valuation_fields()
    env['product.product'].with_user(SUPERUSER_ID).search([])._inverse_standard_price_drbb()
