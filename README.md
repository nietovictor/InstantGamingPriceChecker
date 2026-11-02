# Price Dashboard

Este proyecto comprueba precios de Instant Gaming con GitHub Actions y publica un
dashboard de solo lectura mediante GitHub Pages.

## Funcionamiento

1. `games.txt` contiene una URL y un umbral de precio por juego.
2. `InstantGamingPriceChecker.py` consulta los precios.
3. Cada ejecución reemplaza `prices.csv` con el estado actual.
4. El workflow `.github/workflows/price-check.yml` guarda el CSV y despliega el dashboard.

## GitHub Actions y Pages

1. Sube el repositorio a GitHub incluyendo `games.txt`, `prices.csv`,
   `InstantGamingPriceChecker.py` y `.github/workflows/price-check.yml`.
2. En **Settings > Secrets and variables > Actions**, añade estos secretos opcionales
   si quieres recibir correos:
   - `MAIL_ADDRESS_DESTINATION`
   - `MAIL_ADDRESS_SENDER`
   - `SMTP_APP_PASSWORD`
3. En **Settings > Pages**, selecciona **GitHub Actions** como fuente.
4. Ejecuta una vez **Actions > Update prices and publish dashboard > Run workflow**.
5. El trabajo programado se ejecuta cada día a las 07:00 UTC. La URL de Pages aparece
   en el despliegue del workflow.

El sitio publicado solo contiene el dashboard y `prices.csv`. La edición de juegos,
la configuración SMTP y el scraping se ejecutan fuera de GitHub Pages.

## Uso local

Instala dependencias y ejecuta el comprobador:

```bash
pip install requests beautifulsoup4 lxml
python InstantGamingPriceChecker.py
```

Para abrir el dashboard localmente:

```bash
python -m http.server 8000
```

Después visita `http://localhost:8000/game_price_tracker_dashboard.html`.

## Formato de `games.txt`

Cada juego ocupa dos líneas:

```text
https://www.instant-gaming.com/es/6791-comprar-days-gone-pc-juego-steam/
12
```

Las líneas vacías y las que empiezan por `//` se ignoran. Si el umbral no es válido,
se utiliza el valor predeterminado de 10 euros.

## Seguridad

No subas `credentials.json` ni contraseñas al repositorio. El archivo está excluido
por `.gitignore`; para Actions utiliza únicamente GitHub Secrets.
