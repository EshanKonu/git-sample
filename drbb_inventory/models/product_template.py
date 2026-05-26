from odoo import fields, models, api, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    drbb_picking_time_category_id = fields.Many2one('drbb.picking.time.category', string="Picking Time Category")
    drbb_product_brand_id = fields.Many2one("drbb.product.brand", string="Brand")
    drbb_article_group_id = fields.Many2one("drbb.article.group", string="Article Group")
    collection = fields.Char(string="Collection")
    drbb_product_subcollection_id = fields.Many2one("drbb.product.subcollection", string="Subcollection")
    drbb_collection_id = fields.Many2one("drbb.product.collection", string="Collection 2")
    publisher = fields.Char(string="Publisher")
    drbb_commercial_supplier_description = fields.Text(string="Commercial description supplier")
    item_status_id = fields.Many2one(string="Item Status", comodel_name='drbb.product.item.status',
                                     compute='_compute_item_status_id',
                                     inverse='_set_item_status_id',
                                     store=True, tracking=True)
    item_status_char = fields.Char(related='item_status_id.name', store=True, string="Item Status Char")
    cs_item_number = fields.Char(string="CS Item Number")
    on_item_number = fields.Char(string="ON Item Number")
    item_type_id = fields.Many2one("drbb.product.item.type", string="Type of Item")
    item_type_char = fields.Char(related='item_type_id.name', store=True, string="Type of Item Char")
    item_role_id = fields.Many2one("drbb.product.item.role", string="Item Role")
    assortment_year = fields.Char(string="Assortment Year")
    brand_type_id = fields.Many2one("drbb.product.brand.type", string="Brand Type")
    medical_device = fields.Selection([('yes', 'Yes'),
                                       ('no', 'No')], string="Medical device?")
    product_language_id = fields.Many2one("drbb.product.language", string="Language")
    category_manager_ids = fields.Many2many(
        'res.users',
        'product_category_manager_rel',
        'product_id', 'user_id',
        string="Category Manager"
    )
    centrally_stocked = fields.Boolean(string="Centrally stocked?")
    abc_class_id = fields.Many2one("drbb.product.abc.class", string="ABC")
    product_stage_id = fields.Many2one('drbb.product.stage', string="Product Stage", index=True, tracking=True,
                                       compute='_compute_stage_id', readonly=False, store=True,
                                       copy=False, ondelete='restrict')
    drbb_base_unit_price = fields.Monetary(string="Price Per Unit", compute="_compute_drbb_base_unit_price")
    drbb_base_unit_count = fields.Float(string="Base Unit Count", help="Base unit price for the product", compute='_compute_drbb_base_unit_count', inverse='_set_drbb_base_unit_count', store=True, default=0)
    drbb_base_unit_id = fields.Many2one('uom.uom', string="Custom Unit of Measure", store=True)
    drbb_base_unit_name = fields.Char(compute='_compute_drbb_base_unit_name')
    initial_forecasted_sales = fields.Integer(string="Initial Forecasted Sales")
    kvi = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="KVI")
    quality_labels_id = fields.Many2one("drbb.product.quality.label", string="Quality Labels")
    quality_labels_char = fields.Char(related='quality_labels_id.name', store=True, string="Quality Labels Char")
    category_supporter_ids = fields.Many2many(
        'res.users',
        'product_category_supporter_rel',
        'product_id', 'user_id',
        string="Category Supporter"
    )
    expiration_date = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Expiration Date ")
    drbb_product_multipart = fields.Boolean(string="Multi-part product")
    drbb_product_multipart_amount = fields.Integer(string="Amount of Part", help="Fill this if the product exists of multiple parts, but uses only one barcode. This can be used to filter and set a quality-check")
    drbb_promotion_exclude_tag_ids = fields.Many2many("drbb.promotion.exclude.label", string="Exclude from Promotion", help="Field for internal use only! Check this tag, and make sure to include it in the domain filter of your promotion rules to exclude this product from promotions, discounts, or campaigns.")
    drbb_promotion_exclude_tag_ids_char = fields.Char(compute='_compute_drbb_promotion_exclude_tag_ids_char', store=True, string='Exclude from Promotion Char')
    drbb_promotion_website_tag_ids = fields.Many2many("drbb.promotion.website.label", string="Promotion Website Labels", help="Select one promotional label to display on the website for this product. Don’t forget to translate the label.")
    recommended_retail_price = fields.Monetary(string="RRP", help="This field contains the recommended retail price (RRP)")
    available_in_webshop = fields.Boolean(string="Available in Webshop")
    available_in_store = fields.Boolean(string="Available in Store")
    drbb_promotion_website_tag_english = fields.Char(string="Promotion Tag Names in English", store=True)
    drbb_promotion_website_tag_dutch = fields.Char(string="Promotion Tag Names in Dutch", store=True)
    drbb_promotion_website_tag_french = fields.Char(string="Promotion Tag Names in French", compute="compute_drbb_promotion_exclude_tag_names", store=True)
    drbb_product_inventory_section_id = fields.Many2one("drbb.product.inventory.section", string="Inventory Section")
    online_minimum_stock = fields.Float(string="Minimum stock for online")
    current_pricelist_price = fields.Monetary(string="Current Pricelist Price", compute="_current_pricelist_price")
    drbb_other_color_ids = fields.One2many(
        "drbb.product.other.color.variant",
        string="Other Colors",
        compute="_compute_drbb_other_color_ids",
        inverse="_set_drbb_other_color_ids",
    )
    drbb_cross_sell_ids = fields.One2many(
        "drbb.product.cross.sell.variant",
        string="Cross-sell",
        compute="_compute_drbb_cross_sell_ids",
        inverse="_set_drbb_cross_sell_ids",
    )

    @api.depends('product_variant_ids', 'product_variant_ids.drbb_other_color_variant_ids')
    def _compute_drbb_other_color_ids(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.drbb_other_color_ids = template.product_variant_ids.drbb_other_color_variant_ids
            else:
                template.drbb_other_color_ids = False

    def _set_drbb_other_color_ids(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.drbb_other_color_variant_ids = template.drbb_other_color_ids

    @api.depends('product_variant_ids', 'product_variant_ids.drbb_cross_sell_variant_ids')
    def _compute_drbb_cross_sell_ids(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.drbb_cross_sell_ids = template.product_variant_ids.drbb_cross_sell_variant_ids
            else:
                template.drbb_cross_sell_ids = False

    def _set_drbb_cross_sell_ids(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.drbb_cross_sell_variant_ids = template.drbb_cross_sell_ids

    def _current_pricelist_price(self):
        """Computes current pricelist price of the product"""
        pricelist = self.env['product.pricelist'].search([], limit=1)
        for product in self:
            product.current_pricelist_price = pricelist._get_product_price(product=product, quantity=1.0, uom=None)

    @api.depends("drbb_promotion_website_tag_ids", "drbb_promotion_website_tag_ids.name")
    def compute_drbb_promotion_exclude_tag_names(self):
        """
        Computes comma-separated promotion tag names for English, Dutch, and French. This method populates three fields
        with the translated names of the tags in their respective languages by fetching translations from
        `drbb_promotion_website_tag_ids`.

        :return: None
        """
        for rec in self:
            # Join all tag names translated to English (en_US)
            rec.drbb_promotion_website_tag_english = ", ".join(
                x.name for x in rec.with_context(lang="en_US")["drbb_promotion_website_tag_ids"])
            # Join all tag names translated to Dutch (nl_BE)
            rec.drbb_promotion_website_tag_dutch = ", ".join(
                x.name for x in rec.with_context(lang="nl_BE")["drbb_promotion_website_tag_ids"])
            # Join all tag names translated to French (fr_BE)
            rec.drbb_promotion_website_tag_french = ", ".join(
                x.name for x in rec.with_context(lang="fr_BE")["drbb_promotion_website_tag_ids"])

    @api.depends('name')
    def _compute_stage_id(self):
        """Setting default stage"""
        for record in self:
            if not record.product_stage_id:
                record.product_stage_id = self.env['drbb.product.stage'].search([], limit=1).id

    @api.model_create_multi
    def create(self, vals):
        """
        Overrides the product template creation to assign a default SAP article number if one is not provided.
        If `default_code` is missing, it generates one using the format 'DB<product_id>'. Also triggers synchronization
        of translation values after creation.

        :param vals: list of dictionaries representing new product templates
        :return: recordset of created product templates
        """
        products = super().create(vals)
        translation_obj = self.env["translation.term"]
        translation_obj.get_syn_value(products)
        return products

    @api.depends('product_variant_ids', 'product_variant_ids.drbb_base_unit_count')
    def _compute_drbb_base_unit_count(self):
        """Compute the base unit count for the product"""
        self.drbb_base_unit_count = 0
        for template in self.filtered(lambda template: len(template.product_variant_ids) == 1):
            template.drbb_base_unit_count = template.product_variant_ids.drbb_base_unit_count

    def _set_drbb_base_unit_count(self):
        """Set the base unit count on the product when changed in the template"""
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.drbb_base_unit_count = template.drbb_base_unit_count

    def _get_drbb_base_unit_price(self, price):
        """Calculate the base unit price for the product"""
        self.ensure_one()
        return self.drbb_base_unit_count and price / self.drbb_base_unit_count

    @api.depends('list_price', 'drbb_base_unit_count')
    def _compute_drbb_base_unit_price(self):
        """Compute the base unit price for the product"""
        for template in self:
            template.drbb_base_unit_price = template._get_drbb_base_unit_price(template.list_price)

    @api.depends('uom_name', 'drbb_base_unit_id.name')
    def _compute_drbb_base_unit_name(self):
        """Compute the base unit name for the product"""
        for template in self:
            template.drbb_base_unit_name = template.drbb_base_unit_id.name or template.uom_name

    @api.depends('product_variant_ids.item_status_id')
    def _compute_item_status_id(self):
        """Compute item status for the product template"""
        self._compute_template_field_from_variant_field('item_status_id')

    def _set_item_status_id(self):
        """Set item status of the product template"""
        self._set_product_variant_field('item_status_id')

    @api.onchange('recommended_retail_price')
    def _onchange_recommended_retail_price(self):
        """Warn users that updating the recommended retail price on a multi-variant product will apply the change to all variants"""
        if self.product_variant_count > 1:
            return {
                'warning': {
                    'title': _("Warning"),
                    'message': _(
                        "Updating the Recommended Retail Price will apply the new value to all variants."),
                },
            }

    def _get_product_names_formatted_list(self, characters_max_length=28):
        """
        Splits the product name into two lines, each with a maximum number of characters.
        :param characters_max_length: Maximum number of characters per line (default is 28).
        :return: A list containing two strings: the first and second lines of the product name.
        """
        first = self.name[:characters_max_length]
        second = self.name[characters_max_length:characters_max_length * 2]
        return [first, second or ""]

    def write(self, vals):
        """Override write to propagate any changes to recommended_retail_price from the template to all its variants"""
        if 'recommended_retail_price' in vals:
            self.product_variant_ids.write({'recommended_retail_price': vals['recommended_retail_price']})
        return super().write(vals)

    @api.depends("drbb_promotion_exclude_tag_ids", "drbb_promotion_exclude_tag_ids.name")
    def _compute_drbb_promotion_exclude_tag_ids_char(self):
        """Compute drbb_promotion_exclude_tag_ids_char seperated by commas"""
        for product_template in self:
            product_template.drbb_promotion_exclude_tag_ids_char = ", ".join(
                x.name for x in product_template["drbb_promotion_exclude_tag_ids"])
