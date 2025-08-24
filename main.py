from nicegui import ui, app
import os, io, re, pandas as pd, requests

# =========================
# CONFIG
# =========================
DATA_URL = os.getenv("DATA_URL", "").strip()
DATA_FILE = os.getenv("DATA_FILE", "").strip()
REQUIRED_LETTERS = ["B","C","D","H","K","L","M","N","O","P"]

# İntersport tema renkleri
PRIMARY_BG = '#004794'   # arka plan
TEXT_COLOR = '#FFFFFF'   # metin
ACTIVE_COLOR = '#E90000' # seçili toggle / birincil buton

# =========================
# HELPERS
# =========================
def strip_accents(s: str) -> str:
    import unicodedata
    s = str(s)
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def norm_token(s: str) -> str:
    s = strip_accents(str(s)).lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

def pick(df: pd.DataFrame, key):
    if key in df.columns:
        return df[key]
    if isinstance(key, int) and str(key) in df.columns:
        return df[str(key)]
    return pd.Series([None]*len(df), index=df.index)

def map_surface(x):
    t = norm_token(x)
    if "yol" in t or "road" in t:
        return "road"
    if "patika" in t or "trail" in t:
        return "trail"
    return None

def map_goal(x):
    t = norm_token(x)
    if "yaris" in t or "race" in t:
        return "yaris"
    if "antrenman" in t or "training" in t:
        return "antrenman"
    return None

def map_durability_long(x):
    t = norm_token(x)
    return ("uzun" in t) and ("omurlu" in t or "omur" in t)

def map_distance_group(x):
    t = norm_token(x)
    if ("orta" in t and "mesafe" in t) or ("medium" in t):
        return "orta mesafe"
    if ("uzun" in t and "mesafe" in t) or ("long" in t):
        return "uzun mesafe"
    if ("kisa" in t and "mesafe" in t) or ("short" in t):
        return "kisa mesafe"
    return None

def map_injury_ok(x):
    try:
        xv = float(x)
        return abs(xv - 1.2) < 1e-6
    except Exception:
        t = norm_token(str(x))
        return ("evet" in t) or ("uygun" in t) or ("yes" in t)

def map_pronation_yes(x):
    t = norm_token(x)
    return ("evet" in t) or (t == "1") or ("yes" in t)

def excel_letter_to_name(cols, letter: str) -> str:
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    val = 0
    for ch in letter:
        val = val * 26 + (alpha.index(ch.upper()) + 1)
    idx = val - 1
    if idx < 0 or idx >= len(cols):
        raise IndexError(f"Column letter {letter} is out of range for this sheet.")
    return str(cols[idx])

def resolve_output_columns(df: pd.DataFrame):
    names = []
    for L in REQUIRED_LETTERS:
        try:
            name = excel_letter_to_name(df.columns, L)
            if name in df.columns:
                names.append(name)
        except Exception:
            pass
    return names

def build_normalized_view(df: pd.DataFrame) -> pd.DataFrame:
    dfn = df.copy()
    c1 = pick(dfn, 1).astype(str)
    c2 = pick(dfn, 2).astype(str)
    c3 = pick(dfn, 3).astype(str)
    c4 = pick(dfn, 4).astype(str)
    c5 = pick(dfn, 5).astype(str)
    c6 = pick(dfn, 6)
    c7 = pick(dfn, 7).astype(str)

    dfn["q1"] = c1.map(lambda x: "erkek" if "erkek" in norm_token(x) or "male" in norm_token(x) else ("kadin" if "kadin" in norm_token(x) or "female" in norm_token(x) else None))
    dfn["q2"] = c2.map(map_surface)
    dfn["q3"] = c3.map(map_goal)
    dfn["q4_is_long"] = c4.map(map_durability_long)
    dfn["q5_group"] = c5.map(map_distance_group)
    dfn["q6_injury_ok"] = c6.map(map_injury_ok)
    dfn["q7_pronation_yes"] = c7.map(map_pronation_yes)

    return dfn

