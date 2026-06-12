{
    'name': 'Website Blog AI',
    'version': '19.0.1.0.0',
    'category': 'Website/Blog',
    'summary': 'AI Content Discovery & Blog Writer - Sniffer and Rédacteur agents',
    'description': """
Website Blog AI
===============

Two autonomous AI agents for Odoo's Website Blog:

* **Sniffer** - runs on a schedule, performs real web searches based on
  user-defined keywords, and generates article proposals (title, summary,
  context, editorial angle, sources, relevance score) stored for human
  validation.
* **Rédacteur** - after a proposal is validated, generates a complete
  SEO-optimized French blog article, stored as an unpublished post for
  review and manual publication.
""",
    'author': 'Hafid',
    'website': 'https://github.com/HafidBma/website_blog_ai',
    'license': 'LGPL-3',
    'depends': ['website_blog'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_keyword_views.xml',
    ],
    'installable': True,
    'application': True,
}
