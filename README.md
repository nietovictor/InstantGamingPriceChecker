# Price Dashboard

Este proyecto comprueba precios de Instant Gaming desde un PC local y publica un
dashboard de solo lectura mediante GitHub Pages.

## Funcionamiento

1. `games.txt` contiene una URL y un umbral de precio por juego.
2. `InstantGamingPriceChecker.py` consulta los precios.
3. Cada ejecución reemplaza `prices.csv` con el estado actual e incluye
   `last_notified_at`, la última notificación enviada para cada juego.
4. Si cambia algún precio, el comprobador crea un commit y hace `git push` usando
   la configuración local de Git. Si no cambia ningún precio, no publica nada.

Las alertas de precio se envían como máximo una vez cada 5 días por juego. Los correos
incluyen un enlace al dashboard de GitHub.

Las peticiones usan idioma español (`es-ES`) y se ejecutan desde tu conexión local,
por lo que los precios corresponden a la región de tu PC.

## GitHub Pages

1. Sube el repositorio a GitHub incluyendo `games.txt`, `prices.csv`,
   `InstantGamingPriceChecker.py` e `index.html`.
2. En **Settings > Pages**, selecciona `Deploy from a branch`, elige `main`
   y la carpeta `/ (root)`.
3. Ejecuta el comprobador en tu PC desde la carpeta del repositorio. Necesitas
   tener configurado el acceso de Git para poder hacer `git push`.

La URL pública del dashboard es:
`https://nietovictor.github.io/InstantGamingPriceChecker/`

La configuración SMTP se lee desde `credentials.json` o desde la variable
`CREDENTIALS_JSON`. El contenido esperado es:
   ```json
   {
     "mail_adress_destination": "tu-correo@gmail.com",
     "mail_adress_sender": "tu-cuenta@gmail.com",
     "app_password": "xxxx xxxx xxxx xxxx"
   }
   ```
   Sin estas credenciales se actualizarán los precios, pero no se enviarán
   notificaciones por correo.

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

Después visita `http://localhost:8000/index.html`.

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
por `.gitignore`.
