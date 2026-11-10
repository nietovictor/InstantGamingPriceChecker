import requests
import re
import smtplib
import json
import csv
import datetime
import os
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup


PRICE_THRESHOLD_DEFAULT = 10.0
LOGS_DIR = os.path.join(os.getcwd(), "Logs")
PRICE_HISTORY_FILE = os.path.join(os.getcwd(), "prices.csv")
os.makedirs(LOGS_DIR, exist_ok=True)
DAYS_SINCE_LAST_MAIL = 5  # Número de días para evitar enviar correos duplicados
GITHUB_DASHBOARD_URL = "https://nietovictor.github.io/InstantGamingPriceChecker/"
REQUEST_LANGUAGE = "es-ES,es;q=0.9,en;q=0.8"

# Read URLs and thresholds from games.txt
URLS_THRESHOLDS = []
with open("games.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip() and not line.startswith("//")]
    for i in range(0, len(lines), 2):
        url = lines[i]
        try:
            threshold = float(lines[i+1])
        except (IndexError, ValueError):
            threshold = PRICE_THRESHOLD_DEFAULT  # Usa el global si no hay threshold válido
        URLS_THRESHOLDS.append((url, threshold))

# SMTP configuration can come from the complete CREDENTIALS_JSON secret or a local file.
def load_credentials():
    credentials_json = os.getenv("CREDENTIALS_JSON")
    if credentials_json:
        try:
            credentials = json.loads(credentials_json)
        except json.JSONDecodeError as error:
            raise RuntimeError("CREDENTIALS_JSON must contain valid JSON.") from error
        if not isinstance(credentials, dict):
            raise RuntimeError("CREDENTIALS_JSON must contain a JSON object.")
        return credentials

    if os.path.exists("credentials.json"):
        with open("credentials.json", "r", encoding="utf-8") as credentials_file:
            return json.load(credentials_file)

    return {}


creds = load_credentials()
RECIPIENT = creds.get("mail_adress_destination", "")
SMTP_USER = creds.get("mail_adress_sender", "")
SMTP_PASS = creds.get("app_password", "")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

 # Cambia este valor al precio máximo que deseas

def get_price_and_title(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": REQUEST_LANGUAGE,
        "Referer": "https://www.instant-gaming.com/es/",
    }
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "lxml")
    # Precio
    price = None
    try:
        price_div = soup.find("div", class_="total")
        if price_div:
            price_text = price_div.get_text(strip=True)
            price_num = re.findall(r"[\d\.,]+", price_text)
            if price_num:
                normalized_price = price_num[0]
                if "," in normalized_price and "." in normalized_price:
                    normalized_price = normalized_price.replace(".", "").replace(",", ".")
                else:
                    normalized_price = normalized_price.replace(",", ".")
                price = float(normalized_price)
            else:
                price = None
    except Exception as e:
        print_log(f"Error extracting price: {e}", type="ERROR",file=log_file)
        price = None
    # Título
    title = ""
    try:
        # Try h1 first (more reliable)
        title_h1 = soup.find("h1")
        if title_h1:
            title = title_h1.get_text(strip=True)
        # Fallback to div.name if h1 not found
        if not title:
            title_div = soup.find("div", class_="name")
            if title_div:
                title = title_div.get_text(strip=True)
        # Clean up title (remove Vue.js variables)
        if title and "%%" in title:
            title = ""
    except Exception as e:
        print_log(f"Error extracting product title: {e}", type="ERROR", file=log_file)
        title = ""
    return price, title

