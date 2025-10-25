# Saavutettavuusskanneri 🔍

Moderni Python-pohjainen saavutettavuustyökalu, joka käyttää Playwright-selainta ja axe-core-kirjastoa web-sivujen automaattiseen saavutettavuustarkistukseen.

## ✨ Ominaisuudet

- 🚀 **Nopea skannaus** - Playwright + axe-core yhdistelmä
- 📊 **Monipuoliset raportit** - HTML, Markdown, CSV ja JSON 
- 🌐 **Web UI** - Streamlit-pohjainen käyttöliittymä
- 💻 **CLI-tuki** - Komentorivikäyttö automatisoinnille
- 🗺️ **Sitemap-tuki** - Koko sivuston skannaus kerralla
- 🤖 **AI-analyysi** - GPT-4o alt-tekstien arviointi
- � **Kuvakaappaukset** - Visuaalinen elementtien tunnistus virheistä
- �🐳 **Docker-tuki** - Helppo käyttöönotto
- 🏥 **Terveydenvalvonta** - Reaaliaikainen suorituskyvyn seuranta
- 📈 **Mittaristo** - Yksityiskohtaiset mittarit ja tilastot
- 🔍 **Strukturoitu lokitus** - JSON-muotoinen lokitus ja virheenseuranta

### 🚀 **Uudet suorituskykyparannukset:**
- ⚡ **Redis-välimuisti** - 60-80% nopeampi skannaus toistuvilla sivuilla
- 🛡️ **Rate limiting** - API-kutsujen älykkäs rajoitus ja räjähdyssuojaus
- 🔗 **Connection pooling** - 70% vähemmän verkkolatenssia
- 💾 **Memory optimization** - 30-50% vähemmä muistinkäyttöä
- � **Performance monitoring** - Reaaliaikainen suorituskyvyn seuranta

## �🚀 Pika-asennus

```bash
# Kloonaa repo
git clone https://github.com/yourusername/saavutettavuusskanneri.git
cd saavutettavuusskanneri

# Asenna riippuvuudet
make install

# Kopioi ympäristöasetukset
cp .env.example .env

# Käynnistä web UI
make run-ui
```

## 📦 Asennus

### Perusasennus

```bash
pip install -r requirements.txt
playwright install
```

### Suorituskykyparannukset (valinnainen)

```bash
# Redis-välimuisti (suositeltu)
pip install redis aioredis

# Suorituskykykirjastot
pip install uvloop orjson psutil aiohttp
```

### Kehitysasennus

```bash
make install-dev
```

## 🔧 Käyttö

### Komentorivikäyttöliittymä (CLI)

```bash
# Skannaa yksittäinen sivu
python3 cli.py scan https://example.com

# Skannaa kuvakaappausten kanssa
python3 cli.py scan https://example.com --screenshots --max-screenshots 5

# Skannaa sivusto sitemapista
python3 cli.py scan --sitemap https://example.com/sitemap.xml

# Tarkista terveydenvalvonta
python3 cli.py health status

# Käynnistä terveydenvalvonta
python3 cli.py health start-monitoring

# Näytä suorituskykymittarit
python3 cli.py health metrics --hours 24

# Suorituskykyparannukset
python3 cli.py performance overview
python3 cli.py performance cache status
python3 cli.py performance memory status

# Turvallisuus
python3 cli.py security status
python3 cli.py security scan-dependencies
```

### Web-käyttöliittymä

```bash
# Uusi suositeltu tapa

# Tai suoraan Streamlitilla
streamlit run src/ui/streamlit_app.py
# Avaa selaimessa: http://localhost:8501
```

### Komentorivi

Yksittäisen sivun skannaus:
```bash
python cli.py scan https://example.com
```

Sitemap-pohjainen skannaus:
```bash
python cli.py scan --sitemap https://example.com/sitemap.xml --filter /fi/
```

### Docker

```bash
make docker-build
make docker-run
```

## ⚡ Suorituskykyominaisuudet

### Cache-hallinta
```bash
# Tarkista cache-tila
python cli.py performance cache status

# Tyhjennä välimuisti
python cli.py performance cache clear

# Näytä tilastot
python cli.py performance overview
```

### Memory-optimointi
```bash
# Muistin tila
python cli.py performance memory status

# Pakota muistin siivous
python cli.py performance memory cleanup

# Käynnistä automaattinen optimointi
python cli.py performance memory start
```

### Rate limiting
```bash
# Rate limiting -tila
python cli.py performance ratelimit status

# Nollaa rate limits
python cli.py performance ratelimit reset
```

## 📸 Kuvakaappausominaisuus

Skanneri voi ottaa kuvakaappauksia saavutettavuusvirheiden elementeistä paremman visuaalisen tunnistamisen mahdollistamiseksi.

### CLI-käyttö

```bash
# Ota kuvakaappaukset käyttöön
python3 cli.py scan https://example.com --screenshots

# Määritä kuvakaappausten enimmäismäärä
python3 cli.py scan https://example.com --screenshots --max-screenshots 10

# Määritä kuvakaappausten tallennushakemisto
python3 cli.py scan https://example.com --screenshots --screenshot-dir custom/path
```

### Web UI -käyttö

