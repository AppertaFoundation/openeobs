# -*- coding: utf-8 -*-
from openerp.osv import orm, fields


class NHClinicalSpell(orm.Model):
    """
    Override to add a boolean flag that indicates whether there are active
    patient monitoring exceptions on the spell.
    """
    _name = 'nh.clinical.spell'
    _inherit = 'nh.clinical.spell'

    _columns = {
        'obs_stop': fields.boolean('Stop Observations for patient?')
    }

    _defaults = {
        'obs_stop': False
    }
