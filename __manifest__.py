{
    'name': 'Website Blog AI',
    'version': '19.0.1.0.0',
    'category': 'Website/Blog',
    'summary': 'AI Content Discovery & Blog Writer - Sniffer and Rédacteur agents',
    'description': """
Two autonomous AI agents for Odoo's Website Blog. The Sniffer monitors the news
from user-defined keywords and creates blog proposals pending validation. The
Rédacteur turns a validated proposal into a complete SEO-optimized article,
stored as an unpublished post for manual publication. See README.md for details.
""",
    'author': 'Hafid',
    'website': 'https://github.com/HafidBma/website_blog_ai',
    'license': 'LGPL-3',
    'depends': ['website_blog'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/ai_keyword_views.xml',
        'views/ai_blog_proposal_views.xml',
        'views/ai_sniffer_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
}
