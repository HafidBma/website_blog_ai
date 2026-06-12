from odoo import fields, models


class AiBlogKeyword(models.Model):
    _name = 'ai.blog.keyword'
    _description = 'Blog AI Keyword'
    _order = 'name'

    name = fields.Char(
        string='Keyword',
        required=True,
    )
    active = fields.Boolean(default=True)
    note = fields.Char(
        string='Note',
    )
