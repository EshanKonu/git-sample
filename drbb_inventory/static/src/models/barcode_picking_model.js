/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

patch(BarcodePickingModel.prototype, {

    async _putInPack(additionalContext = {}) {
        const context = Object.assign({ barcode_view: true }, additionalContext);
        if (!this.groups.group_tracking_lot) {
            return this.notification(
                _t("To use packages, enable 'Packages' in the settings"),
                { type: 'danger'}
            );
        }
        // Before the put in pack, create a new empty move line with the remaining
        // quantity for each uncompleted move line who will be packaged.
        const lines = [...this.pageLines];
        for (const line of lines) {
            if (line.result_package_id || !this.shouldSplitLine(line)) {
                continue; // Line is already in a package or no quantity to process.
            }
            await this.splitLine(line);
        }
        await this.save();
        const result = await this.orm.call(
            this.resModel,
            'action_put_in_pack',
            [[this.resId]],
            { context }
        );
        if (typeof result === 'object') {
            this.trigger('process-action', result);
        } else {
            this.trigger('refresh');
            // taken from core, only change here is to reload
            window.location.reload();
        }
    },

    get displaySplitBatch() {
        return this.config.restrict_split_batch != 'no';
    },

    get canSplitBatch() {
        if (this.config.restrict_scan_product) {
            return this.pageLines.some(line => line.qty_done && !line.result_package_id);
        }
        return true;
    },

    async _splitBatch(additionalContext = {}) {
        const context = Object.assign({ barcode_view: true }, additionalContext);
        // Before the split batch, create a new empty move line with the remaining
        // quantity for each uncompleted move line who will be packaged.
        const lines = [...this.pageLines];
        for (const line of lines) {
            if (line.result_package_id || !this.shouldSplitLine(line)) {
                continue; // Line is already in a package or no quantity to process.
            }
            await this.splitLine(line);
        }
        await this.save();
        const result = await this.orm.call(
            this.resModel,
            'action_split_batch',
            [[this.resId]],
            { context }
        );
        this.trigger('refresh');
    },

    /**
     * @override
     * changing the sort index
     */
    async updateLine(line, args) {
        // calling super method
        await super.updateLine(...arguments);
        // checking if there are quality checks by calling the backend
        const action = await this.orm.call(
            this.resModel,
            'action_check_quality_line',
            [[this.resId], line.id]
        );
        const options = {
            onClose: ev => this._closeValidate(ev)
        };
        // returning the action
        if (action && (action.res_model || action.type == "ir.actions.client")) {
            if (action.type == "ir.actions.client") {
                action.params = Object.assign(action.params || {}, options)
            }
            this.trigger("playSound");
            return this.action.doAction(action, options);
        }
        return options.onClose();
    },

    // function to refresh after closing QC barcode popup
    async _onRefreshState(paramsRefresh) {
        const { recordId, lineId } = paramsRefresh || {}
        const { route, params } = this.getActionRefresh(recordId);
        const result = await rpc(route, params);
        await this.refreshCache(result.data.records);
        await this.displayBarcodeLines(lineId);
        this.trigger('refresh');
    },

    // Function to check quality of all the lines
    async _checkQuality() {
        await this.save();
        if (this.record && this.record.quality_check_todo) {
            const res = await this.orm.call(
                this.resModel,
                this.openQualityChecksMethod,
                [[this.resId]]
            );
            const options = {
                onClose: ev => this._closeValidate(ev)
            };
            if (typeof res === 'object' && res !== null) {
                return this.action.doAction(res, {
                    onClose: this._onRefreshState.bind(this, {recordId: this.resId}),
                });
            } else {
                this.notification(_t("All the quality checks have been done"), {type: 'danger'});
            }
        } else {
            this.notification(_t("All the quality checks have been done"), {type: 'danger'});
        }
    },

    async _manualCheckQuality() {
        await this.save();
        const res = await this.orm.call(
            this.resModel,
            "action_open_on_demand_quality_check",
            [[this.resId]]
        );
        if (typeof res === 'object' && res !== null) {
            return this.action.doAction(res, {
                onClose: this._onRefreshState.bind(this, { recordId: this.resId }),
            });
        } else {
            this.notification(_t("There's no quality checks defined"), { type: 'danger'});
        }
    },

    // overidding to add ned the new barcode
    _getCommands() {
        const commands = super._getCommands();
        if (this.record) {
            commands['OBTQCCH'] = this._checkQuality.bind(this);
            commands['OBTMQCH'] = this._manualCheckQuality.bind(this);
        }
        return commands;
    },

    /**
     * Check if the given move line's location is a cousin location based on custom configuration.
     * This helper communicates with the server to check cousin location rules.
     * 
     * @private
     * @param {number} moveLineId - The ID of the move line to check.
     * @param {Object} barcodeData - The barcode data containing location information.
     * @returns {Promise<boolean>} - Resolves with true if the location is a cousin location, false otherwise.
     */
    async _checkCousinLocations(moveLineId, barcodeData) {
        const isCousinLocation = await this.orm.call(
            'stock.move',
            'get_cousin_locations',
            [[], moveLineId, barcodeData]
        );
        return isCousinLocation
    },

    /**
     * @override
     * This section is for checking cousin location configurations.
     */
    async _processLocationDestination(barcodeData) {
        const configScanDest = this.config.restrict_scan_dest_location;
        if (configScanDest == "no") {
            return;
        }
        // For planned transfers, check the scanned location is a part of transfer destination.
        if (this._useReservation && !this._isSublocation(barcodeData.destLocation, this._defaultDestLocation())) {
            // Check the scanned location is cousin location
            // Get all lines that will be moved to check cousin locations
            const linesToMove = this._getLinesToMove();
            let moveLineIds = [];
            
            if (this.selectedLine && this.selectedLine.id) {
                moveLineIds.push(this.selectedLine.id);
            }
            
            // Add all other lines that will be moved (avoid duplicates)
            for (const line of linesToMove) {
                if (line.id && !moveLineIds.includes(line.id)) {
                    moveLineIds.push(line.id);
                }
            }
            
            // Check cousin locations for all lines - allow if at least one line allows it
            if (moveLineIds.length > 0) {
                let isCousinLocation = false;
                for (const moveLineId of moveLineIds) {
                    const result = await this._checkCousinLocations(moveLineId, barcodeData);
                    if (result) {
                        isCousinLocation = true;
                        break; // At least one line allows it, so we can proceed
                    }
                }
                
                if (!isCousinLocation) {
                    barcodeData.stopped = true;
                    const message = _t("The scanned location doesn't belong to this operation's destination. To allow scanning of cousin locations, please activate the appropriate option in the related operation type settings.");
                    return this.notification(message, { type: 'danger' });
                }
            }
        }

        // Change the destination of all concerned lines.
        const lines = this._getLinesToMove();
        for (const line of lines) {
            await this.changeDestinationLocation(barcodeData.destLocation.id, line);
        }
        barcodeData.stopped = true;
    }
});

