import base64
import io
import pandas as pd
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PurchaseRequisitionLineImportWizard(models.TransientModel):
    _name = 'purchase.requisition.line.import.wizard'
    _description = 'Wizard para Importar Líneas de Requisición desde Excel'

    requisition_id = fields.Many2one('purchase.requisition', string="Requisición", required=True)
    excel_file = fields.Binary(string="Archivo Excel", required=True)
    excel_filename = fields.Char(string="Nombre del Archivo")

    def action_import_requisition_lines(self):
        """Procesa el archivo Excel y crea las líneas de requisición."""
        if not self.excel_file:
            raise UserError("Por favor, carga un archivo Excel antes de importar.")

        try:
            data = base64.b64decode(self.excel_file)
            file = io.BytesIO(data)
            df = pd.read_excel(file)
        except Exception as e:
            raise UserError(f"Error al leer el archivo Excel: {str(e)}")

        # Renombrar columnas para normalizar nombres
        column_mapping = {
            'producto': 'NOMBRE',
            'cantidad': 'CANTIDAD',
            'precio unitario': 'PRECIO_UNITARIO',
            'descripcion': 'DESCRIPCION',
            'variantes': 'VARIANTES',
            'detalles': 'DETALLES'
        }
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.lower()
        df.rename(columns=column_mapping, inplace=True)
        
        # Validar columnas requeridas
        required_columns = ['NOMBRE', 'CANTIDAD', 'PRECIO_UNITARIO']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise UserError(
                f"El archivo Excel debe contener las columnas: {', '.join(missing_columns)}\n"
                f"Columnas encontradas: {', '.join(df.columns)}"
            )

        # Comprobar si existe columna para descripción de variantes
        description_column = None
        for col_name in ['DESCRIPCION', 'VARIANTES', 'DETALLES']:
            if col_name in df.columns:
                description_column = col_name
                break
        
        # Filtrar filas vacías
        df = df.dropna(subset=required_columns, how='all')
        df = df[df['CANTIDAD'] != 0]

        # Procesar filas
        for index, row in df.iterrows():
            excel_row = index + 2  # Fila real en Excel (contando encabezado)
            
            # Validar datos requeridos
            for col in required_columns:
                if pd.isna(row[col]) or (isinstance(row[col], str) and not row[col].strip()):
                    raise UserError(f"Campo '{col}' vacío en fila {excel_row}")
            
            # Obtener valores limpios
            nombre = str(row['NOMBRE']).strip()
            
            # Obtener descripción de variantes si existe
            description = ""
            if description_column:
                if not pd.isna(row[description_column]):
                    description = str(row[description_column]).strip()
            
            # Buscar producto por nombre exacto
            product = self.env['product.product'].search([
                ('name', '=', nombre)
            ], limit=1)
            
            # Si no se encuentra por nombre exacto, buscar por similitud
            if not product:
                product = self.env['product.product'].search([
                    ('name', 'ilike', nombre)
                ], limit=1)
            
            # Si aún no se encuentra, mostrar error con la línea de Excel
            if not product:
                raise UserError(
                    f"Línea {excel_row}: Producto no encontrado\n\n"
                    f"Nombre: '{nombre}'\n\n"
                    "Por favor verifique o cree el producto primero."
                )
            
            # Validar y convertir valores numéricos
            try:
                cantidad = float(row['CANTIDAD'])
                precio_unitario = float(row['PRECIO_UNITARIO'])
                
                # Validar valores positivos
                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor que 0")
                if precio_unitario < 0:
                    raise ValueError("El precio unitario no puede ser negativo")
                if cantidad < 1:
                    raise ValueError(f"La cantidad debe ser al menos 1 (valor actual: {cantidad})")
                    
            except (ValueError, TypeError) as e:
                raise UserError(
                    f"Línea {excel_row}: Error en valores numéricos\n\n"
                    f"Error: {str(e)}\n"
                    f"Cantidad: '{row['CANTIDAD']}'\n"
                    f"Precio: '{row['PRECIO_UNITARIO']}'"
                )

            # Crear línea de requisición con descripción de variantes
            self.env['purchase.requisition.line'].create({
                'requisition_id': self.requisition_id.id,
                'product_id': product.id,
                'product_qty': cantidad,
                'price_unit': precio_unitario,
                'product_description_variants': description,
            })

        return {'type': 'ir.actions.act_window_close'}