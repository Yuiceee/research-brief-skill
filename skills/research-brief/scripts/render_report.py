#!/usr/bin/env python3
"""Render a local research Markdown document with embedded figures; no network I/O."""
import argparse
import base64
import html
import mimetypes
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

import markdown
from bs4 import BeautifulSoup


def local_path(url, base):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        raise ValueError(f'Expected local path: {url}')
    path = (base / unquote(parsed.path)).resolve()
    if not path.is_file():
        raise ValueError(f'Missing local file: {url}')
    return path


def render(source, output, lang, meta, expand_appendix=False):
    source, output = source.resolve(), output.resolve()
    if source == output:
        raise ValueError('Output must differ from the source Markdown')
    body = BeautifulSoup(markdown.markdown(source.read_text(encoding='utf-8'),
                         extensions=['tables', 'fenced_code', 'sane_lists']), 'html.parser')
    if len(body.find_all('h1')) != 1:
        raise ValueError('Exactly one Markdown H1 title is required')
    if body.find(['script', 'iframe', 'object', 'embed', 'link', 'style']):
        raise ValueError('Use static figures; external resources or executable HTML are unsupported')
    for tag in body.find_all(True):
        if any(k.lower().startswith('on') or k.lower() in ('style', 'srcset') for k in tag.attrs):
            raise ValueError('Inline event handlers, styles and srcset are unsupported')
    title_node = body.find('h1')
    title = title_node.get_text(' ', strip=True)
    if not title:
        raise ValueError('Title cannot be empty')
    title_node.extract()
    for img in body.find_all('img'):
        if not img.get('alt', '').strip():
            raise ValueError('Every figure requires meaningful alt text')
        src = img.get('src', '')
        path = local_path(src, source.parent)
        mime = mimetypes.guess_type(path.name)[0]
        if mime not in ('image/png', 'image/jpeg', 'image/webp', 'image/gif'):
            raise ValueError('Export scientific figures as PNG/JPEG/WebP/GIF for embedding')
        img['src'] = f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')
        if not img.find_parent('figure'):
            para = img.parent
            if para.name != 'p' or para.get_text(strip=True) or len(para.find_all('img')) != 1:
                raise ValueError('Place each image in its own Markdown paragraph')
            cap = para.find_next_sibling()
            if not cap or cap.name != 'p' or not re.match(r'^(图\s*\d+|Figure\s+\d+)', cap.get_text(strip=True), re.I):
                raise ValueError('Follow each image with a caption paragraph beginning 图 1 or Figure 1')
            fig = body.new_tag('figure')
            para.replace_with(fig)
            fig.append(img.extract())
            cap.name = 'figcaption'
            fig.append(cap.extract())
    for fig in body.find_all('figure'):
        if not fig.find('img') or not fig.find('figcaption') or not fig.find('figcaption').get_text(strip=True):
            raise ValueError('Each figure requires an image and a non-empty figcaption')
    for table in body.find_all('table'):
        table.wrap(body.new_tag('div', attrs={'class': 'table-scroll'}))
    heads = body.find_all(['h2', 'h3'])
    used_ids = {x['id'] for x in body.find_all(id=True)}
    for i, heading in enumerate(heads, 1):
        if not heading.get('id'):
            candidate = f'section-{i}'
            while candidate in used_ids:
                candidate += '-x'
            heading['id'] = candidate
            used_ids.add(candidate)
    for a in body.find_all('a', href=True):
        url = a['href']
        parsed = urlsplit(url)
        if parsed.scheme in ('https', 'http', 'mailto'):
            continue
        if parsed.scheme or parsed.netloc:
            raise ValueError(f'Unsupported link scheme: {url}')
        if parsed.path:
            target = local_path(url, source.parent)
            a['href'] = quote(os.path.relpath(target, output.parent), safe='/')
            if parsed.fragment:
                a['href'] += '#' + parsed.fragment
        elif parsed.fragment and parsed.fragment not in used_ids:
            raise ValueError(f'Missing anchor: {url}')
    appendix = next((h for h in body.find_all('h2') if re.match(r'^(附录|Appendix)', h.get_text(), re.I)), None)
    if appendix:
        details = body.new_tag('details')
        if expand_appendix:
            details['open'] = ''
        summary = body.new_tag('summary', id=appendix['id'])
        summary.string = appendix.get_text()
        details.append(summary)
        for sibling in list(appendix.next_siblings):
            details.append(sibling.extract())
        appendix.replace_with(details)
    toc = body.new_tag('details', attrs={'class': 'toc'})
    label = body.new_tag('summary')
    label.string = '目录 / Contents'
    toc.append(label)
    nav = body.new_tag('nav', attrs={'aria-label': 'Contents'})
    listing = body.new_tag('ol')
    for h in heads:
        if h.name == 'h2' and h is not appendix and h.get_text(strip=True) not in ('摘要', 'Abstract'):
            item = body.new_tag('li')
            a = body.new_tag('a', href='#' + h['id'])
            a.string = h.get_text()
            item.append(a)
            listing.append(item)
    nav.append(listing)
    toc.append(nav)
    abstract = next((h for h in body.find_all('h2') if h.get_text(strip=True) in ('摘要', 'Abstract')), None)
    abstract_text = abstract.find_next_sibling('p') if abstract else None
    if abstract_text:
        abstract_text['class'] = 'abstract'
        abstract_text.insert_after(toc)
    elif listing.find('li'):
        body.insert(0, toc)
    template = (Path(__file__).resolve().parents[1] / 'assets/report.html').read_text(encoding='utf-8')
    replacements = {'LANG': html.escape(lang, quote=True), 'TITLE': html.escape(title),
                    'META': html.escape(meta), 'BODY': str(body),
                    'MARKDOWN': html.escape(quote(os.path.relpath(source, output.parent), safe='/'), quote=True)}
    result = re.sub(r'@@(LANG|TITLE|META|BODY|MARKDOWN)@@', lambda m: replacements[m.group(1)], template)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding='utf-8')
    return {'title': title, 'figures': len(body.find_all('figure')), 'html': str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--lang', default='zh-CN')
    parser.add_argument('--meta', default='阶段研究报告')
    parser.add_argument('--expand-appendix', action='store_true', help='Keep appendix expanded, e.g. before printing')
    parser.add_argument('--force', action='store_true', help='Replace an existing output HTML')
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        parser.error('Output exists; choose another name or use --force')
    try:
        result = render(args.source, args.output, args.lang, args.meta, args.expand_appendix)
    except (ValueError, OSError) as e:
        parser.exit(1, f'ERROR: {e}\n')
    print(f"OK: {result['figures']} figures embedded; local file links checked; {result['html']}")
    print('Scientific accuracy, external URLs and browser layout still require review.')


if __name__ == '__main__':
    main()
