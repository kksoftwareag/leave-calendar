#!/bin/bash

set -e
cd ~ || exit

sudo apt update
sudo apt remove mysql-server mysql-client
sudo apt install libcups2-dev mariadb-client redis-server

pip install frappe-bench
bench init --skip-assets --python "$(which python)" --frappe-branch version-15 frappe-bench

mkdir ~/frappe-bench/sites/test
cp -r "${GITHUB_WORKSPACE}/.github/helpers/site_config.json" ~/frappe-bench/sites/test/


mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL character_set_server = 'utf8mb4'"
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "CREATE USER 'test_kk'@'localhost' IDENTIFIED BY 'test_kk'"
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "CREATE DATABASE test_kk"
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "GRANT ALL PRIVILEGES ON \`test_kk\`.* TO 'test_kk'@'localhost'"

mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "FLUSH PRIVILEGES"

install_whktml() {
    wget -O /tmp/wkhtmltox.tar.xz https://github.com/frappe/wkhtmltopdf/raw/master/wkhtmltox-0.12.3_linux-generic-amd64.tar.xz
    tar -xf /tmp/wkhtmltox.tar.xz -C /tmp
    sudo mv /tmp/wkhtmltox/bin/wkhtmltopdf /usr/local/bin/wkhtmltopdf
    sudo chmod o+x /usr/local/bin/wkhtmltopdf
}
install_whktml &

cd ~/frappe-bench || exit

sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

bench get-app https://github.com/frappe/erpnext --branch version-15 --resolve-deps
bench get-app --overwrite leave_calendar "${GITHUB_WORKSPACE}"
bench --verbose setup requirements --dev

bench start &>> ~/frappe-bench/bench_start.log &
CI=Yes bench build --app frappe &
bench --site test reinstall --yes

bench --verbose --site test install-app erpnext
bench --verbose --site test install-app leave_calendar