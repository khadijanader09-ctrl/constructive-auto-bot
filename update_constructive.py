import cloudscraper
from bs4 import BeautifulSoup
import feedparser
import os
import datetime
import re
import random
import json

# --- CONFIGURATION ---
MY_SITE_URL = "https://constructivevoice.com"
AUTHORITY_RSS = "https://news.google.com/rss/search?q=construction+architecture+industry&hl=en-US&gl=US&ceid=US:en"
OUTPUT_FILE = "public/index.html"

# Images bannies
EXCLUDED_IMGS = ["placeholder", "logo.svg", "default", "blank", "1x1", "pixel"]

# Images HD de Secours
THEMATIC_IMAGES = [
    "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1581094794329-cd56b50d068e?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1590644365607-1c5a29bf42f7?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1531834685032-c34bf0d84c77?auto=format&fit=crop&w=600&q=80",
    "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=600&q=80"
]
FALLBACK_IMG = "https://constructivevoice.com/assets/placeholder.jpg"

# SEO
SEO_DESC = "Breaking news from the construction world, architecture updates and global industry events. Curated by AI."
SEO_KEYWORDS = "construction news, architecture, green energy, engineering, constructive voice, global news"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

# Variable globale pour stocker les catégories trouvées
FOUND_CATEGORIES = {}

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    return text[:130] + "..."

def get_external_news(rss_url, limit=6):
    print(f"   -> 🌍 Google News...")
    try:
        response = scraper.get(rss_url)
        feed = feedparser.parse(response.content)
        links = []
        if not feed.entries: return []

        for entry in feed.entries:
            img_src = random.choice(THEMATIC_IMAGES)
            desc = clean_html(entry.description) if hasattr(entry, 'description') else ""
            
            links.append({
                'title': entry.title, 
                'link': entry.link, 
                'img': img_src, 
                'desc': desc,
                'source': 'Global News',
                'is_mine': False,
                'date': datetime.datetime.now().isoformat()
            })
            if len(links) >= limit: break
        return links
    except Exception as e:
        print(f"      [!] Erreur Google: {e}")
        return []

def get_my_links():
    print(f"   -> 🏠 ConstructiveVoice (Mode Sécurisé)...")
    try:
        response = scraper.get(MY_SITE_URL)
        response.encoding = 'utf-8'
        
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, 'html.parser')
        my_links = []
        
        cards = soup.find_all(['div', 'article'], class_=lambda x: x and ('card' in x or 'post' in x))
        
        for card in cards:
            # 1. Extraction Lien & Titre (Safe Mode)
            link_tag = card.find('a')
            if not link_tag: continue
            
            url = link_tag.get('href') # .get() ne plante jamais, renvoie None si vide
            if not url: continue
            if url.startswith('/'): url = MY_SITE_URL + url
            
            title_tag = card.find(['h3', 'h2', 'h4'])
            title = title_tag.get_text().strip() if title_tag else link_tag.get_text().strip()
            if len(title) < 5: continue

            # 2. Extraction Image (Safe Mode)
            img_tag = card.find('img')
            if not img_tag: continue 
            img_src = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-original')
            if not img_src: continue
            if img_src.startswith('/'): img_src = MY_SITE_URL + img_src
            
            # Filtre images bannies
            is_bad = False
            for bad in EXCLUDED_IMGS:
                if bad in img_src: is_bad = True
            if is_bad: continue

            # 3. Extraction Catégorie (Blindage Anti-Crash)
            try:
                cat_elem = card.find('a', class_='cat-link')
                
                # Si pas trouvé, on cherche un badge
                if not cat_elem:
                    cat_elem = card.find(class_='badge')
                
                # Si on a trouvé un élément, on essaie de lire ses infos
                if cat_elem:
                    # On utilise .get() pour ne pas planter si href manque
                    c_link = cat_elem.get('href')
                    c_name = cat_elem.get_text().strip()
                    
                    if c_link and len(c_name) > 2:
                        if c_link.startswith('/'): c_link = MY_SITE_URL + c_link
                        FOUND_CATEGORIES[c_name] = c_link
            except Exception:
                pass # Si l'extraction de catégorie échoue, on continue sans planter

            # 4. Description
            desc_tag = card.find('p')
            desc = ""
            if desc_tag:
                txt = desc_tag.get_text().strip()
                if len(txt) > 20: desc = txt[:120] + "..."

            # Ajout à la liste
            if not any(d['link'] == url for d in my_links):
                my_links.append({
                    'title': title, 
                    'link': url, 
                    'img': img_src,
                    'desc': desc,
                    'source': 'ConstructiveVoice',
                    'is_mine': True,
                    'date': datetime.datetime.now().isoformat()
                })

            if len(my_links) >= 6: break
        
        print(f"      > {len(my_links)} articles valides trouvés.")
        return my_links

    except Exception as e:
        print(f"      [!] Erreur scraping globale : {e}")
        return []

