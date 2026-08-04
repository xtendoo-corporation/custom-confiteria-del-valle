# Kubernetes adaptation for Odoo 19

Esta carpeta contiene una primera adaptación del proyecto Doodba a Kubernetes.

## Qué se ha tomado como fuente

La adaptación parte de estos ficheros existentes del proyecto:

1. `common.yaml`
2. `devel.yaml`
3. `prod.yaml`
4. `odoo/Dockerfile`

## Criterio usado

1. Se toma `prod.yaml` como referencia funcional de producción.
2. Se toma `common.yaml` como referencia estructural de imagen, base de datos y
   persistencia.
3. Se consideran varios elementos de `devel.yaml` como exclusivos de desarrollo y por
   tanto no se trasladan tal cual a Kubernetes de producción.

## Qué se mantiene

1. Proyecto Doodba con Odoo `19.0`.
2. PostgreSQL `17`.
3. Persistencia del filestore en `/var/lib/odoo`.
4. Base de datos `prod` y usuario `odoo` como valores funcionales actuales.
5. Variables clave de producción como `DB_FILTER`, `LIST_DB` y `PGHOST`.

## Qué no se traslada tal cual

1. `odoo_proxy` con puertos locales ligados a `127.0.0.1`.
2. `pgweb`.
3. Los proxies `docker-whitelist` para destinos externos de desarrollo.
4. El modo `--workers=0 --dev=all` de `devel.yaml`.
5. Los bind mounts de `./odoo/custom` y `./odoo/auto`, porque en Kubernetes el código
   debe ir dentro de la imagen construida por Doodba.

## Ficheros incluidos

1. `values-prod.example.yaml`: base de valores Helm para un despliegue inicial.
2. `secrets-prod.example.yaml`: secretos mínimos de ejemplo para Odoo y PostgreSQL.

## Suposiciones abiertas

1. Aún falta decidir el chart Helm exacto o el repositorio del chart.
2. Aún falta confirmar el dominio final e ingress real.
3. Aún falta confirmar si PostgreSQL irá dentro del clúster o fuera.
4. Aún falta confirmar el registry final donde se publicará la imagen del proyecto.

## Siguiente uso recomendado

1. Construir la imagen del proyecto Doodba y publicarla en un registry.
2. Rellenar `values-prod.example.yaml` con el dominio, namespace, imagen y storage class
   reales.
3. Crear los secretos reales a partir de `secrets-prod.example.yaml`.
4. Ajustar recursos a la máquina final antes del primer release.
