import base64
import io
import pandas as pd
from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    excel_file = fields.Binary(string="Archivo Excel")
    excel_filename = fields.Char(string="Nombre del Archivo")

    def action_import_order_lines(self):
        if not self.excel_file:
            raise UserError("Por favor, carga un archivo Excel antes de importar.")
        
        # Decodificar el archivo Excel
        try:
            data = base64.b64decode(self.excel_file)
            file = io.BytesIO(data)
            df = pd.read_excel(file)
        except Exception as e:
            raise UserError(f"Error al leer el archivo Excel: {str(e)}")

        # Validar la existencia de las columnas necesarias
        required_columns = ['product_code', 'quantity', 'price_unit']
        for column in required_columns:
            if column not in df.columns:
                raise UserError(f"El archivo Excel debe contener la columna '{column}'")

        # Iterar sobre las filas y crear líneas de pedido
        for _, row in df.iterrows():
            product = self.env['product.product'].search([('default_code', '=', row['product_code'])], limit=1)
            if not product:
                raise UserError(f"Producto con código '{row['product_code']}' no encontrado.")

            # Agregar la línea de pedido
            self.order_line.create({
                'order_id': self.id,
                'product_id': product.id,
                'product_uom_qty': row['quantity'],
                'price_unit': row['price_unit'],
            })

        return True
