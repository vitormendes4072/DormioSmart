"""Compara resultados com tolerância absoluta/relativa 1e-10, sem alterá-los.

Metadados compatíveis não provam identidade de participantes. Exclui novas
execuções parciais; uma referência histórica parcial é identificada no relatório.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re



def hash_texto(p):return hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def comparar(a,b,caminho='$',dif=None):
    if dif is None:dif=[]
    ignorar={'utc','segundos','parcial','AVISO','nota','o_que_nao_mede','teto_no_newcastle','nota_assimetria'}
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(a.keys() & b.keys()):
            if k not in ignorar:comparar(a[k],b[k],caminho+'.'+k,dif)
        for k in sorted(a.keys()-b.keys()):
            if k not in ignorar:dif.append({'caminho':caminho+'.'+k,'tipo':'campo_ausente'})
        for k in sorted(b.keys()-a.keys()):
            if k not in ignorar:dif.append({'caminho':caminho+'.'+k,'tipo':'campo_novo'})
    elif isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b):dif.append({'caminho':caminho,'tipo':'tamanho','antes':len(a),'depois':len(b)})
        else:
            for i,(x,y) in enumerate(zip(a,b)):comparar(x,y,caminho+'['+str(i)+']',dif)
    elif type(a) in (int,float) and type(b) in (int,float):
        if math.isnan(a) and math.isnan(b):return dif
        if a==b:return dif
        if math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,abs_tol=1e-10,rel_tol=1e-10):return dif
        dif.append({'caminho':caminho,'tipo':'numero','antes':a if math.isfinite(a) else None,
                    'depois':b if math.isfinite(b) else None,
                    'antes_nan':math.isnan(a),'depois_nan':math.isnan(b)})
    elif type(a) is not type(b) or a!=b:dif.append({'caminho':caminho,'tipo':'valor','antes':str(a),'depois':str(b)})
    return dif


def comparar_pastas(referencias, novos):
    manifest=[]
    for p in sorted(novos.glob('*.json')):
        b=json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(b,dict) or b.get('parcial'):continue
        stem=p.stem
        prefix=re.sub(r'_\d{8}T\d{6}Z$','',stem)
        if prefix!=stem:
            refs=sorted(referencias.glob(prefix+'_*.json'))
        else:refs=[referencias/p.name] if (referencias/p.name).exists() else []
        for ref in refs:
            a=json.loads(ref.read_text(encoding='utf-8'))
            coorte=all(a.get(k)==b.get(k) for k in ('n_sujeitos','n_epocas','hash_config','seed'))
            dif=comparar(a,b)
            f1=[d for d in dif if '.f1_' in d['caminho']]
            outras=[d for d in dif if '.f1_' not in d['caminho']]
            manifest.append({'referencia':ref.name,'novo':p.name,'referencia_sha256_utf8_lf':hash_texto(ref),
                'novo_sha256_utf8_lf':hash_texto(p),'coorte_metadados_compativeis':coorte,
                'referencia_parcial':bool(a.get('parcial')),
                'n_diferencas_f1':len(f1),'n_outras_diferencas':len(outras),
                'diferencas_f1':f1,'outras_diferencas':outras})
    return manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--referencias',type=Path,default=Path(__file__).resolve().parents[1]/'experimentos/saida')
    ap.add_argument('--novos',type=Path,required=True)
    ap.add_argument('--saida',type=Path,required=True)
    ap.add_argument('--conferir',action='store_true',help='conferir relatório já salvo')
    args=ap.parse_args()
    if not args.novos.is_dir() or not args.referencias.is_dir():
        ap.error('pasta de resultados inexistente')
    manifest=comparar_pastas(args.referencias,args.novos)
    if not manifest:ap.error('nenhum par de resultados completos encontrado')
    if args.conferir:
        if json.loads(args.saida.read_text(encoding='utf-8'))!=manifest:
            print('DIVERGÊNCIA: relatório, resultado ou referência mudou')
            return 1
    else:
        args.saida.write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    for m in manifest:print(m['referencia'],'F1',m['n_diferencas_f1'],'outras',m['n_outras_diferencas'])
    return 0


if __name__=='__main__':raise SystemExit(main())
