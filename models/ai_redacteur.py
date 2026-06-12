import logging
import re

from odoo import _, models

_logger = logging.getLogger(__name__)

# Section markers used to structure the article. HTML content comes last and
# raw, so we avoid the quoting/escaping problems of embedding HTML in JSON.
SECTIONS = [
    'TITLE', 'SUBTITLE', 'META_TITLE', 'META_DESCRIPTION',
    'META_KEYWORDS', 'TEASER', 'CONTENT',
]


class AiRedacteur(models.AbstractModel):
    """Rédacteur agent: turns a validated proposal into a complete,
    SEO-optimized blog article stored as an (unpublished) ``blog.post``.

    Publishing stays a manual user action.
    """

    _name = 'ai.redacteur'
    _description = 'Rédacteur Agent - SEO Article Writer'

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def generate_article(self, proposal):
        proposal.ensure_one()
        result = self.env['ai.provider'].generate(
            self._build_prompt(proposal),
            system_instruction=self._system_instruction(),
        )
        data = self._parse_sections(result['text'])
        post = self._create_blog_post(proposal, data)
        proposal.write({'state': 'generated', 'blog_post_id': post.id})
        _logger.info("Rédacteur: created blog post %s for proposal %s.",
                     post.id, proposal.id)
        return post

    # ------------------------------------------------------------------
    # Blog post creation
    # ------------------------------------------------------------------
    def _create_blog_post(self, proposal, data):
        blog = self.env['blog.blog'].search([], limit=1)
        if not blog:
            blog = self.env['blog.blog'].create({'name': _("Blog")})

        vals = {
            'name': data.get('TITLE') or proposal.suggested_title or '',
            'subtitle': data.get('SUBTITLE') or '',
            'blog_id': blog.id,
            'content': data.get('CONTENT') or '',
            'website_meta_title': data.get('META_TITLE') or '',
            'website_meta_description': data.get('META_DESCRIPTION') or '',
            'website_meta_keywords': data.get('META_KEYWORDS') or '',
        }
        teaser = (data.get('TEASER') or '').strip()
        if teaser:
            vals['teaser'] = teaser
        return self.env['blog.post'].create(vals)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_sections(text):
        """Split the delimiter-structured answer into a dict of sections.

        Markers look like ``###CONTENT###``; each section runs until the next
        marker, so the HTML body can contain anything (quotes, newlines).
        """
        pattern = re.compile(r'###\s*(%s)\s*###' % '|'.join(SECTIONS))
        matches = list(pattern.finditer(text or ''))
        result = {}
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            result[match.group(1)] = text[start:end].strip()
        return result

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------
    @staticmethod
    def _system_instruction():
        return (
            "Tu es « Rédacteur », un rédacteur web SEO expert. Tu rédiges des "
            "articles de blog complets et optimisés pour le référencement "
            "naturel (SEO), en français. Tu respectes toujours exactement le "
            "format de sortie demandé, sans aucun autre texte."
        )

    @staticmethod
    def _build_prompt(proposal):
        extra = ""
        if proposal.extra_instructions:
            extra = (
                "\nInstructions complémentaires de l'utilisateur "
                "(à respecter en priorité) :\n%s\n" % proposal.extra_instructions
            )
        return (
            "Rédige un article de blog complet et optimisé SEO à partir de la "
            "proposition suivante.\n\n"
            "Titre suggéré : %(title)s\n"
            "Résumé : %(summary)s\n"
            "Contexte : %(context)s\n"
            "Angle rédactionnel : %(angle)s\n"
            "Justification : %(justification)s\n"
            "%(extra)s\n"
            "Consignes :\n"
            "- Article en français, 800 à 1200 mots.\n"
            "- Structure claire avec des sous-titres (balises <h2> et <h3>).\n"
            "- Paragraphes courts, style professionnel et engageant.\n"
            "- Optimisé SEO (titres descriptifs, mots-clés pertinents placés "
            "naturellement).\n"
            "- Le corps de l'article doit être du HTML propre (uniquement "
            "<h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>), sans <html> ni "
            "<body>.\n\n"
            "Réponds en respectant EXACTEMENT ce format, en répétant les "
            "marqueurs ###...### tels quels, et sans rien ajouter avant ou "
            "après :\n\n"
            "###TITLE###\n"
            "le titre final de l'article\n"
            "###SUBTITLE###\n"
            "un sous-titre accrocheur\n"
            "###META_TITLE###\n"
            "titre SEO (max 60 caractères)\n"
            "###META_DESCRIPTION###\n"
            "meta description SEO (environ 155 caractères)\n"
            "###META_KEYWORDS###\n"
            "mot-clé1, mot-clé2, mot-clé3\n"
            "###TEASER###\n"
            "un court extrait introductif (1 ou 2 phrases)\n"
            "###CONTENT###\n"
            "<h2>...</h2><p>...</p>..."
        ) % {
            'title': proposal.suggested_title or '',
            'summary': proposal.summary or '',
            'context': proposal.context or '',
            'angle': proposal.editorial_angle or '',
            'justification': proposal.justification or '',
            'extra': extra,
        }
