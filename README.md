# A11y Scanner

Python-pohjainen saavutettavuustyökalu, joka käyttää Playwrightia ja axe-corea sivujen skannaamiseen.

## Asennus

```bash
pip install -r requirements.txt
playwright install
```

## Käyttö

Yksittäisen sivun skannaus:
```bash
python cli.py https://example.com
```

Sivuston skannaus sitemap.xml-tiedoston perusteella:
```bash
python cli.py --sitemap https://example.com/sitemap.xml --filter /fi/
```
