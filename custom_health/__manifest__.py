##############################################################################
#
#    Desarrollado por Quilsoft para Instituto San Gabriel
#    2021 All Rights Reserved.
#
##############################################################################

{
    'name': 'Custom Health',
    'version': '11.0.1.0.0',
    'category': 'Generic Modules/Medical',
    'summary': "Customización para San Gabriel",
    'author': "Quilsoft",
    'website': 'http://gitlab.com/Quilsoft/salud',
    'license': 'AGPL-3',
    'depends': [
        'oehealth_all_in_one'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/social_work.xml',
        'views/views.xml'
    ],
    'external_dependencies': {
    },
    'installable': True,
}
