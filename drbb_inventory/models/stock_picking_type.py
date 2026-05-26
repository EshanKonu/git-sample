from odoo import fields, models, api


SCHEDULED_DAY_SELECTION = [
    ('MON', 'Monday'),
    ('TUE', 'Tuesday'),
    ('WED', 'Wednesday'),
    ('THU', 'Thursday'),
    ('FRI', 'Friday'),
    ('SAT', 'Saturday'),
    ('SUN', 'Sunday'),
]


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def _get_default_volume_uom(self):
        """Get default volume unit of measure"""
        return self.env['product.template']._get_volume_uom_name_from_ir_config_parameter()

    role_id = fields.Many2one('planning.role', string="Role")
    scheduled_day = fields.Selection(SCHEDULED_DAY_SELECTION, string='Scheduled Day')
    pick_pack_ship = fields.Selection([
        ('pick', 'Pick'),
        ('pack', 'Pack'),
        ('ship', 'Ship'),
    ], string='Pick/Pack/Ship')
    filter_by_zone = fields.Boolean(string='Filter pickings by packaging zone', copy=False)
    wave_group_by_location_group = fields.Boolean('Location Group',
                                                  help="Split transfers by defined location groups, then group transfers with the same location group.")
    wave_location_group_ids = fields.Many2many('drbb.location.group', string='Wave Location Groups',
                                               help="Location Groups to consider when grouping waves.")
    wave_group_by_location_group_parent = fields.Many2one(string="Parent of the Location Group",
                                                          comodel_name='stock.location',
                                                          compute='_compute_wave_group_by_location_group_parent')
    batch_max_volume = fields.Float("Maximum volume",
                                    help="A transfer will not be automatically added to batches that will exceed this volume if the transfer is added to it.\n"
                                         "Leave this value as '0' if no volume limit.")
    volume_uom_name = fields.Char(string='Volume unit of measure label', compute='_compute_volume_uom_name', readonly=True, default=_get_default_volume_uom)
    hide_header_footer_in_barcode = fields.Boolean(string="Hide Header & Footer in Barcode")
    warn_assigned_user_in_barcode = fields.Boolean(
        string="Warn on assigned user in Barcode",
        default=True,
        help="If enabled, show a warning in the barcode app when another user is assigned.",
    )
    restrict_split_batch = fields.Selection([
            ("yes", "Yes"),
            ("no", "No"),
        ], "Restrict Batch Split?",
        default="yes", required=True)
    force_destination_package = fields.Boolean(string="Force Destination Package")
    wave_group_by_package = fields.Boolean(string="Package")
    respect_minimum_stock_for_online = fields.Boolean("Respect minimum stock for online.")
    prevent_wave_addition_user = fields.Boolean("Prevent wave addition when user assigned")
    bc_cousin_loc_scan = fields.Boolean('Allow cousin location scan')

    def _compute_volume_uom_name(self):
        """Compute the volume unit of measure"""
        for picking_type in self:
            picking_type.volume_uom_name = self.env['product.template']._get_volume_uom_name_from_ir_config_parameter()

    def _get_barcode_config(self):
        """ Extends the barcode config with a custom flag to control batch split behavior. """
        config = super()._get_barcode_config()
        config["restrict_split_batch"] = self.restrict_split_batch
        return config

    def get_action_picking_tree_ready_kanban(self):
        additional_context = {}
        user = self.env.user
        action = super(StockPickingType, self).get_action_picking_tree_ready_kanban()
        if user.package_zone_id and self.filter_by_zone:
            additional_context['search_default_package_zone_ids'] = user.package_zone_id.name
        action['context'].update(additional_context)

        # Remove To DO Filter
        action['context'].pop('search_default_to_do_transfers', None)
        return action

    @api.model
    def _get_wave_group_by_keys(self):
        """Extends the parent's wave grouping keys by adding 'wave_group_by_location_group'."""
        return super()._get_wave_group_by_keys() + ['wave_group_by_location_group'] + ['wave_group_by_package']

    @api.depends('wave_group_by_location_group', 'wave_location_group_ids')
    def _compute_wave_group_by_location_group_parent(self):
        """Compute parent of all locations"""
        Location = self.env['stock.location']
        for pick_type in self:
            locations = pick_type.wave_location_group_ids.location_ids
            if not locations:
                pick_type.wave_group_by_location_group_parent = False
                continue

            # Build a dict of {location_id: [ancestor_id, ancestor_id, ...]}
            location_all_parents = {}
            for loc in locations:
                ancestors = []
                parent = loc.location_id
                # walk up the chain until there are no more parents
                while parent:
                    ancestors.append(parent.id)
                    parent = parent.location_id
                location_all_parents[loc.id] = ancestors

            # Pick the first candidate in the first list that's in every list
            all_lists = list(location_all_parents.values())
            first_list = all_lists[0]
            common_id = None
            for candidate in first_list:
                if all(candidate in lst for lst in all_lists[1:]):
                    common_id = candidate
                    break

            # Assign the record (or False)
            pick_type.wave_group_by_location_group_parent = (
                    common_id and Location.browse(common_id) or False
            )

    def action_wave(self):
        """Returns a action which shows wave transfers that is related to operation type"""
        action = self.env['ir.actions.act_window']._for_xml_id('stock_picking_batch.action_picking_tree_wave')
        action['domain'] = [('is_wave', '=', True), ('picking_type_id', '=', self.id)]
        return action

    def action_batch(self):
        """Overiding super function to add a domain to show only relevant batch transfers for the operation type"""
        action = super().action_batch()
        action['domain'] = [('is_wave', '=', False), ('picking_type_id', '=', self.id)]
        return action
