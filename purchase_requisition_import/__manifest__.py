{
    'name': 'Importar Líneas de Requerimiento desde Excel',
    'version': '1.0',
    'author': 'Joaquin',
    'category': 'Purchase',
    'summary': 'Importa líneas de pedido desde un archivo Excel en los requerimiento de compra.',
    'depends': ['purchase', 'base'],
    'data': [
        'views/purchase_requisition_views.xml',
        'views/import_wizard_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': False,
    'external_dependencies':{'python':['pandas','openpyxl']}
}
