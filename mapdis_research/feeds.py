"""Public RSS/Atom metadata adapter. Does not fetch article bodies."""
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET


def parse_feed(text, feed_url, limit=10, quality=0.6):
    from .sources import record, plain
    # External entities and DTDs are not needed for RSS/Atom and are rejected.
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('Feed DTD/entity declarations are unsupported')
    root = ET.fromstring(text)
    local = lambda tag: tag.rsplit('}',1)[-1]
    if local(root.tag) not in {'rss','feed','RDF'}:
        raise ValueError('Not an RSS/Atom feed')
    def value(item,names):
        for child in item:
            if local(child.tag) in names:
                return ''.join(child.itertext()).strip()
        return ''
    result=[]
    for item in root.iter():
        if local(item.tag) not in {'item','entry'}:continue
        link=value(item,{'link'})
        for child in item:
            if local(child.tag)=='link' and child.get('rel','alternate')=='alternate' and child.get('href'):
                link=child.get('href');break
        if not link:continue
        link=urljoin(feed_url,link)
        if urlsplit(link).scheme!='https' or urlsplit(link).username:continue
        rawdate=value(item,{'pubDate','published','date'})
        published=None
        if rawdate:
            try:published=parsedate_to_datetime(rawdate).date().isoformat()
            except (ValueError,TypeError,OverflowError):
                try:published=datetime.fromisoformat(rawdate.replace('Z','+00:00')).date().isoformat()
                except ValueError:pass
        description=value(item,{'description','summary','content'})
        rec=record(value(item,{'title'}),published,link,plain(description),None,'rss',quality)
        rec.update(content_scope='feed_summary_only',feed_url=feed_url,
                   discovery=[{'source':'rss','query':feed_url,'page':1}])
        result.append(rec)
        if len(result)>=limit:break
    return result


def discover_feed(client,config,source):
    if not source.get('terms_reviewed',False):
        raise PermissionError('Review feed usage terms and set terms_reviewed before enabling')
    if not client.allowed(source['url']):
        raise PermissionError('Feed robots policy denies access or could not be verified')
    response=client.get(source['url'])
    return parse_feed(response.text,source['url'],config.get('max_results_per_source',10),source.get('quality',0.6))
