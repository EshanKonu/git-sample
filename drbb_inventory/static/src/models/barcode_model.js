import BarcodeModel from "@stock_barcode/models/barcode_model";

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { MissingMovesDialog } from '../components/missing_moves_dialog';


patch(BarcodeModel.prototype, {

    /**
     * @override
     * changing the sort index
     */
    get groupedLinesByLocation() {
        const lines = [].concat(this.groupedLines, this.packageLines);
        const linesByLocations = []
        const linesByLocation = {};
        for (const line of lines) {
            const lineLoc = line.location_id;
            if (!linesByLocation[lineLoc.id]) {
                linesByLocation[lineLoc.id] = {
                    location: lineLoc,
                    lines: [],
                };
            }
            if (!linesByLocations.includes(linesByLocation[lineLoc.id])) {
                linesByLocations.push(linesByLocation[lineLoc.id]);
            }
            linesByLocation[lineLoc.id].lines.push(line);
        }
        // Sorts groups to ensure that locations will always follow the alphabetical order.
        linesByLocations.sort((lblA, lblB) => {
            const [rmPrioA, rmPrioB] = [lblA.location.removal_prio, lblB.location.removal_prio];
            return rmPrioA < rmPrioB ? -1 : rmPrioA > rmPrioB ? 1 : 0;
        });
        return linesByLocations
    },

    _verifyExistingLineIds(id) {
        const res = this.orm.call(
            "stock.move.line",
            "check_record_exist",
            [[id]]
        );
        return res
    },

    async _customGetSaveLineCommand() {
        const commands = [];
        const missingRecords = [];
        const fields = this._getFieldToWrite();
        for (const virtualId of this.linesToSave) {
            const line = this.currentState.lines.find(l => l.virtual_id === virtualId);
            if (line.id) { // Update an existing line.
                const initialLine = this.initialState.lines.find(l => l.virtual_id === line.virtual_id);
                const changedValues = {};
                let somethingToSave = false;
                for (const field of fields) {
                    const fieldValue = line[field];
                    const initialValue = initialLine[field];
                    if (fieldValue !== undefined && (
                        (['boolean', 'number', 'string'].includes(typeof fieldValue) && fieldValue !== initialValue) ||
                        (typeof fieldValue === 'object' && fieldValue.id !== initialValue.id)
                    )) {
                        changedValues[field] = this._fieldToValue(fieldValue);
                        somethingToSave = true;
                    }
                }
                if (somethingToSave && this.resModel !== "stock.quant"){
                    const recordExisting = await this._verifyExistingLineIds(line.id);
                    if (recordExisting) {
                        commands.push([1, line.id, changedValues]);
                    }
                    else {
                        missingRecords.push(line)
                    }
                }
            } else { // Create a new line.
                commands.push([0, 0, this._createCommandVals(line)]);
            }
        }
        if (missingRecords.length > 0) {
            this.trigger("playSound", "error");
            await new Promise((resolve) => {
                const dialog = this.dialogService;
                dialog.add(MissingMovesDialog, {
                    missingMoves: missingRecords,
                    onApply: () => resolve(commands),
                    onCancel: () => {},
                });
            });
        }
        return commands;
    },

    async _customGetSaveCommand() {
        const commands = await this._customGetSaveLineCommand();
        if (commands.length) {
            return {
                route: '/stock_barcode/save_barcode_data',
                params: {
                    model: this.resModel,
                    res_id: this.resId,
                    write_field: 'move_line_ids',
                    write_vals: commands,
                },
            };
        }
        return {};
    },

    async save() {
        if (this.resModel === "stock.quant") {
            return super.save(...arguments);
        }
        const { route, params } = await this._customGetSaveCommand();
        if (route) {
            const res = await rpc(route, params);
            await this.refreshCache(res.records);
        }
        this.linesToSave = [];
    }
})
