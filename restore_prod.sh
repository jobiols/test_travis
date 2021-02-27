#!/bin/sh
# Restaurar produccion
# --------------------

BASE='/odoo_ar/odoo-11.0/gabriel'

# restaurar la base de produccion
cp $BASE/backup_dir/bkp_test/gabriel_base.zip $BASE/backup_dir/
oe --restore -c gabriel -f gabriel_base.zip
rm $BASE/backup_dir/gabriel_base.zip
