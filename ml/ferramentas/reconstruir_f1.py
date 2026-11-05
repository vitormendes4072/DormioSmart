"""Recupera matrizes por sujeito de acuracia/especificidade + rotulos conhecidos.

Verifica integridade por kappa e limites inteiros. Nao estima as contagens por
suporte global: usa o numero real de rotulos de cada participante no cache.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import pickle
import sys
import numpy as np




def contagens(y,ids):
    return {s:(int(np.sum(y[ids==s]==1)),int(np.sum(y[ids==s]==0))) for s in set(ids.tolist())}


def matriz(acc,esp,kappa,pos,neg):
    n=pos+neg
    if n<=0 or pos<0 or neg<0:raise ValueError('suporte inválido')
    vn=int(round(esp*neg)) if neg else 0
    vp=int(round(acc*n))-vn
    if not (0<=vn<=neg and 0<=vp<=pos):raise ValueError('contagem fora do suporte')
    fp,fn=neg-vn,pos-vp
    if abs((vp+vn)/n-acc)>=1e-10:raise ValueError('acurácia incompatível com contagens inteiras')
    if neg and abs(vn/neg-esp)>=1e-10:raise ValueError('especificidade incompatível com contagens inteiras')
    po=(vp+vn)/n
    pe=((vp+fn)*(vp+fp)+(vn+fp)*(vn+fn))/(n*n)
    k=(po-pe)/(1-pe) if abs(1-pe)>1e-12 else float('nan')
    if not np.isclose(k,kappa,atol=1e-10,rtol=0,equal_nan=True):raise ValueError('kappa incompatível')
    return vp,vn,fp,fn


def resumo(v,seed,n_boot):
    v=np.asarray(v,float);v=v[~np.isnan(v)]
    if not len(v):return {'n_valido':0,'media':None,'desvio_padrao':None,'ic95':[None,None]}
    b=np.random.default_rng(seed).choice(v,size=(n_boot,len(v)),replace=True).mean(axis=1)
    return {'n_valido':len(v),'media':float(v.mean()),
            'desvio_padrao':float(v.std(ddof=1)) if len(v)>1 else 0.0,
            'ic95':np.percentile(b,[2.5,97.5]).tolist()}


def derivar(no,counts,seed):
    if not all(s in counts for s in no['sujeitos']):raise ValueError('sujeito fora da coorte')
    f={nome:[] for nome in ('f1_sono','f1_vigilia')}
    antigo={nome:[] for nome in f};matrizes=[]
    ps=no['por_sujeito']
    if any(len(ps[k])!=len(no['sujeitos']) for k in ('acuracia','especificidade','kappa')):
        raise ValueError('quantidade de métricas diferente da quantidade de sujeitos')
    for i,s in enumerate(no['sujeitos']):
        vp,vn,fp,fn=matriz(ps['acuracia'][i],ps['especificidade'][i],ps['kappa'][i],*counts[s])
        matrizes.append({'sujeito':s,'vp':vp,'vn':vn,'fp':fp,'fn':fn})
        for nome,tp in (('f1_sono',vp),('f1_vigilia',vn)):
            den=2*tp+fp+fn
            f[nome].append(2*tp/den if den else float('nan'))
            prec=tp/(tp+fp) if tp+fp else float('nan')
            rec=tp/(tp+fn) if tp+fn else float('nan')
            antigo[nome].append(2*prec*rec/(prec+rec) if prec+rec else float('nan'))
    return {'matrizes':matrizes,'avaliacao':{nome:{
        'formula_antiga_mesmas_classificacoes':resumo(antigo[nome],seed,no['n_bootstrap']),
        'formula_corrigida':resumo(f[nome],seed,no['n_bootstrap']),
        'zeros_antes_excluidos':sum(math.isnan(a) and math.isfinite(b) for a,b in zip(antigo[nome],f[nome]))}
        for nome in f}}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ml-isolado',type=Path,required=True)
    ap.add_argument('--saida',type=Path,required=True)
    ap.add_argument('--incluir-matrizes',action='store_true')
    args=ap.parse_args()
    ML=args.ml_isolado.resolve()
    sys.path.insert(0,str(ML))
    from src.configuracao import carregar_config
    from experimentos.ml04_validacao_externa import carregar_features_newcastle, carregar_features_walch
    cfg=carregar_config()
    with (ML/'dados/processado/_cache_base_wearanize_14646b9aacb7d397.pkl').open('rb') as fh:base=pickle.load(fh)
    b=base['cabeca'];wear=contagens(b['y'],b['id'])
    _,y,ids=carregar_features_newcastle(cfg,'esquerdo');newcastle=contagens(y,ids)
    walch={}
    for variante,incluir in [('principal',False),('todos',True)]:
        _,y,ids=carregar_features_walch(cfg,incluir);walch[variante]=contagens(y,ids)
    saida=[]
    for p in sorted((ML/'experimentos/saida').glob('*.json')):
        if p.name.startswith(('ml03_','ml03b_')):counts=wear
        elif p.name.startswith('ml04_validacao_externa_'):
            counts=walch['principal' if '_principal' in p.name else 'todos'] if '_walch_' in p.name else newcastle
        else:continue
        dados=json.loads(p.read_text(encoding='utf-8'))
        if dados.get('parcial'):continue
        def visitar(no,caminho):
            if isinstance(no,dict):
                if 'por_sujeito' in no and all(k in no['por_sujeito'] for k in ('acuracia','especificidade','kappa')):
                    resultado=derivar(no,counts,cfg.seed)
                    resultado['n_matrizes_verificadas']=len(resultado['matrizes'])
                    if not args.incluir_matrizes:resultado.pop('matrizes')
                    digest=hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                    saida.append({'arquivo':p.name,'sha256_utf8_lf':digest,'caminho':caminho,**resultado})
                else:
                    for k,v in no.items():visitar(v,caminho+'.'+k)
        visitar(dados,'$')
    args.saida.write_text(json.dumps(saida,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print('Avaliacoes por sujeito reconstruidas e verificadas:',len(saida))


if __name__=='__main__':main()