Streamlit-käyttöliittymässä kuvakaappaukset voi ottaa käyttöön sivupalkista:
- ✅ **Ota kuvakaappaukset** - Käyttöönotto/pois päältä
- 🎨 **Korosta virhe-elementit** - Värikoodattu korostus
- 📏 **Elementin padding** - Kuvan reunamarginaali (pikseleinä)
- 🔢 **Max kuvakaappauksia** - Enimmäismäärä per skannaus

### Visuaalinen korostus

Elementit korostetaan automaattisesti vaikavuuden mukaan:
- 🔴 **Kriittinen** - Punainen reunus (#ff0000)
- 🟠 **Vakava** - Oranssi reunus (#ff6600)
- 🟡 **Kohtalainen** - Keltainen reunus (#ffcc00)
- 🔵 **Vähäinen** - Sininen reunus (#0066ff)

### Raportit

Kuvakaappaukset sisällytetään automaattisesti:

- **HTML-raportteihin** - Upotetut base64-kuvat
- **Markdown-raportteihin** - Base64-linkit
- **Web UI:hin** - Reaaliaikainen näyttö

### Esimerkki käytöstä

Kuvakaappausominaisuus on erityisen hyödyllinen tunnistettaessa:
- Tyhjät linkit (kuten `<a href="..."></a>`)
- Puuttuvat alt-tekstit kuvissa
- Kontrastivirheet
- Lomakeelementit ilman label-tekstejä

```bash
# Esimerkkiskannaus joka löytää tyhjän LinkedIn-linkin
python3 cli.py scan https://lahtinen.me --screenshots
# Tuloksena: kuvakaappaus oranssilla reunuksella korostetusta tyhjästä linkistä
```

## ⚙️ Konfigurointi

Kopioi `.env.example` → `.env` ja täytä tarvittavat arvot:

```bash
# OpenAI API-avain alt-tekstien analysointiin
OPENAI_API_KEY=your_key_here

# Tulosteen hakemisto
OUTPUT_DIR=reports

# Lokitustaso
LOG_LEVEL=INFO
```

## 🧪 Testaus

```bash
# Aja testit
make test

# Testikattavuus
make test-coverage

# Koodin laatu
make lint
make format
```

## 📂 Projektin rakenne

```text
saavutettavuusskanneri/
├── app.py                  # Uusi pääkäynnistin (Streamlit UI)
├── cli.py                  # Komentoriviasä
├── config.py               # Konfiguraatio
├── utils.py                # Yleiset apufunktiot
├── src/                    # Päälähdekoodit
│   ├── __init__.py
│   ├── scanner/            # Skannaustoiminnot
│   │   ├── __init__.py
│   │   ├── core.py         # Pääskannauslogiikka (ent. scanner.py)
│   │   └── sitemap.py      # Sitemap-käsittely
│   ├── reports/            # Raportointi
│   │   ├── __init__.py
│   │   ├── reporter.py     # HTML/MD raportit
│   │   ├── csv_export.py   # CSV-vienti
│   │   └── json_export.py  # JSON-vienti
│   ├── analysis/           # AI-analyysi
│   │   ├── __init__.py
│   │   └── alt_analysis.py # Alt-tekstien analyysi (ent. backend/)
│   └── ui/                 # Käyttöliittymä
│       ├── __init__.py
│       ├── streamlit_app.py # Streamlit sovellus (ent. ui.py)
│       └── components/      # UI-komponentit
│           ├── __init__.py
│           └── alt-analysis.py
├── tests/                  # Yksikkötestit
│   ├── __init__.py
│   └── test_scanner.py
├── reports/                # Generoidut raportit
├── backend/                # [DEPRECATED - Poistetaan]
└── components/             # [DEPRECATED - Poistetaan]
```

## 🔍 API-dokumentaatio

### Scanner API

```python
from src.scanner.core import run_axe
import asyncio

# Skannaa sivu
result = asyncio.run(run_axe("https://example.com"))
```

### Sitemap API

```python
from src.scanner.sitemap import get_urls_from_sitemap

# Hae URL:t sitemapista
urls = get_urls_from_sitemap("https://example.com/sitemap.xml", "/fi/")
```

## 🤝 Kehittäminen

1. **Fork** projektia
2. **Luo** feature branch (`git checkout -b feature/amazing-feature`)
3. **Commitoi** muutokset (`git commit -m 'Add amazing feature'`)
4. **Push** branchiin (`git push origin feature/amazing-feature`)
5. **Avaa** Pull Request

### Kehitystyökalut

```bash
# Formatoi koodi
make format

# Tarkista koodin laatu
make lint

# Aja testit
make test
```

## 📄 Lisenssi

MIT License - katso [LICENSE](LICENSE) tiedosto.

## 🐛 Bugit ja feature-pyynnöt

Käytä [GitHub Issues](https://github.com/yourusername/saavutettavuusskanneri/issues) raportoidaksesi bugeja tai pyytääksesi uusia ominaisuuksia.

## 🏆 Kiitokset

- [axe-core](https://github.com/dequelabs/axe-core) - Saavutettavuustestaus
- [Playwright](https://playwright.dev/) - Selainotomaatio
- [Streamlit](https://streamlit.io/) - Web UI framework
