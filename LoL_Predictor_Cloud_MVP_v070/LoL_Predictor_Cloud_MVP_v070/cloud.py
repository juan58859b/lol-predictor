#!/usr/bin/env python3
"""Cloud dashboard: solo calendario + registro ya sellado. NUNCA emite predicciones.
No almacena token ni datos privados; si falla la consulta falla el despliegue.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, html, json, os, sys, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
API='https://api.pandascore.co/lol/matches/upcoming'
UTC=dt.timezone.utc

def stable(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(obj): return hashlib.sha256(stable(obj)).hexdigest()
def when(value):
    try:
        out=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return out.astimezone(UTC) if out.tzinfo else None
    except (ValueError,TypeError,AttributeError):return None

def checked_register():
    src=ROOT/'data/WORLDS2026-FINAL-GEN-BLG.json'
    record=json.loads(src.read_text(encoding='utf-8'))
    p, r = record['prediccion'],record['registro']
    core={k:r[k] for k in ('partido_id','archivo','hash_prediccion','hash_previo')}
    if digest(p)!=r['hash_prediccion'] or digest(core)!=r['hash_registro']:
        raise ValueError('Registro original alterado; se cancela la publicación')
    return p,r

def page_live(token,page):
    query=urlencode({'sort':'scheduled_at','per_page':100,'page':page})
    req=urllib.request.Request(API+'?'+query,headers={
        'Authorization':'Bearer '+token,'Accept':'application/json',
        'User-Agent':'LoLPredictorResearch/0.7'})
    with urllib.request.urlopen(req,timeout=35) as response:
        if response.status!=200: raise RuntimeError('PandaScore HTTP '+str(response.status))
        blob=response.read(5_000_001)
        if len(blob)>5_000_000:raise RuntimeError('Respuesta de PandaScore excesiva')
        data=json.loads(blob)
        if not isinstance(data,list):raise RuntimeError('PandaScore devolvió un formato inválido')
        headers={x.lower():y for x,y in response.headers.items()}
        page_header=headers.get('x-page')
        if page_header and int(page_header)!=page:
            raise RuntimeError('PandaScore no confirmó la página solicitada')
        total=headers.get('x-total')
        return data,(int(total) if total is not None else None)

def get_fixtures(token,max_pages=15):
    if not token:raise RuntimeError('Configura PANDASCORE_TOKEN como secret de GitHub (no en código)')
    events=[];seen=set();expected_total=None
    for page in range(1,max_pages+1):
        batch,total=page_live(token,page)
        if total is not None:
            if expected_total is not None and total != expected_total:
                raise RuntimeError('El total de PandaScore cambió durante la paginación; reintentar')
            expected_total=total
        for item in batch:
            mid=item.get('id')
            if not isinstance(mid,int) or mid in seen:
                raise RuntimeError('IDs inválidos o repetidos de PandaScore')
            seen.add(mid);events.append(item)
        if len(batch)<100:
            if expected_total is not None and len(events)!=expected_total:
                raise RuntimeError('Número de resultados != X-Total')
            break
        if expected_total is not None and len(events)>=expected_total:
            if len(events)!=expected_total:raise RuntimeError('Exceso sobre X-Total')
            break
    else: raise RuntimeError('Paginación no exhaustiva; no se publica')
    return events

def normalize(raw,now,days=14):
    soon=[]
    for item in raw:
        if not isinstance(item,dict):continue
        date=when(item.get('scheduled_at'))
        if not date or not (now < date <= now+dt.timedelta(days=days)):continue
        if item.get('status')!='not_started':continue
        ops=item.get('opponents') or []
        teams=[]
        for team in ops:
            o=team.get('opponent',{}) if isinstance(team,dict) else {}
            if isinstance(o,dict) and isinstance(o.get('id'),int) and o.get('name'):
                teams.append({'id':str(o['id']),'nombre':str(o['name'])[:100]})
        league=item.get('league') or {}
        league_name=str(league.get('name','Sin liga'))[:100] if isinstance(league,dict) else 'Sin liga'
        bo=item.get('number_of_games')
        soon.append({'id':str(item.get('id','')),'fecha':date.isoformat(),
                     'equipos':teams,'liga':league_name,'bo':bo if bo in (1,3,5) else None})
    return sorted(soon,key=lambda f:(f['fecha'],f['id']))

def annotate(fixtures,p):
    confirmed={'Gen.G':'2882','Bilibili Gaming':'1566'}
    for row in fixtures:
        teams=row['equipos']
        if len(teams)!=2 or not row['bo']:
            row['estado']='BLOQUEADO · faltan participantes o formato'
        elif row['fecha']==p['inicio_utc'].replace('Z','+00:00') and row['bo']==p['mejor_de'] and {x['id'] for x in teams}==set(confirmed.values()):
            row['estado']='YA REGISTRADO · B3/C18'
        else:
            row['estado']='SIN PRONÓSTICO · cobertura de mapas por verificar'
    return fixtures

def render(fixtures,p,r,now,source):
    def esc(v): return html.escape(str(v), quote=True)
    cards=[]
    for item in fixtures[:40]:
        names=' vs '.join(x['nombre'] for x in item['equipos']) if item['equipos'] else 'Rivales por confirmar'
        cards.append('<article class="match"><div class="small">'+esc(item['liga'])+' · '+esc(item['fecha'][:16].replace('T',' '))+' UTC · '+esc('Bo'+str(item['bo']) if item['bo'] else 'Bo?')+'</div><h3>'+esc(names)+'</h3><div class="status">'+esc(item['estado'])+'</div></article>')
    if not cards:cards=['<p>No hay encuentros en esta ventana. No significa que no existan partidos fuera de la cobertura.</p>']
    b=100*p['modelos']['B3']['p_serie_equipo_a_5050_independiente']
    c=100*p['modelos']['C18']['p_serie_equipo_a_5050_independiente']
    css=""":root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color-scheme:dark;background:#080e19;color:#f3f7ff}body{max-width:900px;margin:0 auto;padding:20px}header{display:flex;justify-content:space-between;gap:12px;align-items:center}h1{font-size:1.6rem;margin:0}.sub,.small{color:#aebed2;font-size:.86rem}.hero,.match,.notice{border:1px solid #26364d;background:#121d30;padding:18px;border-radius:14px;margin:14px 0}.notice{background:#242033}strong{color:#f9fbff}.scores{display:grid;grid-template-columns:1fr 1fr;gap:12px}.score{padding:14px;border-radius:10px;background:#21354e}.big{font-size:2rem;font-weight:800}.status{font-size:.8rem;color:#becfe5}h3{margin:8px 0}footer{color:#aebed2;font-size:.82rem;margin:30px 0}code{overflow-wrap:anywhere}.matches{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:0 12px}@media(max-width:500px){.scores{grid-template-columns:1fr}}"""
    return ("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>LoL Predictor · Piloto</title><style>"""+css+"""</style></head><body>
<header><div><h1>LoL Predictor</h1><div class="sub">Piloto de publicación en la nube · no es emisión automática</div></div></header>
<div class="notice">Actualización: <strong>"""+esc(now.isoformat())+"""</strong> · Fuente del calendario: """+esc(source)+"""<p>Los partidos nuevos se muestran sin pronóstico hasta validar los mapas y la identidad. No se generan estimaciones con información incompleta.</p></div>
<section class="hero"><div class="small">Worlds 2026 · Predicción archivada · Gen.G frente a BLG</div><h2>Probabilidad de victoria de Gen.G</h2><div class="scores"><div class="score">B3 · referencia<br><span class="big">"""+f'{b:.3f}'+""" %</span></div><div class="score">C18 · candidato<br><span class="big">"""+f'{c:.3f}'+""" %</span></div></div><p class="small">Emitida: """+esc(p['emitido_utc'])+""" · SHA-256 predicción: <code>"""+esc(r['hash_prediccion'])+"""</code></p><p class="small">C18 no confirmó superioridad estadística en EXP-002 3a. Los porcentajes asumen selección de lados equilibrada e independencia entre mapas; no constituyen una garantía.</p></section>
<h2>Próximos encuentros (14 días)</h2><div class="matches">"""+''.join(cards)+"""</div><footer>Producto de investigación. Los hashes comprueban integridad, no fecha mediante un sello externo. El calendario puede sufrir modificaciones. No hay reentrenamiento ni emisiones nuevas en esta versión.</footer></body></html>""")

