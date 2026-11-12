# LoL Predictor · Cloud MVP v0.7.0

## Para qué sirve
**Primer despliegue real** de consulta móvil sin depender de la PC. GitHub Actions consulta PandaScore cada 2 horas (cron aproximado, no garantiza ejecución puntual), reconstruye una página estática y la publica en GitHub Pages. Conserva la predicción auténtica ya emitida para Gen.G vs BLG, verificando su SHA-256 antes de generar la web.

**NO** emite todavía nuevas predicciones, **NO** actualiza Elo y **NO** pretende que PandaScore Fixtures provea mapas completos. Los encuentros nuevos están expresamente marcados sin pronóstico, pendientes de cobertura. No altera EXP-002, V1 ni los datos de 2026.

## Instalación en GitHub (primero crear repositorio)
1. Crea un repositorio **público** vacío para pruebas. **Advertencia:** una página GitHub Pages en plan gratuito será públicamente visible; este ZIP no contiene token ni datos personales intencionales, pero su pronóstico sí será público.
2. Sube el **contenido de esta carpeta**, conservando `.github/workflows/deploy.yml`. No subas los ZIP históricos del proyecto ni un archivo con tu token. Si usas GitHub Desktop o git, asegúrate de subir también carpetas ocultas `.github`.
3. En el repositorio: `Settings` → `Secrets and variables` → `Actions` → `New repository secret` → Name **`PANDASCORE_TOKEN`**, Value: tu token. No envíes ni pegues el token en el chat.
4. En `Settings` → `Pages` → `Build and deployment` → `Source`: **GitHub Actions**.
5. Ve a `Actions` → `Actualizar calendario y publicar piloto` → `Run workflow` y comprueba el enlace de `Pages`.

Si no quieres que el pronóstico histórico sea público, **no subas el proyecto a un repositorio público**. GitHub Free soporta Pages público en repositorios públicos; para Pages desde repos privados revisa el plan de GitHub.

## Prueba en Windows antes de desplegar (no necesita token)
Abre PowerShell en esta carpeta y ejecuta:

`python -m unittest discover -s tests -v`

Hay una prueba local offline que genera una página temporal con un fixture sintético. Puedes hacer tu propia captura con `python cloud.py --offline archivo_fixture.json --out site` si tienes un JSON de la respuesta de PandaScore.

## Limitaciones importantes
- La ejecución programada de GitHub Actions puede retrasarse o no dispararse en algunas ocasiones; **no** utilizar cron como única garantía de predicción emitida antes de partido.
- La ausencia de partidos puede reflejar cobertura insuficiente, nunca se interpreta como certidumbre de que no hay encuentros.
- `PANDASCORE_TOKEN` se mantiene en GitHub Secrets, nunca en el HTML. Un error HTTP hace fallar el job, sin publicar una actualización incorrecta.
- El historial de GitHub sirve como rastro adicional, **no** es un sello temporal externo irrefutable. El registro V1 y el pronóstico #44 permanecen intactos fuera de este paquete.
- Para emitir nuevas predicciones necesitamos una fuente de mapas por lado verificable, cobertura de liga y un mecanismo de emisión que registre cada pronóstico antes del evento. Esto será el siguiente desarrollo después de confirmar el despliegue.
