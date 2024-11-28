{
    'name': 'Importar Líneas de Pedido desde Excel',
    'version': '1.0',
    'author': 'Tu Nombre',
    'category': 'Sales',
    'summary': 'Importa líneas de pedido desde un archivo Excel en las órdenes de venta.',
    'depends': ['sale', 'base'],
    'data': [
        'views/sale_order_views.xml',
        'views/sale_order_line_import_wizard_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': False,
    'external_dependencies':{'python':['pandas','openpyxl']}
}
