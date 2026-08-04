#!/bin/bash
cd /home/xtendoo/Documentos/odoo/19
docker compose run --rm -T odoo bash -c "odoo --test-enable --stop-after-init --workers=0 -u aicia_account_project_closure --test-tags /aicia_account_project_closure > /tmp/out.log 2>&1; echo EXIT_CODE=\$?; grep -cE 'FAIL|fail' /tmp/out.log || true; echo '---TESTS---'; grep -E 'Starting Test|FAIL|ERROR|completado|Modules loaded' /tmp/out.log | tail -25; echo '---TAIL---'; tail -5 /tmp/out.log"
