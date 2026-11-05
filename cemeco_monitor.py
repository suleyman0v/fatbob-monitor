"""
cemeco.ru auksionunda Harley-Davidson Dyna Fat Bob (FXDF1580) yeni lotlarını izləyir.
Yeni lot tapılanda Telegram-a bildiriş göndərir.
"""
import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Yürüş 30 000 km-ə qədər (saytın öz filtri)
URL = ("https://cemeco.ru/auc-online/harley-davidson/dyna-fat-bob-fxdf1580/"
       "?f-st=0&f-run-to=40000")
LIST_PATH = "/auc-online/harley-davidson/dyna-fat-bob-fxdf1580/"
SEEN_FILE = "seen.json"

TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def send_telegram(text: str) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )


def load_seen() -> set:
    try:
        with open(SEEN_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen: set) -> None:
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=1)


def find_lots(html: str) -> dict:
    """Səhifədəki lot linklərini tapır: {link: qısa mətn (qiymət, yürüş və s.)}"""
    soup = BeautifulSoup(html, "html.parser")
    lots = {}
    for a in soup.find_all("a", href=True):
        full = urljoin(URL, a["href"])
        path = urlparse(full).path
        # Lot səhifəsi: siyahı ünvanından daha uzun, eyni model qovluğunda olan link
        if path.startswith(LIST_PATH) and path.rstrip("/") != LIST_PATH.rstrip("/"):
            link = full.split("?")[0]
            # Lot kartının mətni (qiymət, il, yürüş görünsün deyə)
            block = a
            for _ in range(4):
                if block.parent and len(block.parent.get_text(" ", strip=True)) < 400:
                    block = block.parent
            text = " ".join(block.get_text(" ", strip=True).split())[:300]
            if link not in lots or len(text) > len(lots[link]):
                lots[link] = text
    return lots


def main() -> None:
    r = requests.get(URL, headers=HEADERS, timeout=60)
    r.raise_for_status()
    lots = find_lots(r.text)

    if not lots:
        print("Heç bir lot linki tapılmadı (ya lot yoxdur, ya da saytın quruluşu fərqlidir).")
        return

    # Satılmış ("Продан"/"Продано") və geri götürülmüş ("Снят") lotları atırıq
    SKIP_WORDS = ("продан", "снят")
    active = {k: v for k, v in lots.items()
              if not any(w in v.lower() for w in SKIP_WORDS)}
    print(f"Cəmi {len(lots)} lot, satılmamış: {len(active)}")
    lots = active

    seen = load_seen()
    first_run = not seen
    new = {k: v for k, v in lots.items() if k not in seen}

    if new and not first_run:
        for link, info in new.items():
            send_telegram(f"🏍 Yeni Fat Bob lotu!\n\n{info}\n\n{link}")
    elif first_run:
        send_telegram(f"✅ İzləmə başladı. Hazırda {len(lots)} lot var:\n\n"
                      + "\n".join(list(lots)[:15]))

    save_seen(seen | set(lots))
    print(f"Cəmi {len(lots)} lot, yeni: {len(new)}")


if __name__ == "__main__":
    main()
