import requests
import re
import smtplib
import json
import datetime
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup


PRICE_THRESHOLD_DEFAULT = 10.0
LOGS_DIR = os.path.join(os.getcwd(), "Logs")
os.makedirs(LOGS_DIR, exist_ok=True)
DAYS_SINCE_LAST_MAIL = 5  # Número de días para evitar enviar correos duplicados

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

# SMTP configuration
with open("credentials.json", "r", encoding="utf-8") as f:
    creds = json.load(f)

RECIPIENT = creds["mail_adress_destination"]
SMTP_USER = creds["mail_adress_sender"]
SMTP_PASS = creds["app_password"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

 # Cambia este valor al precio máximo que deseas

def get_price_and_title(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
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
                price = float(price_num[0].replace(",", "."))
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
    subject = f"Game Tracker - {title} at {price}€"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_body = f"""
    <html>
      <body>
        <h2>Game Tracker Notification</h2>
        <p><strong>Game:</strong> {title}</p>
        <p><strong>Price:</strong> {price}€</p>
        <p><strong>URL:</strong> <a href="{url}">{url}</a></p>
        <p><strong>Date:</strong> {now}</p>
        <hr>
        <p>This is an automated notification from your price tracker.</p>
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

def send_weekly_summary(games_data, log_file):
    """Send weekly price summary every Sunday"""
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
        <h2>🎮 Weekly Game Price Summary</h2>
        <p><strong>Date:</strong> {today.strftime('%d-%m-%Y')}</p>
        <p><strong>Total Games Tracked:</strong> {len(games_data)}</p>
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

if __name__ == "__main__":
    log_file = os.path.join(LOGS_DIR, "gameLogs.txt")
    
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
                'status': status
            })
        else:
            games_data.append({
                'name': product_name if product_name else "Unknown Game",
                'price': 'N/A',
                'threshold': threshold,
                'url': url,
                'status': '⚠️ Price not found'
            })
        
        # Regular price checking logic
        if price is not None and title:
            print_log(f"The game {product_name} has a price of {price}€", file=log_file)
            if price <= threshold:
                print_text = f"Notification sent: {product_name}"
                if not was_email_sent_recently(text_to_check=print_text, log_file=log_file):
                    send_email_smtp(price, url, product_name)
                    print_log(print_text + f" at {price}€.", file=log_file)
                else:
                    print_log(f"Email already sent for {product_name} at {price}€ in the last {DAYS_SINCE_LAST_MAIL} days.", file=log_file)
        elif price is None:
            print_log(f"No price found for the product {product_name}.", file=log_file)

    # Send weekly summary if it's Sunday (pass the already collected data)
    send_weekly_summary(games_data, log_file)