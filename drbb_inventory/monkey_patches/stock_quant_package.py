from odoo import _

from odoo.addons.stock.models.stock_quant import QuantPackage


def unpack(self):
    """Backport of https://github.com/odoo/odoo/commit/715d445c7e74ee52594e1bd9842c7eeaabb8396e
    — [PERF] stock: don't perform quant_tasks when unpacking empty packs.

    Without this fix, ``move_quants(unpack=True)`` empties ``self.quant_ids``
    (the One2many is filtered by ``package_id``), so ``self.quant_ids._quant_tasks()``
    runs on an empty recordset. Because ``_merge_quants`` / ``_unlink_zero_quants``
    fall back to an unbounded query when ``self._ids`` is empty, every unpack
    triggers a full-table scan + write on ``stock_quant``. With our automation
    rule unpacking many packages per cron tick, this is the root cause of the
    deadlocks on ``stock_quant_package``.

    Remove this monkey patch when upgrading to a build that already contains
    commit 715d445c7e.
    """
    if not self.quant_ids:
        return
    quants = self.quant_ids
    self.quant_ids.move_quants(message=_("Quantities unpacked"), unpack=True)
    quants._quant_tasks()


QuantPackage.unpack = unpack
