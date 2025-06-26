from odoo import models

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def action_open_import_wizard(self):
        return {
            'name': 'Importar Líneas desde Excel',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition.line.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_requisition_id': self.id},
        }