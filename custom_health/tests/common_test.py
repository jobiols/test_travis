
def create_physician(self, data=False):
    """ Crear medico """
    data = data if data else {}
    return self.env['oeh.medical.physician'].create({
        'name': 'Dr. House'
    })
