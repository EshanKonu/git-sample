import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class MissingMovesDialog extends Component {
    static components = { Dialog };
    static props = {
        missingMoves: Array,
        onApply: Function,
        onCancel: Function,
    };
    static template = "drbb_inventory.MissingMovesDialog";

    async _onApply() {
        await this.props.onApply();
        this.props.close();
    }
}
