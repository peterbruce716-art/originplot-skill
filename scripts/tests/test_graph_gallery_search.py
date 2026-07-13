import importlib.util
import sys
import unittest
import urllib.parse
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("search_official_templates", SCRIPTS / "search_official_templates.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class GraphGallerySearchTests(unittest.TestCase):
    def test_keyword_url_is_official_and_encoded(self):
        url = MODULE.build_gallery_url(search_terms="box chart normalized")
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual("www.originlab.com", parsed.hostname)
        self.assertEqual(["box chart normalized"], query["k"])
        self.assertEqual(["Newest"], query["sort"])

    def test_rejects_non_gallery_and_ambiguous_sources(self):
        with self.assertRaises(ValueError):
            MODULE.build_gallery_url(gallery_url="https://example.com/GraphGallery.aspx")
        with self.assertRaises(ValueError):
            MODULE.build_gallery_url("line", "https://www.originlab.com/www/products/GraphGallery.aspx")

    def test_gid_parser_deduplicates_and_preserves_order(self):
        html = """
        <a href="GraphGallery.aspx?GID=42">first</a>
        <a href="/www/products/GraphGallery.aspx?gid=7">second</a>
        <a href="GraphGallery.aspx?GID=42">duplicate</a>
        <a href="GraphGallery.aspx?GID=bad">invalid</a>
        """
        self.assertEqual(["42", "7"], MODULE.extract_gids(html))

    def test_zip_parser_accepts_only_official_gallery_archives(self):
        detail = "https://www.originlab.com/www/products/GraphGallery.aspx?GID=42"
        html = """
        <title>Example | OriginLab</title>
        <a href="https://blog.originlab.com/ftp/graph_gallery/example.zip">download</a>
        <a href="https://example.com/ftp/graph_gallery/evil.zip">external</a>
        <a href="https://blog.originlab.com/files/other.zip">wrong path</a>
        """
        self.assertEqual(
            ["https://blog.originlab.com/ftp/graph_gallery/example.zip"],
            MODULE.extract_zip_urls(html, detail),
        )

    def test_title_prefers_open_graph_metadata(self):
        parser = MODULE.parse_html(
            '<title>Originlab GraphGallery</title><meta property="og:title" content="Line + Symbol Plot">'
        )
        self.assertEqual("Line + Symbol Plot", parser.title)

    def test_archive_name_is_sanitized(self):
        name = MODULE.safe_archive_name(
            "https://blog.originlab.com/ftp/graph_gallery/My%20Template.zip", "42", 1
        )
        self.assertEqual("My_Template.zip", name)

    def test_generic_document_title_falls_back_to_archive_name(self):
        title = MODULE.candidate_title(
            "Originlab GraphGallery",
            ["https://blog.originlab.com/ftp/graph_gallery/Line_Symbol_Plot.zip"],
            "42",
        )
        self.assertEqual("Line Symbol Plot", title)

    def test_item_limit_is_fail_closed_before_network(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 20"):
            MODULE.discover("https://www.originlab.com/www/products/GraphGallery.aspx?s=0", 21, 3, 1, 0)


if __name__ == "__main__":
    unittest.main()
