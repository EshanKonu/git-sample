import logging

from psycopg2 import Error

from odoo.addons.stock.models.stock_quant import StockQuant

_logger = logging.getLogger(__name__)


def _merge_quants(self):
    """Extend core merge to keep inventory flags/diff in sync after import merges."""
    params = []
    query = """WITH
                    dupes AS (
                        SELECT min(id) as to_update_quant_id,
                            (array_agg(id ORDER BY id))[2:array_length(array_agg(id), 1)] as to_delete_quant_ids,
                            GREATEST(0, SUM(reserved_quantity)) as reserved_quantity,
                            SUM(inventory_quantity) as inventory_quantity,
                            SUM(quantity) as quantity,
                            MIN(in_date) as in_date,
                            BOOL_OR(inventory_quantity_set) as inventory_quantity_set
                        FROM stock_quant
    """
    if self._ids:
        query += """
                        WHERE
                            location_id in %s
                            AND product_id in %s
        """
        params = [tuple(self.location_id.ids), tuple(self.product_id.ids)]
    query += """
                        GROUP BY product_id, company_id, location_id, lot_id, package_id, owner_id
                        HAVING count(id) > 1
                    ),
                    _up AS (
                        UPDATE stock_quant q
                            SET quantity = d.quantity,
                                reserved_quantity = d.reserved_quantity,
                                inventory_quantity = d.inventory_quantity,
                                inventory_diff_quantity = d.inventory_quantity - d.quantity,
                                inventory_quantity_set = d.inventory_quantity_set,
                                in_date = d.in_date
                        FROM dupes d
                        WHERE d.to_update_quant_id = q.id
                    )
               DELETE FROM stock_quant WHERE id in (SELECT unnest(to_delete_quant_ids) from dupes)
    """
    try:
        with self.env.cr.savepoint():
            self.env.cr.execute(query, params)
            self.env.invalidate_all()
    except Error as exc:
        _logger.info('an error occurred while merging quants: %s', exc.pgerror)


StockQuant._merge_quants = _merge_quants
