ARG ODOO_VERSION
FROM ghcr.io/tecnativa/doodba:${ODOO_VERSION}-onbuild

# Ensure XlsxWriter is available in the runtime image (some addons import it via odoo.tools.misc)
RUN pip3 install --no-cache-dir XlsxWriter
