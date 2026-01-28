# InstantGaming Price Tracker and Email Notifier
This Python script monitors a list of InstantGaming product URLs, checks their prices against custom thresholds, and sends automated HTML email notifications when prices drop below your specified limits. It also sends a weekly summary every Sunday. All activity is logged to a file.

You can schedule a task so this script is run periodically, this way you will get a notification every time one of your wished games reaches your target price.

## How It Works

1. **Product URLs and Thresholds:**  
   The script reads game URLs and price thresholds from a file called `games.txt`. Each game requires two lines: the URL and the maximum price you're willing to pay.

2. **Credentials:**  
   Email credentials and recipient information are stored in a file called `credentials.json`. This file must be present in the same directory as the script.

3. **Price Check:**  
   For each game, the script checks if the current price is at or below your threshold. If so, an email notification is sent (maximum once every 2 days per game to avoid spam).

4. **Weekly Summary:**  
   Every Sunday, the script sends a comprehensive email with all tracked games, their current prices, and status.

5. **Email Notification:**  
   Emails are sent using Gmail's SMTP server and contain game details, current price, and a clickable link.

6. **Logging:**  
   All actions and errors are logged to `Logs/gameLogs.txt`.

---

## Setup

### 1. `credentials.json` Format

Create a file named `credentials.json` in the same directory as the script with the following structure:

```json
{
    "mail_adress_destination": "recipient@example.com",
    "mail_adress_sender": "yourgmail@gmail.com",
    "app_password": "your_gmail_app_password"
}
```

- `mail_adress_destination`: The email address where notifications will be sent.
- `mail_adress_sender`: Your Gmail address (must match the account for the app password).
- `app_password`: A Gmail App Password (not your regular Gmail password).  
  [How to generate an App Password](https://support.google.com/accounts/answer/185833?hl=en).

### 2. `games.txt` Format

Create a file named `games.txt` in the same directory as the script. For each game, add two lines:
1. The InstantGaming product URL
2. Your maximum acceptable price (in euros)

Example:

```
https://www.instant-gaming.com/es/6791-comprar-days-gone-pc-juego-steam/
12
https://www.instant-gaming.com/es/15381-comprar-borderlands-4-pc-steam/
35
// This is a comment and will be ignored
https://www.instant-gaming.com/es/8260-comprar-stray-pc-mac-juego-steam-europe-us-canada/
10
```

- Blank lines and lines starting with `//` are ignored.
- If a threshold is missing or invalid, the default value (10.0€) is used.

---

## Usage

1. Install dependencies:
   ```bash
   pip install requests beautifulsoup4 lxml
   ```

2. Run the script:
   ```bash
   python InstantGamingPriceChecker.py
   ```

3. Check your email for:
   - **Immediate notifications** when a game drops to or below your threshold
   - **Weekly summary** every Sunday with all tracked games

4. **Automate Daily Checks:**  
   You can schedule this script to run automatically every day using your operating system's task scheduler:
   - **Windows:** Use Task Scheduler ([How to schedule a Python script on Windows](https://datatofish.com/python-script-windows-scheduler/))
   - **Linux/macOS:** Use `cron` jobs ([How to schedule a cron job](https://opensource.com/article/19/7/getting-started-cron))

   This is what I do so I don't have to run it manually.

---

## Features

- ✅ **Custom price thresholds** per game
- ✅ **Email cooldown** (notifications sent max once every 2 days per game)
- ✅ **Weekly summary** every Sunday with all tracked games
- ✅ **Detailed logging** in `Logs/gameLogs.txt`
- ✅ **HTML formatted emails** with clean, professional layout
- ✅ **Error handling** for missing prices or unavailable products

---

## Notas

- El script está configurado para Gmail SMTP. Si utilizas otro proveedor, actualiza la configuración de SMTP en el script.
- Asegúrate de que tu cuenta de Gmail tenga [habilitados las contraseñas de aplicación](https://support.google.com/accounts/answer/185833?hl=en).
- Los umbrales de precio se configuran individualmente para cada juego en `games.txt`.
- El resumen semanal se envía automáticamente todos los domingos.
- Para evitar spam, las notificaciones de precio bajo se envían como máximo una vez cada 2 días por juego.

---

## License

This project is open source and available for personal use.
