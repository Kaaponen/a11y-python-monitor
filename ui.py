import streamlit as st
import asyncio
from scanner import run_axe
from sitemap import get_urls_from_sitemap
from reporter import save_report
from csv_export import save_csv
from json_export import save_json

st.set_page_config(page_title="A11y Scanner", layout="wide")
st.title("🧪 A11y Scanner – Saavutettavuustarkistin (axe-core + Python)")

mode = st.radio("Valitse tarkistusmuoto:", ["Yksittäinen URL", "Sitemap.xml"])
urls = []

if mode == "Yksittäinen URL":
    url = st.text_input("Syötä tarkistettava URL", "https://example.com")
    if url:
        urls.append(url)
else:
    sitemap_url = st.text_input(
        "Sitemap.xml osoite", "https://example.com/sitemap.xml")
    path_filter = st.text_input("Suodata polkualulla (esim. /fi/)", "")
    if st.button("Hae URL-osoitteet sitemapista"):
        with st.spinner("Haetaan sivuja..."):
            urls = get_urls_from_sitemap(sitemap_url, path_filter or None)
        st.success(f"Löytyi {len(urls)} sivua")

if urls and st.button("🚀 Skannaa saavutettavuus"):
    st.info("Skannaus käynnissä... Tämä voi kestää hetken.")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(
        asyncio.gather(*[run_axe(u) for u in urls]))
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
                    for check in node["any"]:
                        st.code(node["html"])
                        st.markdown(f"- {check['message']}")

    md_path, html_path = save_report(results_by_url)
    csv_path = save_csv(results_by_url)
    json_path = save_json(results_by_url)

    st.markdown("### 📁 Lataa raportit:")
    st.download_button("📄 Markdown", data=open(
        md_path, "rb"), file_name=md_path.name)
    st.download_button("🌐 HTML", data=open(
        html_path, "rb"), file_name=html_path.name)
    st.download_button("📊 CSV", data=open(
        csv_path, "rb"), file_name=csv_path.name)
    st.download_button("🧾 JSON", data=open(
        json_path, "rb"), file_name=json_path.name)
