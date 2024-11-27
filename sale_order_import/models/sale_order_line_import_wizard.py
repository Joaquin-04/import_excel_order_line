import base64
import io
import pandas as pd
from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrderLineImportWizard(models.TransientModel):
    _name = 'sale.order.line.import.wizard'
    _description = 'Wizard para Importar Líneas de Pedido desde Excel'

    order_id = fields.Many2one('sale.order', string="Orden de Venta", required=True)
    excel_file = fields.Binary(string="Archivo Excel", required=True)
    excel_filename = fields.Char(string="Nombre del Archivo")

    def action_import_order_lines(self):
        """Procesa el archivo Excel y crea las líneas de pedido."""
        if not self.excel_file:
            raise UserError("Por favor, carga un archivo Excel antes de importar.")

        # Leer el archivo Excel
        try:
            data = base64.b64decode(self.excel_file)
            file = io.BytesIO(data)
            df = pd.read_excel(file)
        except Exception as e:
            raise UserError(f"Error al leer el archivo Excel: {str(e)}")

        # Validar las columnas requeridas
        required_columns = [
            'TIPOLOGIA', 'CANTIDAD', 'CODIGO', 'DESCRIPCION', 
            'PRECIO UNITARIO CARPINTERIA', 'CODIGO DISTANCIA /KM', 
            'PRECIO UNITARIO INSTALACION', 'SUBTOTAL UNIDAD', 'SUBTOTAL'
        ]
        for column in required_columns:
            if column not in df.columns:
                raise UserError(f"El archivo Excel debe contener la columna '{column}'")

        # Procesar las filas del archivo
        for _, row in df.iterrows():
            # Buscar o crear producto
            product = self.env['product.product'].search([('default_code', '=', row['CODIGO'])], limit=1)
            if not product:
                product = self.env['product.product'].create({
                    'name': row['DESCRIPCION'],
                    'default_code': row['CODIGO'],
                    'list_price': row['SUBTOTAL UNIDAD'],  # Precio base
                })

            # Calcular subtotal y validar
            calculated_subtotal = row['CANTIDAD'] * row['SUBTOTAL UNIDAD']
            if calculated_subtotal != row['SUBTOTAL']:
                raise UserError(
                    f"El subtotal calculado ({calculated_subtotal}) no coincide con el valor en el archivo ({row['SUBTOTAL']})."
                )

            # Crear línea de pedido
            self.order_id.order_line.create({
                'order_id': self.order_id.id,
                'product_id': product.id,
                'product_uom_qty': row['CANTIDAD'],
                'price_unit': row['SUBTOTAL UNIDAD'],
                'x_studio_tipologia': row['TIPOLOGIA'],
                'x_studio_precio_unitario_carpinteria': row['PRECIO UNITARIO CARPINTERIA'],
                'x_studio_codigo_distancia': row['CODIGO DISTANCIA /KM'],
                'x_studio_precio_unitario_instalacion': row['PRECIO UNITARIO INSTALACION'],
            })

        return {'type': 'ir.actions.act_window_close'}
