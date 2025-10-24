import requests
import xml.etree.ElementTree as ET

def get_urls_from_sitemap(sitemap_url, prefix_filter=None):
    urls = []
    def parse_sitemap(url):
        r = requests.get(url)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        if root.tag.endswith("sitemapindex"):
            for sitemap in root.findall("ns:sitemap", ns):
                loc = sitemap.find("ns:loc", ns)
                if loc is not None:
                    urls.extend(parse_sitemap(loc.text))
        else:
            for url_tag in root.findall("ns:url", ns):
                loc = url_tag.find("ns:loc", ns)
                if loc is not None:
                    if not prefix_filter or loc.text.startswith(prefix_filter):
                        urls.append(loc.text)
        return urls

    return parse_sitemap(sitemap_url)