def build(mode,output,fixture=None,now=None):
    p,r=checked_register()
    now=now or dt.datetime.now(UTC)
    if mode=='live':
        raw=get_fixtures(os.getenv('PANDASCORE_TOKEN',''))
        source='PandaScore (consulta en vivo)'
    elif mode=='offline':
        if not fixture:raise RuntimeError('Falta fixture de pruebas')
        raw=json.loads(Path(fixture).read_text(encoding='utf8'))
        source='ARCHIVO HISTÓRICO DE PRUEBA · NO EN VIVO'
    else:raise ValueError('Modo desconocido')
    rows=annotate(normalize(raw,now),p)
    output.mkdir(parents=True,exist_ok=True)
    (output/'index.html').write_text(render(rows,p,r,now,source),encoding='utf8')
    status={'fecha_utc':now.isoformat(),'fuente':source,'n_eventos':len(rows),
            'n_registros_historicos':1,'hash_registro':r['hash_registro'],
            'predicciones_nuevas':0,'autoemision_habilitada':False}
    (output/'estado.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    return status

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--live',action='store_true');group.add_argument('--offline',type=Path)
    ap.add_argument('--out',type=Path,default=ROOT/'site')
    args=ap.parse_args()
    try:print(json.dumps(build('live' if args.live else 'offline',args.out,args.offline),indent=2,ensure_ascii=False))
    except Exception as e:print('ERROR:',str(e),file=sys.stderr);sys.exit(1)
