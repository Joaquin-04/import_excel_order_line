from odoo import models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_open_import_wizard(self):
        """Abre el wizard de importación para esta orden de venta."""
        return {
            'name': 'Importar Líneas desde Excel',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }
