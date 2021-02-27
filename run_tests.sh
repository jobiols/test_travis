#!/bin/sh
# correr localmente todos los tests
# ---------------------------------

BASE='/odoo_ar/odoo-11.0/gabriel'

# restaurar la base de test vacia
cp $BASE/backup_dir/bkp_test/gabriel_test.zip $BASE/backup_dir/
oe --restore -d gabriel_test -c gabriel -f gabriel_test.zip
rm $BASE/backup_dir/gabriel_test.zip

# correr los tests
sudo docker run --rm -it \
    -v $BASE/config:/opt/odoo/etc/ \
    -v $BASE/data_dir:/opt/odoo/data \
    -v $BASE/sources:/opt/odoo/custom-addons \
    --link pg-gabriel:db \
    --name gabriel \
    jobiols/odoo-jeo:11.0 -- \
        --stop-after-init \
        -d gabriel_test \
        -i custom_health
#        --test-enable
