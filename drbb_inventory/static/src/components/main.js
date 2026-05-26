/** @odoo-module **/

import MainComponent from "@stock_barcode/components/main";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { user } from '@web/core/user';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


patch(MainComponent.prototype, {

    async _checkConditionAndNotify() {
        // "record" comes from barcodeData (populated in onWillStart)
        const rec = this.env.model?.record;
        if (!rec) return;

        // rec.user_id usually looks like [id, display_name]
        const assignedUserId = Array.isArray(rec.user_id) ? rec.user_id[0] : rec.user_id;
        const currentUserId = user.userId;
        const warnAssignedUser = rec.warn_assigned_user_in_barcode;

        if (warnAssignedUser && assignedUserId && assignedUserId !== currentUserId) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Warning"),
                body: _t("Another user is already assigned to this batch!."),
                confirm: () => {}, // optional: do something if they press OK
                cancel: () => {},      // removes the Cancel button → forces them to acknowledge
            });
        }
    },

    async onWillStart() {
        await super.onWillStart();
        await this._checkConditionAndNotify();

        this.env.model.addEventListener("refresh", () => this._checkConditionAndNotify());
        // this.env.model.addEventListener("update", () => this._checkConditionAndNotify());
    },

    // function to split batch
    splitBatch(ev) {
        ev.stopPropagation();
        this.env.model._splitBatch();
    }
});

