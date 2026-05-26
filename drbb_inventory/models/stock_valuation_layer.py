# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _change_standart_price_accounting_entries(self, new_price):
        """
        Override to provide more descriptive error messages that include
        company name, product name, and category name.
        """
        # Handle account moves.
        product_accounts = {
            product.id: product.product_tmpl_id.get_product_accounts()
            for product in self.product_id
        }
        company_id = self.env.company
        am_vals_list = []
        
        for layer in self:
            product = layer.product_id
            value = layer.value

            if not product.is_storable or product.valuation != 'real_time':
                continue

            # Enhanced sanity checks with detailed error messages and instructions
            if not product_accounts[product.id].get('expense'):
                raise UserError(_(
                    "You must set a counterpart account (Expense Account) on product category "
                    "'%(category)s' for company '%(company)s'.\n\n"
                    "Product: [%(code)s] %(product)s\n\n"
                    "How to fix:\n"
                    "1. Switch to company '%(company)s'\n"
                    "2. Go to Inventory → Configuration → Product Categories\n"
                    "3. Open category '%(category)s'\n"
                    "4. In 'Account Properties' section, set the 'Expense Account' field\n"
                    "   (typically an expense account like 'Cost of Goods Sold')",
                    category=product.categ_id.display_name,
                    company=company_id.name,
                    code=product.default_code or 'N/A',
                    product=product.name,
                ))
            
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_(
                    "You must set a Stock Valuation Account on product category "
                    "'%(category)s' for company '%(company)s'.\n\n"
                    "Product: [%(code)s] %(product)s\n\n"
                    "How to fix:\n"
                    "1. Switch to company '%(company)s'\n"
                    "2. Go to Inventory → Configuration → Product Categories\n"
                    "3. Open category '%(category)s'\n"
                    "4. In 'Account Properties' section, set the 'Stock Valuation Account' field\n"
                    "   (typically an asset account like 'Stock Interim' or 'Inventory')",
                    category=product.categ_id.display_name,
                    company=company_id.name,
                    code=product.default_code or 'N/A',
                    product=product.name,
                ))
            
            if not product_accounts[product.id].get('stock_journal'):
                raise UserError(_(
                    "You must set a Stock Journal on product category "
                    "'%(category)s' for company '%(company)s'.\n\n"
                    "Product: [%(code)s] %(product)s\n\n"
                    "How to fix:\n"
                    "1. Switch to company '%(company)s'\n"
                    "2. Go to Inventory → Configuration → Product Categories\n"
                    "3. Open category '%(category)s'\n"
                    "4. In 'Account Properties' section, set the 'Stock Journal' field\n"
                    "   (typically a miscellaneous or stock journal)",
                    category=product.categ_id.display_name,
                    company=company_id.name,
                    code=product.default_code or 'N/A',
                    product=product.name,
                ))

            if value < 0:
                debit_account_id = product_accounts[product.id]['expense'].id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
            else:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['expense'].id

            name = _(
                '[Manual Cost Update] %(user)s changed cost from %(previous)s to %(new_price)s - %(record)s',
                user=self.env.user.name,
                previous=layer.lot_id.standard_price if layer.lot_id else product.standard_price,
                new_price=new_price,
                record=layer.lot_id.display_name or product.display_name
            )
            # Create a clear reference for manual cost updates
            ref = _("Manual Cost Update: [%(code)s] %(product)s",
                    code=product.default_code or 'N/A',
                    product=product.name)
            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': company_id.id,
                'ref': ref,
                'stock_valuation_layer_ids': [(6, None, [layer.id])],
                'move_type': 'entry',
                'line_ids': [(0, 0, {
                    'name': name,
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                    'quantity': 0,
                }), (0, 0, {
                    'name': name,
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                    'quantity': 0,
                })],
            }
            am_vals_list.append(move_vals)

        account_moves = self.env['account.move'].sudo().create(am_vals_list)
        if account_moves:
            account_moves._post()

