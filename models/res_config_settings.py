from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Provider-agnostic settings
    ai_provider = fields.Selection(
        selection=[('gemini', 'Google Gemini')],
        string='AI Provider',
        config_parameter='website_blog_ai.ai_provider',
        default='gemini',
    )
    ai_timeout = fields.Integer(
        string='Request Timeout (seconds)',
        config_parameter='website_blog_ai.ai_timeout',
        default=120,
    )

    # Gemini-specific settings
    gemini_api_key = fields.Char(
        string='API Key',
        config_parameter='website_blog_ai.gemini_api_key',
    )
    gemini_model = fields.Char(
        string='Model',
        config_parameter='website_blog_ai.gemini_model',
        default='gemini-2.5-flash',
    )
    gemini_base_url = fields.Char(
        string='API Base URL',
        config_parameter='website_blog_ai.gemini_base_url',
        default='https://generativelanguage.googleapis.com/v1beta/models',
    )

    # Sniffer agent settings
    sniffer_interval_days = fields.Integer(
        string='Run Every (days)',
        default=7,
        help='How often the Sniffer agent monitors the news.',
    )
    sniffer_max_proposals = fields.Integer(
        string='Max Proposals per Run',
        config_parameter='website_blog_ai.sniffer_max_proposals',
        default=3,
    )

    def get_values(self):
        res = super().get_values()
        cron = self.env.ref(
            'website_blog_ai.ir_cron_sniffer', raise_if_not_found=False,
        )
        if cron:
            res['sniffer_interval_days'] = cron.interval_number
        return res

    def set_values(self):
        super().set_values()
        cron = self.env.ref(
            'website_blog_ai.ir_cron_sniffer', raise_if_not_found=False,
        )
        if cron and self.sniffer_interval_days:
            cron.sudo().write({
                'interval_number': self.sniffer_interval_days,
                'interval_type': 'days',
            })

    def action_test_ai_connection(self):
        """Quick round-trip to verify the provider configuration works."""
        self.ensure_one()
        self.set_values()
        result = self.env['ai.provider'].generate(
            "Reply with exactly the two characters: OK"
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("AI connection successful"),
                'message': _("The AI replied: %s") % (result['text'] or '')[:200],
                'type': 'success',
                'sticky': False,
            },
        }