def fix_cloud_link(url: str) -> str:
    m = re.search(r"drive\.google\.com/file/d/([^/]+)/", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"drive\.google\.com/open\?id=([^&]+)", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    if "dropbox.com" in url and "raw=1" not in url:
        if "dl=0" in url:
            url = url.replace("dl=0", "raw=1")
        else:
            url = url + ("&" if "?" in url else "?") + "raw=1"
    if "1drv.ms" in url or "onedrive.live.com" in url:
        if "download=1" not in url:
            url = url + ("&" if "?" in url else "?") + "download=1"
    return url

def load_dataset() -> pd.DataFrame:
    if DATA_URL:
        url = fix_cloud_link(DATA_URL)
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        bio = io.BytesIO(r.content)
        try:
            return pd.read_excel(bio, sheet_name="Data")
        except Exception:
            bio.seek(0)
            return pd.read_excel(bio, sheet_name="DATA")
    if DATA_FILE and os.path.exists(DATA_FILE):
        try:
            return pd.read_excel(DATA_FILE, sheet_name="Data")
        except Exception:
            return pd.read_excel(DATA_FILE, sheet_name="DATA")
    for name in ["Kod _n_ son grlsz.xlsx", "Kod _n_ son.xlsx", "Kod Önü son.xlsx", "data.xlsx"]:
        if os.path.exists(name):
            try:
                return pd.read_excel(name, sheet_name="Data")
            except Exception:
                return pd.read_excel(name, sheet_name="DATA")
    raise FileNotFoundError("Dataset not found. Set DATA_URL or DATA_FILE or place the Excel in the working dir.")

# =========================
# LOAD & NORMALIZE
# =========================
DF = load_dataset()
DFN = build_normalized_view(DF)
OUT_COLS = resolve_output_columns(DF)

# =========================
# THEME (Intersport)
# =========================
ui.page_title('Intersport Running Footwear')

# Koyu mod → açık zemin üstünde koyu bileşenleri beyaz metinle gösterir
dark = ui.dark_mode()
dark.enable()

# Global CSS (yüzde formatı ile!)
css = """
<style>
  :root {
    --brand-bg: %(bg)s;
    --brand-text: %(text)s;
    --brand-active: %(active)s;
    --radius-lg: 16px;
  }
  body { background: var(--brand-bg); color: var(--brand-text); }
  .q-header { background: var(--brand-bg) !important; color: var(--brand-text) !important; }
  .q-card { background: transparent !important; border: 1px solid rgba(255,255,255,.25); border-radius: var(--radius-lg); }
  .q-separator { background: rgba(255,255,255,.2) !important; }
  .q-btn { color: var(--brand-text); }
  .q-btn-toggle .q-btn.q-btn--active, .q-btn.q-btn--active {
    background: var(--brand-active) !important;
    color: #fff !important;
  }
  .btn-primary { background: var(--brand-active) !important; color: #fff !important; border-radius: var(--radius-lg); }
  .q-table__container { background: transparent !important; color: var(--brand-text) !important; }
  .q-table thead th { background: rgba(255,255,255,.10); color: var(--brand-text) !important; }
  .q-table tbody td { color: var(--brand-text) !important; }
  .q-table__bottom, .q-table__top { color: var(--brand-text) !important; }
</style>
""" % {"bg": PRIMARY_BG, "text": TEXT_COLOR, "active": ACTIVE_COLOR}
ui.add_head_html(css)

# =========================
# UI
# =========================
with ui.header().classes('items-center justify-between'):
    ui.label('Intersport Running Footwear').classes('text-lg md:text-xl font-semibold')
    ui.label('Koşucuya özel öneri sihirbazı').classes('text-sm opacity-90')

with ui.card().classes('max-w-2xl mx-auto mt-8'):
    ui.label('Soru 1/7 — Cinsiyet').classes('text-base font-medium')
    q1 = ui.toggle(['Erkek','Kadin']).props('dense'); q1.value = 'Erkek'

    ui.separator().classes('my-2')
    ui.label('Soru 2/7 — Zemin').classes('text-base font-medium')
    q2 = ui.toggle(['Road','Trail']).props('dense'); q2.value = 'Road'

    ui.separator().classes('my-2')
    ui.label('Soru 3/7 — Hedef').classes('text-base font-medium')
    q3 = ui.toggle(['Yaris','Antrenman']).props('dense'); q3.value = 'Yaris'

    ui.separator().classes('my-2')
    ui.label('Soru 4/7 — Haftalık sıklık').classes('text-base font-medium')
    q4 = ui.toggle(['3 ve daha az','4 ve daha fazla']).props('dense'); q4.value = '3 ve daha az'

    ui.separator().classes('my-2')
    ui.label('Soru 5/7 — Mesafe (her koşu)').classes('text-base font-medium')
    q5 = ui.toggle(['0-20 km','20 km ve daha fazla']).props('dense'); q5.value = '0-20 km'

    ui.separator().classes('my-2')
    ui.label('Soru 6/7 — Diz/Kalça sakatlığı').classes('text-base font-medium')
    q6 = ui.toggle(['Var','Yok']).props('dense'); q6.value = 'Yok'

    ui.separator().classes('my-2')
    ui.label('Soru 7/7 — Pronasyon').classes('text-base font-medium')
    q7 = ui.toggle(['Evet','Hayir']).props('dense'); q7.value = 'Hayir'

    result_area = ui.column().classes('mt-4')

    def compute():
        params = dict(gender=q1.value, surface=q2.value, goal=q3.value, freq=q4.value, distance=q5.value, injury=q6.value, pronation=q7.value)
        f = DFN.copy()
        f = f[f["q1"] == ("erkek" if params["gender"] == "Erkek" else "kadin")]
        f = f[f["q2"] == ("road" if params["surface"] == "Road" else "trail")]
        f = f[f["q3"] == ("yaris" if params["goal"] == "Yaris" else "antrenman")]
        if params["freq"] == "4 ve daha fazla":
            f = f[f["q4_is_long"] == True]
        if params["distance"] == "20 km ve daha fazla":
            f = f[f["q5_group"].isin(["orta mesafe", "uzun mesafe"])]
        if params["injury"] == "Var":
            f = f[f["q6_injury_ok"] == True]
        if params["pronation"] == "Evet":
            f = f[f["q7_pronation_yes"] == True]

        show_cols = [c for c in OUT_COLS if c in f.columns]
        with result_area:
            result_area.clear()
            ui.label(f'Toplam sonuç: {len(f)}').classes('text-sm opacity-90')
            if len(f) == 0:
                ui.label('Sonuç bulunamadı. Seçimleri değiştirip tekrar deneyin.').classes('text-red-4')
            else:
                rows = f[show_cols].to_dict(orient='records')
                columns = [{'name': c, 'label': c, 'field': c, 'sortable': True} for c in show_cols]
                ui.table(columns=columns, rows=rows).props('dense flat row-stripe').classes('w-full')

    ui.button('Önerileri Göster', on_click=compute).classes('w-full btn-primary')

import os
ui.run(host='0.0.0.0', port=int(os.getenv("PORT", "8080")), reload=False)
