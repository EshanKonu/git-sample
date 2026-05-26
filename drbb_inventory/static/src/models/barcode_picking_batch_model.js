/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import BarcodePickingBatchModel from '@stock_barcode_picking_batch/models/barcode_picking_batch_model';

patch(BarcodePickingBatchModel.prototype, {

    _sortingMethod(l1, l2) {
        // Hello
        if (l1.picking_weight < l2.picking_weight) {
            return -1;
        } else if (l1.picking_weight > l2.picking_weight) {
            return 1;
        }
        return 0;
    }

});

