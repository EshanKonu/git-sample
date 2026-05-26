from odoo import models, _
from odoo.exceptions import UserError


class ReportZPLDiscountLabel(models.AbstractModel):
    _name = "report.drbb_inventory.report_zpl_product_discount"
    _description = "Report ZPL Discount Label"

    def _get_report_values(self, docids, data):
        """
        Prepares data for a product pricing report.

        Based on the active model (product.template or product.product), it:
        - Retrieves the selected products.
        - Calculates the discount percentage based on list_price vs lowest_sale_price.
        - Appends quantity and discount info to the report data.

        :param docids: Document IDs (not used here).
        :param data: Dictionary containing 'active_model' and 'quantity_by_product'.
        :return: Updated data dictionary including 'product_details'.
        """
        if data.get('active_model') == 'product.template':
            Product = self.env['product.template']
        elif data.get('active_model') == 'product.product':
            Product = self.env['product.product']
        else:
            raise UserError(_('Product model not defined, Please contact your administrator.'))

        product_details = []
        for product, quantity in data.get('quantity_by_product').items():
            product = Product.browse(int(product))
            # Calculate discount only if prices are valid and not equal
            product_details.append({
                "product_id": product,
                "quantity": quantity,
                "previous_lowest_price_label": _("previous lowest price"),
                "price_per_unit": _("price per unit")
            })
        data["product_details"] = product_details
        return data