def generate_html():
    print("1. Génération V12 (Correction Crash)...")
    
    my_news = get_my_links()
    auth_news = get_external_news(AUTHORITY_RSS, limit=6)
    
    final_list = []
    if not my_news: my_news = []
    if not auth_news: auth_news = []
    
    max_len = max(len(my_news), len(auth_news))
    for i in range(max_len):
        if i < len(my_news): final_list.append(my_news[i])
        if i < len(auth_news): final_list.append(auth_news[i])

    now_str = datetime.datetime.now().strftime("%H:%M")
    year = datetime.datetime.now().year

    # --- TAGS DYNAMIQUES ---
    tags_html = ""
    # Si vide, on met des défauts
    if not FOUND_CATEGORIES:
        FOUND_CATEGORIES["Latest News"] = f"{MY_SITE_URL}/news_en.html"
        FOUND_CATEGORIES["Francais"] = f"{MY_SITE_URL}/news_fr.html"
        FOUND_CATEGORIES["Español"] = f"{MY_SITE_URL}/news_es.html"
    
    for name, link in FOUND_CATEGORIES.items():
        tags_html += f'<a href="{link}" target="_blank" class="footer-tag">{name}</a>'

    # JSON-LD
    json_ld = {
        "@context": "https://schema.org",
        "@type": "NewsMediaOrganization",
        "name": "ConstructiveVoice News Feed",
        "url": "https://constructivevoice-news.web.app",
        "logo": "https://constructivevoice.com/assets/logo.svg",
        "sameAs": [MY_SITE_URL]
    }
    json_ld_str = json.dumps(json_ld)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ConstructiveVoice - Global News Feed</title>
        <meta name="description" content="{SEO_DESC}">
        <meta name="keywords" content="{SEO_KEYWORDS}">
        
        <script type="application/ld+json">
        {json_ld_str}
        </script>

        <link rel="icon" href="https://constructivevoice.com/assets/favicon.svg">
        
        <style>
            :root{{
                --bg:#f6f8fb; --card:#fff; --text:#0b1020; --muted:#5c6c7e;
                --line:#e6edf5; --brand:#c62828; --brand2:#1565c0; --accent:#0b8457;
                --shadow:0 4px 12px rgba(0,0,0,0.08);
            }}
            body{{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,sans-serif}}
            a{{color:inherit;text-decoration:none;transition:color .2s}}
            a:hover{{color:var(--brand)}}
            .container{{max-width:1200px;margin:0 auto;padding:16px}}
            
            header.site{{position:sticky;top:0;z-index:50;background:var(--card);border-bottom:1px solid var(--line);}}
            .clock-row{{text-align:center;font-family:monospace;color:var(--brand);font-weight:700;padding-top:5px;font-size:.9rem}}
            .bar{{display:flex;justify-content:space-between;align-items:center;padding:10px 0}}
            .brand-link{{display:flex;align-items:center;gap:10px;font-size:1.4rem;font-weight:800;color:var(--text)}}
            .brand-link img{{width:32px;height:32px}}
            
            .links{{display:flex;justify-content:center;gap:10px;padding-bottom:15px}}
            .links a{{display:flex;flex-direction:column;align-items:center;background:var(--bg);border:1px solid var(--line);padding:6px 16px;border-radius:30px;min-width:70px}}
            .links a strong{{font-size:.9rem}}
            .links a span{{font-size:.7rem;color:var(--muted)}}
            
            .grid3{{display:grid;grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));gap:20px; margin-top:30px;}}
            
            .card{{
                background:var(--card);
                border:1px solid var(--line);
                border-radius:12px;
                overflow:hidden;
                box-shadow:var(--shadow);
                display:flex;
                flex-direction:column;
                transition:transform 0.2s;
                height: 100%;
            }}
            .card:hover{{transform: translateY(-3px);}}
            
            .card-img {{
                height: 180px; width: 100%; overflow: hidden; position: relative; background: #eee;
            }}
            .card-img img {{
                width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s;
            }}
            .card:hover .card-img img {{ transform: scale(1.05); }}
            
            .pad{{padding:15px; flex-grow:1; display:flex; flex-direction:column;}}
            .meta{{font-size:0.75rem;color:var(--muted);margin-bottom:8px;text-transform:uppercase;font-weight:bold; letter-spacing:0.5px;}}
            .card h3{{font-size:1.1rem;margin:0 0 10px 0;line-height:1.4; color:var(--text);}}
            
            .desc {{ font-size:0.9rem; color:var(--muted); line-height:1.5; margin-bottom:15px; }}
            .desc:empty {{ display: none; margin: 0; }}

            .source-tag {{ display:inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; margin-bottom: 5px; }}
            .bg-mine {{ background: #ffebee; color: var(--brand); }}
            .bg-ext {{ background: #e8f5e9; color: var(--accent); }}

            /* SECTION TAGS */
            .tags-section {{ margin-top: 60px; padding: 40px 20px; background: var(--card); border-top: 1px solid var(--line); text-align:center; }}
            .tags-title {{ font-size: 1.2rem; font-weight: 800; color: var(--text); margin-bottom: 20px; text-transform:uppercase; }}
            .tags-cloud {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; max-width: 800px; margin: 0 auto; }}
            .footer-tag {{ 
                padding: 8px 16px; background: var(--bg); border: 1px solid var(--line); 
                border-radius: 20px; font-size: 0.85rem; font-weight: 600; color: var(--muted);
                text-decoration: none;
            }}
            .footer-tag:hover {{ background: var(--brand); color: #fff; border-color: var(--brand); }}

        </style>
    </head>
    <body>

    <header class="site">
        <div class="container">
            <div class="clock-row" id="clock">{now_str} UTC</div>
            <div class="bar">
                <a href="https://constructivevoice.com" class="brand-link">
                    <img src="https://constructivevoice.com/assets/logo.svg" alt="Logo">
                    <span>ConstructiveVoice</span>
                </a>
            </div>
            <div class="links">
                <a href="https://constructivevoice.com/news_en.html"><strong>EN</strong><span>News</span></a>
                <a href="https://constructivevoice.com/news_fr.html"><strong>FR</strong><span>Actu</span></a>
                <a href="https://constructivevoice.com/news_es.html"><strong>ES</strong><span>Noticias</span></a>
                <a href="https://constructivevoice.com/news_ar.html"><strong>AR</strong><span>أخبار</span></a>
            </div>
        </div>
    </header>

    <main class="container">
        <div class="grid3">
    """

    for item in final_list:
        bg_class = "bg-mine" if item['is_mine'] else "bg-ext"
        fallback = random.choice(THEMATIC_IMAGES)
        
        html_content += f"""
        <article class="card">
            <div class="card-img">
                <a href="{item['link']}" target="_blank">
                    <img src="{item['img']}" alt="{item['title']}" loading="lazy" onerror="this.src='{fallback}'">
                </a>
            </div>
            <div class="pad">
                <div class="meta">
                    <span class="source-tag {bg_class}">{item['source']}</span>
                </div>
                <h3><a href="{item['link']}" target="_blank">{item['title']}</a></h3>
                <p class="desc">{item['desc']}</p>
            </div>
        </article>
        """

    html_content += f"""
        </div>
    </main>

    <div class="tags-section">
        <div class="tags-title">Trending Categories</div>
        <div class="tags-cloud">
            {tags_html}
        </div>
        <div style="margin-top:40px; font-size:0.8rem; color:var(--muted);">
            &copy; {year} ConstructiveVoice Global Aggregator.
        </div>
    </div>

    </body>
    </html>
    """

    if not os.path.exists("public"):
        os.makedirs("public")
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("2. HTML Généré (Fix 'href' crash).")
    return True

if __name__ == "__main__":
    if generate_html():
        os.system("firebase deploy --only hosting")