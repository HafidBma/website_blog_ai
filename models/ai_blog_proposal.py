from odoo import fields, models


class AiBlogProposal(models.Model):
    _name = 'ai.blog.proposal'
    _description = 'Blog AI Topic Proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'suggested_title'
    _order = 'relevance_score desc, create_date desc'

    # --- The 6 mandatory fields required by the spec ---
    suggested_title = fields.Char(
        string='Suggested Title',
        required=True,
        tracking=True,
        help='Title suggested by the Sniffer agent.',
    )
    summary = fields.Text(
        string='Summary',
        help='Summary of the identified topic.',
    )
    context = fields.Text(
        string='Identified Context',
        help='Context the Sniffer identified around the topic.',
    )
    editorial_angle = fields.Text(
        string='Recommended Editorial Angle',
        help='Suggested angle for writing the article.',
    )
    sources = fields.Html(
        string='Potential Sources',
        help='Source URLs found during the web search.',
    )
    relevance_score = fields.Float(
        string='Relevance Score',
        tracking=True,
        help='Relevance score out of 10 (or selection justification).',
    )
    justification = fields.Text(
        string='Selection Justification',
        help='Why the Sniffer selected this topic.',
    )

    # --- Workflow / link fields ---
    keyword_id = fields.Many2one(
        'ai.blog.keyword',
        string='Keyword',
        ondelete='set null',
        help='Keyword that triggered this proposal.',
    )
    extra_instructions = fields.Text(
        string='Additional Instructions',
        help='Optional instructions passed to the Rédacteur agent before '
             'generating the article.',
    )
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('validated', 'Validated'),
            ('generated', 'Article Generated'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='new',
        required=True,
        tracking=True,
    )

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset_to_new(self):
        self.write({'state': 'new'})
