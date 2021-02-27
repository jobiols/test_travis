# For copyright and license notices, see __manifest__.py file in module root

# Copyright 2021 jeo Software Jorge Obiols <jorge.obiols@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

#   Para correr los tests
#
#   Definir un subpackage tests que será inspeccionado automáticamente por
#   modulos de test los modulos de test deben empezar con test_ y estar
#   declarados en el __init__.py, como en cualquier package.
#
#   Hay que crear una base de datos para testing como sigue:
#   - Nombre sugerido: [nombre cliente]_test
#   - Debe ser creada con Load Demostration Data chequeado
#   - Usuario admin y password admin
#   - El modulo que se quiere testear debe estar instalado.
#
#   Arrancar el test con:
#
#   oe -Q custom_health -c atm -d atm_test

from odoo.tests.common import TransactionCase
from odoo.addons.custom_health.tests.common_test import create_physician

class TestTurnero(TransactionCase):
    """ Testea la creacion de turnos para los medicos
    """

    def setUp(self, *args, **kwargs): # noqa
        """ Setup """

        super().setUp(*args, **kwargs)

        self.physician = create_physician(self)

    def test_01_test_name(self):
        self.assertEqual(self.physician.name, 'Dr. House', 'Nombre incorrecto')