def print_log(message, type="INFO", file="log.txt"):
    now = datetime.datetime.now()
    # Create the file if it doesn't exist
    try:
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            last_line = lines[-1].strip()
            last_log_date = last_line[:10]

        if last_log_date != now.strftime("%Y-%m-%d"):
            with open(file, "a", encoding="utf-8") as f:
                f.write("\n" + now.strftime("%d/%m/%Y") + "\n")
    except FileNotFoundError:
        with open(file, "w", encoding="utf-8") as f:
            f.write(now.strftime("%d/%m/%Y") + "\n")
    except Exception:
        pass

    log_line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} [{type}] {message}"
    print(log_line)

    with open(file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def send_email_smtp(price, url, title):
    if not all((RECIPIENT, SMTP_USER, SMTP_PASS)):
        print_log("SMTP not configured; email notification skipped.", type="WARNING")
        return False

    subject = f"Price Dashboard - {title} at {price}€"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_body = f"""
    <html>
      <body>
        <h2>Price Dashboard - Price Alert</h2>
        <p><strong>Game:</strong> {title}</p>
        <p><strong>Price:</strong> {price}€</p>
        <p><strong>URL:</strong> <a href="{url}">{url}</a></p>
        <p><strong>Date:</strong> {now}</p>
        <hr>
        <p>This price is at or below your configured target.</p>
        <p><a href="{GITHUB_DASHBOARD_URL}">Open the Price Dashboard</a></p>
        <p>This is an automated notification from the Price Dashboard.</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT

    # Attach HTML body
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, RECIPIENT, msg.as_string())
    return True

def send_weekly_summary(games_data, log_file):
    """Send weekly price summary every Sunday"""
    if not all((RECIPIENT, SMTP_USER, SMTP_PASS)):
        print_log("SMTP not configured; weekly summary skipped.", type="WARNING", file=log_file)
        return
    today = datetime.datetime.now()
    
    # Check if today is Sunday (weekday() returns 6 for Sunday)
    if today.weekday() != 6:
        return

    if was_email_sent_recently("Weekly summary email sent successfully", days=DAYS_SINCE_LAST_MAIL, log_file=log_file):
        print_log("Weekly summary already sent this week.", file=log_file)
        return
    
    print_log("Generating weekly summary...", file=log_file)
    
    # Create HTML email with auto-adjusting table
    subject = f"Weekly Game Price Summary - {today.strftime('%B %d, %Y')}"
    html_body = f"""
    <html>
      <body>
        <h2>Price Dashboard - Weekly Summary</h2>
        <p><strong>Date:</strong> {today.strftime('%d-%m-%Y')}</p>
        <p><strong>Total Games Tracked:</strong> {len(games_data)}</p>
        <p><a href="{GITHUB_DASHBOARD_URL}">Open the Price Dashboard</a></p>
        <hr>
        
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: auto; table-layout: auto;">
          <tr style="background-color: #f2f2f2;">
            <th style="white-space: nowrap;">Game</th>
            <th style="white-space: nowrap; text-align: center;">Current Price</th>
            <th style="white-space: nowrap; text-align: center;">Threshold</th>
            <th style="white-space: nowrap;">Status</th>
            <th style="white-space: nowrap;">Link</th>
          </tr>
    """
    
    for game in games_data:
        price_display = f"{game['price']}€" if game['price'] != 'N/A' else 'N/A'
        if game['status'].startswith("✅"):
            row_color = "#e8f5e8"
        elif game['status'].startswith("❌"):
            row_color = "#fff5f5"
        else:
            row_color = "#fff8e1"
        
        html_body += f"""
          <tr style="background-color: {row_color};">
            <td>{game['name']}</td>
            <td><strong>{price_display}</strong></td>
            <td>{game['threshold']}€</td>
            <td>{game['status']}</td>
            <td><a href="{game['url']}" target="_blank">View</a></td>
          </tr>
        """
    
    html_body += """
        </table>
        <hr>
        <p><em>This is your automated weekly game price summary.</em></p>
      </body>
    </html>
    """
    
    # Send email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(html_body, "html"))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, RECIPIENT, msg.as_string())
        
        print_log("Weekly summary email sent successfully.", file=log_file)
        
    except Exception as e:
        print_log(f"Error sending weekly summary: {e}", type="ERROR", file=log_file)

def was_email_sent_recently(text_to_check, days=DAYS_SINCE_LAST_MAIL, log_file="log.txt"):
    now = datetime.datetime.now()
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                if text_to_check in line:
                    # Extrae la fecha del log
                    date_str = line[:19]  # 'YYYY-MM-DD HH:MM:SS'
                    log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    if (now - log_date).days < days:
                        return True
                    else:
                        return False
    except Exception:
        pass
    return False


def extract_product_name(full_title):
    # Remove leading and trailing spaces
    full_title = full_title.strip()
    # Look for the first common separator
    for sep in ['|', '-', ',']:
        if sep in full_title:
            name = full_title.split(sep)[0].strip()
            return name
    # If no separator, look for the first closed parenthesis
    match = re.match(r'^([^\)]+\))', full_title)
    if match:
        return match.group(1).strip()
    # If no parenthesis, return the first 6 words as fallback
    return " ".join(full_title.split()[:6])

def load_last_notifications():
    """Read notification timestamps before replacing the current CSV snapshot."""
    notifications = {}
    try:
        with open(PRICE_HISTORY_FILE, "r", newline="", encoding="utf-8") as csv_file:
            for row in csv.DictReader(csv_file):
                if row.get("url"):
                    notifications[row["url"]] = row.get("last_notified_at", "")
    except FileNotFoundError:
        pass
    return notifications

def notification_is_due(last_notified_at, now):
    if not last_notified_at:
        return True
    try:
        last_sent = datetime.datetime.fromisoformat(last_notified_at)
    except ValueError:
        return True
    if last_sent.tzinfo is None:
        last_sent = last_sent.replace(tzinfo=datetime.timezone.utc)
    return now - last_sent >= datetime.timedelta(days=DAYS_SINCE_LAST_MAIL)

def save_price_snapshot(games_data, checked_at):
    """Replace the CSV with the latest result consumed by the dashboard."""
    fieldnames = ["checked_at", "name", "url", "threshold", "price", "status", "last_notified_at"]

    with open(PRICE_HISTORY_FILE, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for game in games_data:
            writer.writerow({
                "checked_at": checked_at,
                "name": game["name"],
                "url": game["url"],
                "threshold": game["threshold"],
                "price": game["price"] if game["price"] != "N/A" else "",
                "status": game["status"],
                "last_notified_at": game.get("last_notified_at", ""),
            })

def price_snapshot_has_changes(games_data):
    """Return whether any tracked price differs from the published snapshot."""
    def normalize_price(value):
        if value in (None, "", "N/A"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return str(value)

    previous_prices = {}
    try:
        with open(PRICE_HISTORY_FILE, "r", newline="", encoding="utf-8") as csv_file:
            for row in csv.DictReader(csv_file):
                if row.get("url"):
                    previous_prices[row["url"]] = normalize_price(row.get("price"))
    except FileNotFoundError:
        return True

    current_prices = {
        game["url"]: normalize_price(game["price"])
        for game in games_data
    }
    return current_prices != previous_prices

def load_last_checked_at():
    try:
        with open(PRICE_HISTORY_FILE, "r", newline="", encoding="utf-8") as csv_file:
            row = next(csv.DictReader(csv_file), None)
            return row.get("checked_at", "") if row else ""
    except FileNotFoundError:
        return ""

def publish_price_snapshot(log_file):
    """Commit and push the changed snapshot using the local Git configuration."""
    try:
        subprocess.run(
            ["git", "add", "--", "prices.csv"],
            check=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
        )
        staged_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", "prices.csv"],
            check=False,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
        )
        if staged_check.returncode == 0:
            latest_commit = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                check=True,
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
            ).stdout.strip()
            if latest_commit != "Update current prices":
                print_log("No changes to prices.csv to publish.", file=log_file)
                return
            print_log("No new changes to prices.csv; checking for a pending local commit.", file=log_file)
        elif staged_check.returncode == 1:
            subprocess.run(
                ["git", "commit", "-m", "Update current prices", "--", "prices.csv"],
                check=True,
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
            )
        else:
            raise RuntimeError(staged_check.stderr.strip() or "Unable to inspect staged changes.")

        subprocess.run(
            ["git", "push", "--set-upstream", "origin", "HEAD"],
            check=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
        )
        print_log("Price snapshot committed and pushed successfully.", file=log_file)
    except FileNotFoundError as error:
        raise RuntimeError("Git was not found. Install Git and run the checker inside the repository.") from error
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or error.stdout.strip() or str(error)
        raise RuntimeError(f"Unable to publish price changes with Git: {details}") from error

if __name__ == "__main__":
    log_file = os.path.join(LOGS_DIR, "gameLogs.txt")
    checked_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    checked_at_datetime = datetime.datetime.fromisoformat(checked_at)
    last_notifications = load_last_notifications()
    
    # Store all game data for weekly summary
    games_data = []
    
    for url, threshold in URLS_THRESHOLDS:
        price, title = get_price_and_title(url)
        product_name = extract_product_name(title)
        
        # Store data for weekly summary
        if price is not None:
            status = "✅ Below threshold" if price <= threshold else "❌ Above threshold"
            games_data.append({
                'name': product_name,
                'price': price,
                'threshold': threshold,
                'url': url,
                'status': status,
                'last_notified_at': last_notifications.get(url, "")
            })
        else:
            games_data.append({
                'name': product_name if product_name else "Unknown Game",
                'price': 'N/A',
                'threshold': threshold,
                'url': url,
                'status': '⚠️ Price not found',
                'last_notified_at': last_notifications.get(url, "")
            })
        
        # Regular price checking logic
        if price is not None and title:
            print_log(f"The game {product_name} has a price of {price}€", file=log_file)
            if price <= threshold:
                last_notified_at = last_notifications.get(url, "")
                if notification_is_due(last_notified_at, checked_at_datetime):
                    if send_email_smtp(price, url, product_name):
                        games_data[-1]["last_notified_at"] = checked_at
                        print_log(f"Notification sent: {product_name} at {price}€.", file=log_file)
                    else:
                        print_log(f"Notification not sent for {product_name}.", type="WARNING", file=log_file)
                else:
                    print_log(f"Email already sent for {product_name} in the last {DAYS_SINCE_LAST_MAIL} days.", file=log_file)
        elif price is None:
            print_log(f"No price found for the product {product_name}.", file=log_file)

    prices_changed = price_snapshot_has_changes(games_data)
    snapshot_checked_at = checked_at if prices_changed else (load_last_checked_at() or checked_at)
    save_price_snapshot(games_data, snapshot_checked_at)
    print_log(f"Latest price snapshot saved to {PRICE_HISTORY_FILE}.", file=log_file)
    publish_price_snapshot(log_file)

    # Send weekly summary if it's Sunday (pass the already collected data)
    send_weekly_summary(games_data, log_file)