# RENDER ORCHESTRATOR — Monitoreo DSNC 360

Primera versión de inventario de cuatro cuentas Render y cuatro Neon. Solo lectura. FastAPI y panel HTML responsive. No incluye aún alertas, persistencia histórica, porcentajes de facturación, migraciones o agente local.

## Configuración
Configurar las variables de .env.example como secretos del servicio Render. No subir credenciales a GitHub. ADMIN_PASSWORD debe ser una contraseña larga y aleatoria; usuario admin. HTTPS obligatorio. Las conexiones de ChatGPT no proporcionan credenciales al servicio autónomo.

## Ejecución
`pip install -r requirements.txt`

`uvicorn main:app --host 0.0.0.0 --port 8000`

Consulta de proveedores cada cinco minutos mientras el proceso esté activo. Las instancias gratuitas pueden suspenderse; no garantizan monitoreo continuo. El endpoint /healthz solo verifica el proceso. /api/monitor y / requieren autenticación. Los datos se mantienen en memoria; no son históricos. No se cambian servicios ni bases de datos operativas.
