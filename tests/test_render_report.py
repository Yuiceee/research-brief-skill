"""Behavioral checks for offline delivery; all fixtures are synthetic."""
import base64
import importlib.util
from pathlib import Path
import tempfile
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('render_report', ROOT/'skills/research-brief/scripts/render_report.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j6l8AAAAASUVORK5CYII=')


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'材料'/'正文.md'
        self.source.parent.mkdir()
        (self.source.parent/'图.png').write_bytes(PNG)
        (self.source.parent/'证据.txt').write_text('Synthetic fixture; no research results.')
        self.output = self.root/'发布'/'report.html'

    def run_render(self, text):
        self.source.write_text(text)
        return module.render(self.source, self.output, 'zh-CN', '合成测试', False)

    def test_offline_images_links_and_collapsed_appendix(self):
        original = '# 测试报告\n\n## 摘要\n\n这是格式测试，不是研究结果。\n\n## 结果\n\n![合成图](图.png)\n\n图 1｜格式测试图片；无科学数据。\n\n## 附录\n\n[证据](证据.txt)\n'
        result = self.run_render(original)
        self.assertEqual(result['figures'], 1)
        self.assertEqual(self.source.read_text(), original)
        soup = BeautifulSoup(self.output.read_text(), 'html.parser')
        self.assertEqual(len(soup.find_all('h1')), 1)
        self.assertTrue(soup.img['src'].startswith('data:image/png;base64,'))
        self.assertEqual(soup.find_all('details')[-1].summary.get_text(), '附录')
        self.assertFalse(soup.find_all('details')[-1].has_attr('open'))
        self.assertIn('%E6%9D%90%E6%96%99', soup.find('a', string='证据')['href'])
        for a in soup.select('nav a'):
            self.assertIsNotNone(soup.find(id=a['href'][1:]))
        self.assertFalse(soup.find('script'))

    def test_missing_caption_fails_before_writing(self):
        with self.assertRaisesRegex(ValueError, 'caption'):
            self.run_render('# 标题\n\n![测试](图.png)\n\n这不是图注。')
        self.assertFalse(self.output.exists())

    def test_plain_report_does_not_gain_extra_sections_or_download_footer(self):
        original = '# Test report\n\n## Background\n\nA question.\n\n## Results\n\n![Synthetic](图.png)\n\nFigure 1. Synthetic fixture.\n'
        self.run_render(original)
        soup = BeautifulSoup(self.output.read_text(), 'html.parser')
        self.assertEqual([h.get_text() for h in soup.find_all('h2')], ['Background', 'Results'])
        self.assertEqual(soup.main.find('h2').get_text(), 'Background')
        self.assertFalse(soup.find('footer'))
        self.assertFalse(soup.select('.abstract'))
        self.assertEqual(len(soup.find_all('figure')), 1)
        self.assertEqual(self.source.read_text(), original)
        self.assertTrue(all(a['href'].startswith('#') for a in soup.find_all('a', href=True)))

    def test_missing_local_evidence_fails(self):
        with self.assertRaisesRegex(ValueError, 'Missing local file'):
            self.run_render('# 标题\n\n[材料](missing.csv)')

    def test_remote_images_are_not_fetched(self):
        with self.assertRaisesRegex(ValueError, 'Expected local path'):
            self.run_render('# 标题\n\n![远程](https://example.invalid/image.png)\n\n图 1｜示意。')

    def test_executable_markup_is_rejected(self):
        for content in ['<script>alert(1)</script>', '<img src="图.png" alt="x" onerror="alert(1)">', '[x](javascript:alert(1))']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.run_render('# 标题\n\n'+content)

    def test_missing_anchor_fails(self):
        with self.assertRaisesRegex(ValueError, 'Missing anchor'):
            self.run_render('# 标题\n\n[章节](#missing)')

    def test_input_cannot_be_output(self):
        self.source.write_text('# 保留原文')
        with self.assertRaisesRegex(ValueError, 'Output must differ'):
            module.render(self.source, self.source, 'zh-CN', '')
        self.assertEqual(self.source.read_text(), '# 保留原文')


if __name__ == '__main__':
    unittest.main()
