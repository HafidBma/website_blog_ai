import html
import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class AiSniffer(models.AbstractModel):
    """Sniffer agent: monitors the news from the configured keywords and
    creates blog topic proposals pending human validation.

    It is driven by a scheduled action (cron) and can also be triggered
    manually from the UI.
    """

    _name = 'ai.sniffer'
    _description = 'Sniffer Agent - News Monitoring'

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------
    @api.model
    def run(self):
        """Run one monitoring cycle. Returns the number of proposals created."""
        keywords = self.env['ai.blog.keyword'].search([('active', '=', True)])
        if not keywords:
            _logger.info("Sniffer: no active keyword, nothing to monitor.")
            return 0
        created = self._discover(keywords)
        _logger.info("Sniffer: created %s proposal(s).", len(created))
        return len(created)

    @api.model
    def action_run_now(self):
        """Manual trigger from the UI: run and notify, then open proposals."""
        count = self.run()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Sniffer finished"),
                'message': (
                    _("%s new proposal(s) created.") % count if count
                    else _("No relevant topic found this time.")
                ),
                'type': 'success' if count else 'warning',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _("Proposals"),
                    'res_model': 'ai.blog.proposal',
                    'view_mode': 'list,form',
                    'target': 'current',
                },
            },
        }

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------
    def _max_proposals(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'website_blog_ai.sniffer_max_proposals', 3,
        )
        try:
            return max(1, int(param))
        except (TypeError, ValueError):
            return 3

    def _discover(self, keywords):
        prompt = self._build_prompt(keywords, self._max_proposals())
        data, grounding_sources = self.env['ai.provider'].generate_json(
            prompt,
            system_instruction=self._system_instruction(),
            use_web_search=True,
        )
        topics = self._normalize_topics(data)
        kw_by_name = {k.name.strip().lower(): k for k in keywords}

        Proposal = self.env['ai.blog.proposal']
        created = Proposal.browse()
        for topic in topics[:self._max_proposals()]:
            vals = self._topic_to_vals(topic, grounding_sources, kw_by_name)
            if vals:
                created |= Proposal.create(vals)
        return created

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------
    @staticmethod
    def _system_instruction():
        return (
            "Tu es « Sniffer », un agent de veille éditoriale. Tu analyses "
            "l'actualité récente et tu proposes des sujets d'articles de blog "
            "pertinents. Tu réponds toujours en français et uniquement avec "
            "du JSON valide, sans aucun texte autour."
        )

    @staticmethod
    def _build_prompt(keywords, max_topics):
        lines = []
        for kw in keywords:
            if kw.note:
                lines.append("- %s (%s)" % (kw.name, kw.note))
            else:
                lines.append("- %s" % kw.name)
        keywords_block = "\n".join(lines)
        return (
            "Mots-clés de veille :\n%(keywords)s\n\n"
            "Ta mission :\n"
            "1. Recherche l'actualité récente (web) en lien avec ces mots-clés.\n"
            "2. Identifie les %(n)s sujets les plus pertinents pour des "
            "articles de blog.\n"
            "3. Pour chaque sujet, fournis les informations demandées.\n\n"
            "Réponds UNIQUEMENT avec un objet JSON de cette forme :\n"
            "{\n"
            '  "topics": [\n'
            "    {\n"
            '      "keyword": "le mot-clé concerné",\n'
            '      "title": "un titre d\'article suggéré",\n'
            '      "summary": "un résumé du sujet en 2 ou 3 phrases",\n'
            '      "context": "le contexte d\'actualité identifié",\n'
            '      "editorial_angle": "l\'angle rédactionnel recommandé",\n'
            '      "sources": ["https://...", "https://..."],\n'
            '      "relevance_score": 8.5,\n'
            '      "justification": "pourquoi ce sujet est pertinent"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Le score de pertinence est un nombre entre 0 et 10.\n"
            "N'invente jamais d'URL : n'utilise que des sources réelles "
            "issues de ta recherche web."
        ) % {'keywords': keywords_block, 'n': max_topics}

    # ------------------------------------------------------------------
    # Response mapping
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_topics(data):
        if isinstance(data, dict):
            return data.get('topics') or data.get('results') or []
        if isinstance(data, list):
            return data
        return []

    def _topic_to_vals(self, topic, grounding_sources, kw_by_name):
        if not isinstance(topic, dict):
            return None
        title = (topic.get('title') or '').strip()
        if not title:
            return None
        try:
            score = float(topic.get('relevance_score'))
        except (TypeError, ValueError):
            score = 0.0
        keyword_id = self._match_keyword(topic.get('keyword'), kw_by_name)
        return {
            'suggested_title': title,
            'summary': topic.get('summary') or '',
            'context': topic.get('context') or '',
            'editorial_angle': topic.get('editorial_angle') or '',
            'sources': self._format_sources(topic.get('sources'),
                                             grounding_sources),
            'relevance_score': score,
            'justification': topic.get('justification') or '',
            'keyword_id': keyword_id,
            'state': 'new',
        }

    @staticmethod
    def _match_keyword(raw_keyword, kw_by_name):
        """Resolve the keyword the AI attributed the topic to.

        Exact match first, then a contains-match, then fall back to the only
        monitored keyword if there is just one.
        """
        name = (raw_keyword or '').strip().lower()
        if name in kw_by_name:
            return kw_by_name[name].id
        # Only attempt a contains-match for a non-empty name, otherwise an
        # empty string would match every keyword.
        if name:
            for kw_name, kw in kw_by_name.items():
                if kw_name in name or name in kw_name:
                    return kw.id
        if len(kw_by_name) == 1:
            return next(iter(kw_by_name.values())).id
        return False

    @staticmethod
    def _format_sources(topic_sources, grounding_sources):
        """Return the sources as an HTML list of clickable links."""
        items = []

        def add(url, title):
            url = (url or '').strip()
            if not url:
                return
            title = (title or url).strip()
            items.append((url, title))

        for src in topic_sources or []:
            if isinstance(src, dict):
                add(src.get('uri') or src.get('url'), src.get('title'))
            else:
                add(str(src), str(src))
        # Fall back to the real grounding citations if the model gave none.
        if not items:
            for src in grounding_sources or []:
                add(src.get('uri'), src.get('title'))
        if not items:
            return False

        links = "".join(
            '<li><a href="%s" target="_blank" rel="noreferrer">%s</a></li>' % (
                html.escape(url, quote=True), html.escape(title),
            )
            for url, title in items
        )
        return "<ul>%s</ul>" % links
