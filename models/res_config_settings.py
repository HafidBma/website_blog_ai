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
        default='gemini-flash-latest',
    )
    gemini_base_url = fields.Char(
        string='API Base URL',
        config_parameter='website_blog_ai.gemini_base_url',
        default='https://generativelanguage.googleapis.com/v1beta/models',
    )

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
