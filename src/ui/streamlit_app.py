import streamlit as st
import asyncio
import sys
import os
from urllib.parse import urlparse

# Lisää juurihakemisto sys.pathiin
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.scanner.core import run_axe
from src.scanner.sitemap import get_urls_from_sitemap
from src.reports.reporter import save_report
from src.reports.csv_export import save_csv
from src.reports.json_export import save_json


def normalize_url(url):
    """Normalize URL to ensure it has a proper protocol"""
    if not url:
        return url
    
    url = url.strip()
    if not url:
        return url
    
    # Check if URL already has a protocol
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https'):
        return url
    elif not parsed.scheme:
        # No protocol, add https://
        return f"https://{url}"
    else:
        # Invalid protocol, skip this URL
        return None


def validate_and_filter_urls(urls):
    """Validate and filter URLs to ensure they're properly formatted"""
    valid_urls = []
    for url in urls:
        normalized = normalize_url(url)
        if normalized:
            valid_urls.append(normalized)
        else:
            st.warning(f"Ohitettu epäkelpo URL: {url}")
    return valid_urls

st.set_page_config(page_title="A11y Scanner", layout="wide")
st.title("🧪 A11y Scanner – Saavutettavuustarkistin (axe-core + Python)")

# Asetukset sivupalkki
with st.sidebar:
    st.header("⚙️ Asetukset")
    
    # Screenshot settings
    st.subheader("📸 Kuvakaappaukset")
    enable_screenshots = st.checkbox("Ota kuvakaappauksia virheellisistä elementeistä", value=False)
    
    if enable_screenshots:
        highlight_violations = st.checkbox("Korosta virheelliset elementit", value=True)
        element_padding = st.slider("Elementin padding (px)", min_value=0, max_value=50, value=20)
        max_screenshots = st.slider("Max kuvakaappauksia per virhe", min_value=1, max_value=10, value=3)
        capture_overview = st.checkbox("Ota yleiskuva sivusta", value=True)
    
    # Advanced settings
    st.subheader("🔧 Lisäasetukset")
    scan_timeout = st.slider("Skannauksen timeout (s)", min_value=10, max_value=120, value=30)

mode = st.radio("Valitse tarkistusmuoto:", ["Yksittäinen URL", "Sitemap.xml"])
urls = []

if mode == "Yksittäinen URL":
    url = st.text_input("Syötä tarkistettava URL", "https://example.com")
    if url:
        normalized_url = normalize_url(url)
        if normalized_url:
            urls.append(normalized_url)
        else:
            st.error(f"Epäkelpo URL: {url}")
else:
    sitemap_url = st.text_input(
        "Sitemap.xml osoite", "https://example.com/sitemap.xml")
    path_filter = st.text_input("Suodata polkualulla (esim. /fi/)", "")
    if st.button("Hae URL-osoitteet sitemapista"):
        with st.spinner("Haetaan sivuja..."):
            raw_urls = get_urls_from_sitemap(sitemap_url, path_filter or None)
            urls = validate_and_filter_urls(raw_urls)
        st.success(f"Löytyi {len(urls)} kelvollista sivua ({len(raw_urls)} yhteensä)")

if urls and st.button("🚀 Skannaa saavutettavuus"):
    st.info("Skannaus käynnissä... Tämä voi kestää hetken.")
    
    # Näytä skandattavat URL:t debuggausta varten
    with st.expander("Skannattavat URL:t"):
        for i, url in enumerate(urls[:10], 1):  # Näytä max 10 ensimmäistä
            st.write(f"{i}. {url}")
        if len(urls) > 10:
            st.write(f"... ja {len(urls) - 10} muuta")
    
    # Configure screenshot settings
    screenshot_config = None
    if enable_screenshots:
        screenshot_config = {
            'output_dir': 'reports/screenshots',
            'highlight_violations': highlight_violations,
            'element_padding': element_padding,
            'max_screenshots_per_node': max_screenshots,
            'max_nodes_per_violation': 3,
            'capture_overview': capture_overview,
            'image_format': 'png'
        }
        st.info(f"📸 Kuvakaappaukset käytössä (max {max_screenshots} per virhe)")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        results = loop.run_until_complete(
            asyncio.gather(*[
                run_axe(
                    u, 
                    timeout=scan_timeout,
                    capture_screenshots=enable_screenshots,
                    screenshot_config=screenshot_config
                ) for u in urls
            ])
        )
        results_by_url = dict(zip(urls, results))

        st.success("✅ Skannaus valmis!")
        for url, result in results_by_url.items():
            st.subheader(url)
            if not result.get("violations"):
                st.markdown("✅ Ei saavutettavuusvirheitä!")
            else:
                for v in result["violations"]:
                    st.markdown(
                        f"**❌ {v['help']}**  \n[{v['helpUrl']}]({v['helpUrl']})")
                    for node in v["nodes"]:
                        # Näytä kuvakaappaus jos saatavilla
                        if "screenshot" in node:
                            st.markdown("**🖼️ Kuvakaappaus elementistä:**")
                            try:
                                import base64
                                screenshot_data = base64.b64decode(node["screenshot"])
                                st.image(screenshot_data, caption=f"Virhe: {v['id']}", use_column_width=True)
                            except Exception as e:
                                st.warning(f"Kuvakaappauksen näyttäminen epäonnistui: {e}")
                        
                        st.code(node["html"])
                        for check in node["any"]:
                            st.markdown(f"- {check['message']}")

        md_path, html_path = save_report(results_by_url)
        csv_path = save_csv(results_by_url)
        json_path = save_json(results_by_url)

        st.markdown("### 📁 Lataa raportit:")
        
        # Extract filenames from paths
        import os
        st.download_button("📄 Markdown", data=open(
            md_path, "rb"), file_name=os.path.basename(md_path))
        st.download_button("🌐 HTML", data=open(
            html_path, "rb"), file_name=os.path.basename(html_path))
        st.download_button("📊 CSV", data=open(
            csv_path, "rb"), file_name=os.path.basename(csv_path))
        st.download_button("🧾 JSON", data=open(
            json_path, "rb"), file_name=os.path.basename(json_path))
        
    except Exception as e:
        st.error(f"Virhe skannauksessa: {str(e)}")
        st.write("Tarkista että URL:t ovat oikeassa muodossa (esim. https://example.com)")
        
        # Lisää debugging tietoa
        with st.expander("Debugging tiedot"):
            st.write(f"**Virhe tyyppi:** {type(e).__name__}")
            st.write(f"**Virhe viesti:** {str(e)}")
            st.write(f"**URL määrä:** {len(urls)}")
            st.write(f"**Ensimmäinen URL:** {urls[0] if urls else 'Ei URL:ja'}")
    finally:
        loop.close()
