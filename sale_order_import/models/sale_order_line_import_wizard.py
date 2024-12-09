import base64
import io
import pandas as pd
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

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

        # Leer el archivo Excel desde la hoja "EXPORTACION ODOO"
        try:
            data = base64.b64decode(self.excel_file)
            file = io.BytesIO(data)
            df = pd.read_excel(file, sheet_name="EXPORTACION ODOO")
        except ValueError as e:
            raise UserError("No se encontró la hoja 'EXPORTACION ODOO' en el archivo Excel.")
        except Exception as e:
            raise UserError(f"Error al leer el archivo Excel: {str(e)}")

        # Validar las columnas requeridas
        required_columns = [
            'TIPOLOGIA', 'CANTIDAD', 'CODIGO', 'DESCRIPCION', 
            'PRECIO UNITARIO CARPINTERIA', 'CODIGO DISTANCIA /KM', 
            'PRECIO UNITARIO INSTALACION', 'SUBTOTAL UNIDAD', 'SUBTOTAL','NOMBRE DEL PRODUCTO'
        ]
        for column in required_columns:
            if column not in df.columns:
                raise UserError(f"El archivo Excel debe contener la columna '{column}'")


        

        # Procesar las filas del archivo
        for index, row in df.iterrows():
            _logger.warning(f"row['CODIGO']: {row['CODIGO']}")
            # Validar que los campos obligatorios no estén vacíos
            required_fields = {
                'CÓDIGO': row['CODIGO'],
                'CANTIDAD': row['CANTIDAD'],
                'SUBTOTAL UNIDAD': row['SUBTOTAL UNIDAD'],
                'SUBTOTAL': row['SUBTOTAL'],
                'TIPOLOGIA': row['TIPOLOGIA'],
                'PRECIO UNITARIO CARPINTERIA': row['PRECIO UNITARIO CARPINTERIA'],
                'CÓDIGO DISTANCIA /KM': row['CODIGO DISTANCIA /KM'],
                'PRECIO UNITARIO INSTALACION': row['PRECIO UNITARIO INSTALACION'],
            }

            # Validar que no sean 0
            required_not_zero = ['TIPOLOGIA', 'CODIGO', 'DESCRIPCION', 'NOMBRE DEL PRODUCTO']
            for column in required_not_zero:
                if str(row[column]).strip() == '0':
                    raise UserError(
                        f"El campo '{column}' no puede ser '0'. "
                        f"Error en la fila {index + 1}."
                    )
        
            for field_name, value in required_fields.items():
                # Terminar el ciclo si se encuentra una fila completamente vacía
                if row.isnull().all():
                    _logger.warning(f"Se encontró una fila completamente vacía en la fila {index + 1}. Terminando el proceso.")
                    break

                _logger.warning(f"field_name: {field_name}.\nValor : {value}")

                if value != 0 and field_name!= 'CÓDIGO':
                    if value == '#VALUE!':
                        raise UserError(
                            f"Tenes un error  '#VALUE!' en el campo '{field_name}'. "
                            f"\nError en la fila {index + 1}."
                        )
                        
                    if not value or str(value).strip() == '':
                        raise UserError(
                            f"El campo '{field_name}' no debe estar vacío. "
                            f"Error en la fila {index + 1}."
                        )
                
            try:
                # Convertir los campos numéricos
                cantidad = float(row['CANTIDAD'])
                subtotal_unidad = float(row['SUBTOTAL UNIDAD'])
                subtotal = float(row['SUBTOTAL'])
                precio_unitario_carp=float(row['PRECIO UNITARIO CARPINTERIA'])
        
                # Validar subtotal calculado
                calculated_subtotal = cantidad * subtotal_unidad
                if calculated_subtotal != subtotal:
                    raise UserError(
                        f"El subtotal calculado ({calculated_subtotal}) no coincide con el valor proporcionado ({subtotal}). "
                        f"Error en la fila {index + 1}."
                    )
            except ValueError as e:
                raise UserError(
                    f"Error de formato numérico en la fila {index + 1}: {e}. "
                    "Verifique que todos los campos numéricos contengan valores válidos."
                )
        
            # Buscar o crear el producto
            product = self.env['product.product'].search([('default_code', '=', row['CODIGO'])], limit=1)
            #raise UserError(f"Buscando un producto: {product}")
            if not product:
                product = self.env['product.product'].create({
                    'name': row.get('NOMBRE DEL PRODUCTO', 'Prod Finalizado sin nombre'),
                    'x_studio_descripcion': row.get('DESCRIPCION','Sin descripción'),
                    'default_code': row['CODIGO'],
                    'list_price': subtotal_unidad,
                })
        
            # Crear la línea de pedido
            self.order_id.order_line.create({
                'order_id': self.order_id.id,
                'product_id': product.id,
                'x_studio_descripcion': row.get('DESCRIPCION','Sin descripción'),
                'product_uom_qty': cantidad,
                'price_unit': subtotal_unidad,
                'x_studio_tipologia': row['TIPOLOGIA'],
                'x_studio_precio_unitario_carpinteria': precio_unitario_carp,
                'x_studio_codigo_distancia_km': row['CODIGO DISTANCIA /KM'],
                'x_studio_precio_unitario_instalacion': row['PRECIO UNITARIO INSTALACION'],
            })
        return {'type': 'ir.actions.act_window_close'}
