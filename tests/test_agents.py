from unittest.mock import patch

from odoo.addons.website_blog_ai.models.ai_provider import AiProvider
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

SNIFFER_REPLY = {
    'text': (
        '{"topics": [{'
        '"keyword": "AI", '
        '"title": "Les agents IA en 2026", '
        '"summary": "Un résumé.", '
        '"context": "Un contexte.", '
        '"editorial_angle": "Un angle.", '
        '"sources": ["https://example.com/article"], '
        '"relevance_score": 8.5, '
        '"justification": "Sujet pertinent."'
        '}]}'
    ),
    'sources': [{'title': 'Example', 'uri': 'https://example.com/article'}],
}

REDACTEUR_REPLY = {
    'text': (
        "###TITLE###\nLes agents IA en 2026\n"
        "###SUBTITLE###\nUn tournant\n"
        "###META_TITLE###\nAgents IA 2026\n"
        "###META_DESCRIPTION###\nTout savoir sur les agents IA.\n"
        "###META_KEYWORDS###\nIA, agents, 2026\n"
        "###TEASER###\nUn court teaser.\n"
        "###CONTENT###\n<h2>Introduction</h2><p>Corps de l'article.</p>"
    ),
    'sources': [],
}


@tagged('post_install', '-at_install')
class TestSnifferAgent(TransactionCase):

    def test_run_creates_proposals(self):
        self.env['ai.blog.keyword'].search([]).write({'active': False})
        self.env['ai.blog.keyword'].create({'name': 'AI'})

        with patch.object(AiProvider, '_call_gemini', return_value=SNIFFER_REPLY):
            count = self.env['ai.sniffer'].run()

        self.assertEqual(count, 1)
        proposal = self.env['ai.blog.proposal'].search(
            [('suggested_title', '=', 'Les agents IA en 2026')], limit=1,
        )
        self.assertTrue(proposal)
        self.assertEqual(proposal.state, 'new')
        self.assertEqual(proposal.relevance_score, 8.5)
        self.assertEqual(proposal.keyword_id.name, 'AI')
        self.assertIn('example.com', proposal.sources)


@tagged('post_install', '-at_install')
class TestRedacteurAgent(TransactionCase):

    def test_generate_article_creates_unpublished_post(self):
        proposal = self.env['ai.blog.proposal'].create({
            'suggested_title': 'Les agents IA en 2026',
            'summary': 'Un résumé.',
            'state': 'validated',
        })

        with patch.object(AiProvider, '_call_gemini', return_value=REDACTEUR_REPLY):
            post = self.env['ai.redacteur'].generate_article(proposal)

        # Article created and correctly populated.
        self.assertEqual(post.name, 'Les agents IA en 2026')
        self.assertEqual(post.subtitle, 'Un tournant')
        self.assertEqual(post.website_meta_title, 'Agents IA 2026')
        self.assertEqual(post.website_meta_description,
                         'Tout savoir sur les agents IA.')
        self.assertEqual(post.website_meta_keywords, 'IA, agents, 2026')
        self.assertIn('<h2>', post.content)
        # Publication stays manual.
        self.assertFalse(post.is_published)
        # Proposal moved to generated and linked to the post.
        self.assertEqual(proposal.state, 'generated')
        self.assertEqual(proposal.blog_post_id, post)
