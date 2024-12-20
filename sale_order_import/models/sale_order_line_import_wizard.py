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

        # Filtrar filas no deseadas: filas vacías, cantidad igual a 0 o todas las celdas vacías (' ').
        df = df.dropna(how='all')  # Elimina filas completamente vacías.
        df = df[df['CANTIDAD'] != 0]  # Ignora filas donde 'CANTIDAD' es igual a 0.
        
        # Función para verificar si todas las celdas de una fila contienen valores vacíos o espacios.
        def is_row_invalid(row):
            return all(str(cell).strip() in ['', ' '] for cell in row)
        
        # Filtrar filas inválidas.
        df = df[~df.apply(is_row_invalid, axis=1)]
        
        
        # Validar las columnas requeridas
        required_columns = [
            'TIPOLOGIA', 'CANTIDAD', 'CODIGO', 'DESCRIPCION', 
            'PRECIO UNITARIO CARPINTERIA', 'CODIGO DISTANCIA /KM', 
            'PRECIO UNITARIO INSTALACION', 'SUBTOTAL UNIDAD', 'SUBTOTAL','NOMBRE DEL PRODUCTO'
        ]
        for column in required_columns:
            if column not in df.columns:
                raise UserError(f"El archivo Excel debe contener la columna '{column}'")

        try:
            # Convertir campos numéricos y manejar valores inválidos
            df['CANTIDAD'] = pd.to_numeric(df['CANTIDAD'], errors='coerce').fillna(0)
            df['SUBTOTAL UNIDAD'] = pd.to_numeric(df['SUBTOTAL UNIDAD'], errors='coerce').fillna(0)
            df['SUBTOTAL'] = pd.to_numeric(df['SUBTOTAL'], errors='coerce').fillna(0)
            df['PRECIO UNITARIO CARPINTERIA'] = pd.to_numeric(df['PRECIO UNITARIO CARPINTERIA'], errors='coerce').fillna(0)
        except Exception as e:
            raise UserError(f"Error procesando los campos numéricos: {str(e)}")

        # Procesar las filas del archivo
        for index, row in df.iterrows():
            ##_logger.warning(f"*************************** Index {index+1} ***************************")
            # Ignorar filas completamente vacías
            if row.isnull().all():
                ##_logger.warning(f"Fila {index + 2} ignorada porque está completamente vacía.")
                continue
            
            # Terminar la lectura si se encuentra "FIN" en la columna "TIPOLOGIA"
            if str(row['TIPOLOGIA']).strip().upper() == "FIN":
                ##_logger.warning(f"Lectura terminada al encontrar 'FIN' en la fila {index + 2}.")
                break

            
            ##_logger.warning(f"row['CODIGO']: {row['CODIGO']}")
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
                        f"Error en la fila {index + 2}."
                    )
        
            for field_name, value in required_fields.items():
                # Terminar el ciclo si se encuentra una fila completamente vacía

                ##_logger.warning(f"field_name: {field_name}.\nValor : {value}")

                if value != 0 and field_name!= 'CÓDIGO':
                    if value == '#VALUE!':
                        raise UserError(
                            f"Tenes un error  '#VALUE!' en el campo '{field_name}'. "
                            f"\nError en la fila {index + 2}."
                        )
                        
                    #if not value or str(value).strip() == '':
                    if not value:
                        raise UserError(
                            f"El campo '{field_name}' no debe estar vacío. "
                            f"Error en la fila {index + 2}."
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
                        f"Error en la fila {index + 2}."
                    )
            except ValueError as e:
                raise UserError(
                    f"Error de formato numérico en la fila {index + 2}: {e}. "
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
                    'uom_id':27,
                    'uom_po_id':27,
                    'categ_id':16036,
                    'purchase_method':"receive",
                    'list_price': subtotal_unidad,
                })

            try:
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
            except Exception as e:
                _logger.error(f"Error al crear la línea de pedido: {e}")
                raise UserError(f"Error al crear la línea de pedido en la fila {index + 2}: {e}")

        return {'type': 'ir.actions.act_window_close'}

