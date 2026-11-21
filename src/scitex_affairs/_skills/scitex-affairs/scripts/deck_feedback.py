#!/usr/bin/env python3
"""Read-only OOXML snapshots/diffs for learning from PowerPoint edits.

Uses the package logging streams. It supports PPTX and PPTM without
rewriting either file. Diffs describe edits, not the operator's motives.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import posixpath
from pathlib import Path
import sys
from urllib.parse import unquote
from xml.etree import ElementTree as E
from zipfile import ZipFile

import scitex_logging as slogging

_console = slogging.getPlainConsole(__name__)

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS={'p':P,'a':A,'r':R}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def relationships(z, part):
    relpart=posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part)+'.rels')
    if relpart not in z.namelist():return {}
    result={}
    for rel in E.fromstring(z.read(relpart)):
        raw=rel.attrib['Target']
        external=rel.get('TargetMode')=='External'
        target=raw if external else posixpath.normpath(posixpath.join(posixpath.dirname(part), unquote(raw))).lstrip('/')
        result[rel.attrib['Id']]={'type':rel.attrib['Type'].rsplit('/',1)[-1],
                                  'target':target,'external':external}
    return result


def xml(element):
    if element is None:return None
    return E.canonicalize(E.tostring(element,encoding='unicode'), rewrite_prefixes=True)


def normalized_node(element, rels, z, slide_ids):
    if element is None:return None
    node=copy.deepcopy(element)
    for parent in node.iter():
        for child in list(parent):
            if child.tag.rsplit('}',1)[-1] in ('creationId','extLst'):
                parent.remove(child)
        for key,value in list(parent.attrib.items()):
            if key.startswith('{'+R+'}') and value in rels:
                rel=rels[value];target=rel['target']
                if rel['type']=='image' and not rel['external'] and target in z.namelist():
                    target='sha256:'+sha(z.read(target))
                elif rel['type']=='slide':target='slide-id:'+slide_ids.get(target,target)
                parent.set(key, rel['type']+':'+target)
    return xml(node)


def shape_snapshot(node, rels, z, slide_ids):
    prop=node.find('.//p:cNvPr',NS)
    if prop is None:return None
    transforms=[dict(n.attrib) for n in node.findall('.//a:xfrm/*',NS)]
    paragraphs=[''.join(t.text or '' for t in para.findall('.//a:t',NS))
                for para in node.findall('.//a:p',NS)]
    runs=[]
    for run in node.findall('.//a:r',NS):
        text=run.find('a:t',NS)
        style=run.find('a:rPr',NS)
        if style is not None:
            style=copy.deepcopy(style)
            for key in ('dirty','smtClean','err','lang','altLang'):
                style.attrib.pop(key,None)
        runs.append({'text':text.text if text is not None else '',
                     'format':normalized_node(style, rels, z, slide_ids)})
    media=[]
    for blip in node.findall('.//a:blip',NS):
        rid=blip.get('{'+R+'}embed') or blip.get('{'+R+'}link')
        rel=rels.get(rid)
        if rel:
            media.append({'external':rel['external'],
                          'value':rel['target'] if rel['external'] else sha(z.read(rel['target']))})
    links=[]
    for kind in ('hlinkClick','hlinkMouseOver'):
        for link in node.findall('.//a:'+kind,NS):
            rel=rels.get(link.get('{'+R+'}id'))
            target=rel['target'] if rel else None
            if rel and rel['type']=='slide':target='slide-id:'+slide_ids.get(target,target)
            links.append({'kind':kind,'target':target,'action':link.get('action')})
    properties=[]
    for tag in ('p:spPr','p:grpSpPr','p:style','p:blipFill','p:txBody/a:bodyPr','p:txBody/a:lstStyle'):
        element=node.find(tag,NS)
        if element is not None:
            properties.append(normalized_node(element,rels,z,slide_ids))
    return {'id':prop.get('id'),'name':prop.get('name',''),
            'kind':node.tag.rsplit('}',1)[-1], 'geometry':transforms,
            'text':paragraphs,'runs':runs,'properties':properties,'media':media,'links':links}


def snapshot(path):
    path=Path(path)
    data=path.read_bytes()
    with ZipFile(path) as z:
        presentation=E.fromstring(z.read('ppt/presentation.xml'))
        rels=relationships(z,'ppt/presentation.xml')
        order=[]
        for item in presentation.findall('p:sldIdLst/p:sldId',NS):
            order.append((item.get('id'),rels[item.get('{'+R+'}id')]['target']))
        slide_ids={part:sid for sid,part in order}
        slides=[]
        for index,(sid,part) in enumerate(order,1):
            root=E.fromstring(z.read(part));rels=relationships(z,part)
            shapes=[]
            tree=root.find('p:cSld/p:spTree',NS)
            for node in list(tree) if tree is not None else []:
                record=shape_snapshot(node,rels,z,slide_ids)
                if record:shapes.append(record)
            tags={};notes=''
            for rel in rels.values():
                if rel['external']:continue
                if rel['type']=='tags':
                    for tag in E.fromstring(z.read(rel['target'])):
                        tags[tag.get('name')]=tag.get('val')
                elif rel['type']=='notesSlide':
                    nr=E.fromstring(z.read(rel['target']));texts=[]
                    for sp in nr.findall('p:cSld/p:spTree/p:sp',NS):
                        ph=sp.find('p:nvSpPr/p:nvPr/p:ph',NS)
                        if ph is not None and ph.get('type')=='body':
                            texts += [''.join(t.text or '' for t in p.findall('.//a:t',NS)) for p in sp.findall('.//a:p',NS)]
                    notes='\n'.join(texts)
            title=next(('\n'.join(s['text']) for s in shapes if s['name']=='SCITEX_TITLE'), '')
            slides.append({'id':sid,'index':index,'title':title,'hidden':root.get('show')=='0',
                           'layout':next((r['target'] for r in rels.values() if r['type']=='slideLayout'),None),
                           'background':xml(root.find('p:cSld/p:bg',NS)),
                           'tags':tags,'notes':notes,'shapes':shapes})
        size=presentation.find('p:sldSz',NS)
        fingerprints={p:sha(z.read(p)) for p in z.namelist()
                      if p.endswith('.xml') and p.startswith(('ppt/slideMasters/','ppt/slideLayouts/','ppt/theme/'))}
        vba={p:sha(z.read(p)) for p in z.namelist() if 'vba' in p.lower()}
    return {'schema_version':1,'source':str(path.resolve()),'source_sha256':sha(data),
            'captured_utc':datetime.now(timezone.utc).isoformat(),
            'slide_size':dict(size.attrib) if size is not None else {},
            'template_fingerprints':fingerprints,'vba_fingerprints':vba,'slides':slides}


def load(path):
    path=Path(path)
    if path.suffix.lower()=='.json':
        value=json.loads(path.read_text())
        if value.get('schema_version')!=1 or 'slides' not in value:
            raise ValueError('Unsupported baseline schema')
        return value
    return snapshot(path)


def changes(old,new,fields):
    return {k:{'before':old.get(k),'after':new.get(k)} for k in fields if old.get(k)!=new.get(k)}


def compare(before,after):
    old={s['id']:s for s in before['slides']};new={s['id']:s for s in after['slides']}
    edited=[]
    for sid in old.keys() & new.keys():
        o,n=old[sid],new[sid]
        meta=changes(o,n,['index','title','hidden','layout','background','tags','notes'])
        os={s['id']:s for s in o['shapes']};ns={s['id']:s for s in n['shapes']}
        altered=[]
        for shape_id in os.keys() & ns.keys():
            diff=changes(os[shape_id],ns[shape_id],['name','kind','geometry','text','runs','properties','media','links'])
            if diff:altered.append({'id':shape_id,'name':ns[shape_id]['name'],'changes':diff})
        added=[ns[k] for k in ns.keys()-os.keys()];removed=[os[k] for k in os.keys()-ns.keys()]
        order_change=[s['id'] for s in o['shapes']]!=[s['id'] for s in n['shapes']]
        if meta or altered or added or removed or order_change:
            edited.append({'id':sid,'index':n['index'],'title':n['title'],
                           'changes':meta,'changed_shapes':sorted(altered,key=lambda x:int(x['id'])),
                           'added_shapes':added,'removed_shapes':removed,'shape_order_changed':order_change})
    shared=len(old.keys() & new.keys())
    return {'schema_version':1,'before':before['source'],'after':after['source'],
            'before_sha256':before['source_sha256'],'after_sha256':after['source_sha256'],
            'identity_method':'persistent slide and shape IDs; re-exported IDs can be ambiguous',
            'identity_caution':shared<min(len(old),len(new)),
            'deck_changes':changes(before,after,['slide_size','template_fingerprints','vba_fingerprints']),
            'changed_slides':sorted(edited,key=lambda x:x['index']),
            'added_slides':[new[k] for k in new.keys()-old.keys()],
            'removed_slides':[old[k] for k in old.keys()-new.keys()],
            'interpretation':'Changes are observations; infer preferences only with feedback and rendered evidence.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    snap=sub.add_parser('snapshot');snap.add_argument('deck',type=Path);snap.add_argument('--output',type=Path,required=True)
    diff=sub.add_parser('compare');diff.add_argument('before',type=Path);diff.add_argument('after',type=Path);diff.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        value=snapshot(args.deck) if args.command=='snapshot' else compare(load(args.before),load(args.after))
        payload=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with args.output.open('x',encoding='utf-8') as f:f.write(payload)
            if args.command=='snapshot':summary={'baseline':str(args.output),'slides':len(value['slides']),'sha256':value['source_sha256']}
            else:summary={'diff':str(args.output),'changed_slides':len(value['changed_slides']),
                          'added_slides':len(value['added_slides']),'removed_slides':len(value['removed_slides'])}
            _console.emit(json.dumps(summary,ensure_ascii=False))
        else:_console.emit(payload,end='')
    except (OSError,ValueError,KeyError,E.ParseError) as exc:
        _console.emit(f'{type(exc).__name__}: {exc}',stream=sys.stderr);return 2
    return 0


if __name__=='__main__':
    sys.exit(main())
