import json
import logging
import re

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Fallback defaults, used only when the matching config parameter is unset.
PARAM_DEFAULTS = {
    'website_blog_ai.ai_provider': 'gemini',
    'website_blog_ai.ai_timeout': '120',
    'website_blog_ai.gemini_base_url':
        'https://generativelanguage.googleapis.com/v1beta/models',
    'website_blog_ai.gemini_model': 'gemini-flash-latest',
}


class AiProvider(models.AbstractModel):
    """Vendor-neutral AI service.

    The rest of the module only calls the provider-agnostic :meth:`generate`
    / :meth:`generate_json`. The active vendor is selected by the
    ``website_blog_ai.ai_provider`` config parameter and dispatched to a
    ``_call_<provider>`` method. Adding a new provider means adding one such
    method (and a Selection option in the settings); no caller changes.
    """

    _name = 'ai.provider'
    _description = 'AI Provider Abstraction Layer'

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _param(self, key):
        return self.env['ir.config_parameter'].sudo().get_param(
            key, PARAM_DEFAULTS.get(key)
        )

    def _timeout(self):
        try:
            return int(self._param('website_blog_ai.ai_timeout') or 120)
        except (TypeError, ValueError):
            return 120

    # ------------------------------------------------------------------
    # Public API (provider agnostic)
    # ------------------------------------------------------------------
    def generate(self, prompt, system_instruction=None, use_web_search=False):
        """Return free text from the configured AI provider.

        :return: dict ``{'text': str, 'sources': [{'title', 'uri'}]}``
        """
        provider = (self._param('website_blog_ai.ai_provider')
                    or 'gemini').strip().lower()
        handler = getattr(self, '_call_%s' % provider, None)
        if handler is None:
            raise UserError(_(
                "Unknown AI provider '%s'. No matching implementation found."
            ) % provider)
        return handler(prompt, system_instruction, use_web_search)

    def generate_json(self, prompt, system_instruction=None, use_web_search=False):
        """Like :meth:`generate` but parse the answer as JSON.

        :return: tuple ``(parsed_json, sources)``
        """
        result = self.generate(prompt, system_instruction, use_web_search)
        return self._extract_json(result['text']), result['sources']

    # ------------------------------------------------------------------
    # Gemini implementation
    # ------------------------------------------------------------------
    def _call_gemini(self, prompt, system_instruction=None, use_web_search=False):
        api_key = self._param('website_blog_ai.gemini_api_key')
        if not api_key:
            raise UserError(_(
                "No API key configured for the AI provider.\n"
                "Set it in Blog AI > Configuration > Settings."
            ))

        base_url = (self._param('website_blog_ai.gemini_base_url') or '').rstrip('/')
        model = self._param('website_blog_ai.gemini_model')
        url = "%s/%s:generateContent" % (base_url, model)
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': api_key,
        }
        payload = {'contents': [{'parts': [{'text': prompt}]}]}
        if system_instruction:
            payload['systemInstruction'] = {
                'parts': [{'text': system_instruction}],
            }
        if use_web_search:
            # Google Search grounding -> real web search.
            payload['tools'] = [{'google_search': {}}]

        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=self._timeout(),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            _logger.error("AI API error %s: %s",
                          response.status_code, response.text[:500])
            raise UserError(_(
                "AI request failed (HTTP %s):\n%s"
            ) % (response.status_code, response.text[:300]))
        except requests.exceptions.RequestException as err:
            _logger.exception("AI API call failed")
            raise UserError(_("Could not reach the AI provider: %s") % err)

        return self._parse_gemini_response(response.json())

    def _parse_gemini_response(self, data):
        candidates = data.get('candidates') or []
        if not candidates:
            raise UserError(_("The AI returned no content."))
        candidate = candidates[0]
        parts = (candidate.get('content') or {}).get('parts') or []
        text = "".join(p.get('text', '') for p in parts).strip()

        # Grounding citations -> real source URLs found by the web search.
        sources = []
        grounding = candidate.get('groundingMetadata') or {}
        for chunk in grounding.get('groundingChunks') or []:
            web = chunk.get('web') or {}
            if web.get('uri'):
                sources.append({
                    'title': web.get('title') or web.get('uri'),
                    'uri': web.get('uri'),
                })
        return {'text': text, 'sources': sources}

    # ------------------------------------------------------------------
    # Pure helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_json(text):
        """Parse JSON from a model answer, tolerating markdown fences."""
        cleaned = (text or '').strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()
        try:
            return json.loads(cleaned)
        except (ValueError, TypeError):
            pass
        # Fallback: grab the outermost object or array.
        for open_ch, close_ch in (('{', '}'), ('[', ']')):
            start, end = cleaned.find(open_ch), cleaned.rfind(close_ch)
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except ValueError:
                    continue
        raise UserError(_(
            "Could not parse the AI response as JSON:\n%s"
        ) % (text or '')[:500])
