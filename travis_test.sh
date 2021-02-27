#!/usr/bin/env bash
# eliminar todos los archivos menos .git
rm -r ~/tmp/test_travis/*
# publicar el repo
sudo rsync -avz --exclude={'.git','.pyc','__pycache__/*'} /odoo_ar/odoo-11.0/gabriel/sources/san-gabriel/ ~/tmp/test_travis

git -C ~/tmp/test_travis add .
git -C ~/tmp/test_travis commit -m "[ADD] san gabriel"
git -C ~/tmp/test_travis push
