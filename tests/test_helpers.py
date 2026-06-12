from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestProviderHelpers(TransactionCase):
    """Pure helpers of the AI provider (no network, no DB writes)."""

    def setUp(self):
        super().setUp()
        self.provider = self.env['ai.provider']

    def test_extract_json_plain_object(self):
        self.assertEqual(self.provider._extract_json('{"a": 1}'), {'a': 1})

    def test_extract_json_markdown_fence(self):
        text = '```json\n{"a": 1, "b": "x"}\n```'
        self.assertEqual(self.provider._extract_json(text), {'a': 1, 'b': 'x'})

    def test_extract_json_array(self):
        self.assertEqual(self.provider._extract_json('[1, 2, 3]'), [1, 2, 3])

    def test_extract_json_embedded_in_prose(self):
        text = 'Voici le résultat : {"ok": true} merci.'
        self.assertEqual(self.provider._extract_json(text), {'ok': True})

    def test_extract_json_invalid_raises(self):
        with self.assertRaises(UserError):
            self.provider._extract_json('not json at all')


@tagged('post_install', '-at_install')
class TestRedacteurHelpers(TransactionCase):
    """Delimiter parsing of the Rédacteur."""

    def setUp(self):
        super().setUp()
        self.redacteur = self.env['ai.redacteur']

    def test_parse_sections_basic(self):
        text = (
            "###TITLE###\nMon Titre\n"
            "###SUBTITLE###\nMon Sous-titre\n"
            "###CONTENT###\n<h2>Section</h2><p>Corps</p>"
        )
        data = self.redacteur._parse_sections(text)
        self.assertEqual(data['TITLE'], 'Mon Titre')
        self.assertEqual(data['SUBTITLE'], 'Mon Sous-titre')
        self.assertEqual(data['CONTENT'], '<h2>Section</h2><p>Corps</p>')

    def test_parse_sections_preserves_quotes_and_newlines(self):
        # The whole point of the delimiter format: HTML with quotes/newlines
        # that would break JSON must survive intact.
        text = (
            '###CONTENT###\n'
            '<p class="lead">Du texte avec "guillemets"\net un saut de ligne.</p>'
        )
        data = self.redacteur._parse_sections(text)
        self.assertIn('"guillemets"', data['CONTENT'])
        self.assertIn('\n', data['CONTENT'])

    def test_parse_sections_missing_markers(self):
        self.assertEqual(self.redacteur._parse_sections('aucun marqueur'), {})


@tagged('post_install', '-at_install')
class TestSnifferHelpers(TransactionCase):
    """Topic/keyword/source mapping helpers of the Sniffer."""

    def setUp(self):
        super().setUp()
        self.sniffer = self.env['ai.sniffer']
        Keyword = self.env['ai.blog.keyword']
        self.kw_ai = Keyword.create({'name': 'AI'})
        self.kw_odoo = Keyword.create({'name': 'Odoo'})

    # --- _match_keyword ---
    def test_match_keyword_exact(self):
        kw_by_name = {'ai': self.kw_ai, 'odoo': self.kw_odoo}
        self.assertEqual(
            self.sniffer._match_keyword('AI', kw_by_name), self.kw_ai.id,
        )

    def test_match_keyword_contains(self):
        kw_by_name = {'ai': self.kw_ai, 'odoo': self.kw_odoo}
        self.assertEqual(
            self.sniffer._match_keyword('the AI protocol', kw_by_name),
            self.kw_ai.id,
        )

    def test_match_keyword_empty_with_multiple_is_false(self):
        # Regression guard: an empty keyword must NOT match the first one.
        kw_by_name = {'ai': self.kw_ai, 'odoo': self.kw_odoo}
        self.assertFalse(self.sniffer._match_keyword('', kw_by_name))
        self.assertFalse(self.sniffer._match_keyword(None, kw_by_name))

    def test_match_keyword_empty_with_single_falls_back(self):
        kw_by_name = {'ai': self.kw_ai}
        self.assertEqual(
            self.sniffer._match_keyword('', kw_by_name), self.kw_ai.id,
        )

    def test_match_keyword_unknown_with_multiple_is_false(self):
        kw_by_name = {'ai': self.kw_ai, 'odoo': self.kw_odoo}
        self.assertFalse(
            self.sniffer._match_keyword('blockchain', kw_by_name),
        )

    # --- _normalize_topics ---
    def test_normalize_topics_dict(self):
        self.assertEqual(
            self.sniffer._normalize_topics({'topics': [{'a': 1}]}), [{'a': 1}],
        )

    def test_normalize_topics_list(self):
        self.assertEqual(self.sniffer._normalize_topics([{'a': 1}]), [{'a': 1}])

    def test_normalize_topics_other(self):
        self.assertEqual(self.sniffer._normalize_topics('nope'), [])

    # --- _format_sources ---
    def test_format_sources_from_strings(self):
        html = self.sniffer._format_sources(['https://example.com/a'], [])
        self.assertIn('<a href="https://example.com/a"', html)

    def test_format_sources_grounding_fallback(self):
        grounding = [{'title': 'Ex', 'uri': 'https://example.com/g'}]
        html = self.sniffer._format_sources(None, grounding)
        self.assertIn('https://example.com/g', html)
        self.assertIn('Ex', html)

    def test_format_sources_escapes_html(self):
        sources = [{'uri': 'https://e.com', 'title': '<script>'}]
        html = self.sniffer._format_sources(sources, [])
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)

    def test_format_sources_empty_returns_false(self):
        self.assertFalse(self.sniffer._format_sources([], []))
