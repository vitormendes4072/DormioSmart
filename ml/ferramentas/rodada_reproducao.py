"""Adaptador de entrada de cache, sem alterar algoritmos de treino dos scripts."""
from pathlib import Path
import importlib
import json
import pickle
import sys
import numpy as np

ML=Path.cwd()
sys.path.insert(0,str(ML))
job,modulo,*args=sys.argv[1:]
sys.argv=[modulo,*args]
e=importlib.import_module(modulo)

if modulo.endswith('ml03_transferencia') or (modulo.endswith('ml02_baselines') and '--dataset' in args and args[args.index('--dataset')+1]=='wearanize'):
    from src.carregar.base import ConjuntoEpocas
    from src.epocas import empilhar_contexto
    from src.features import NOMES_FEATURES
    with (ML/'dados/processado/_cache_base_wearanize_14646b9aacb7d397.pkl').open('rb') as f: base=pickle.load(f)
    def entrada(**kw):return kw
    def processar(kw,cfg):
        braco='cabeca_e4' if kw.get('qualidade')=='e4' else kw['posicao']
        b=base[braco]
        assert len(set(b['id'].tolist()))==92 and len(b['y'])==87795
        sujeitos=kw.get('sujeitos')
        if sujeitos is not None:assert set(sujeitos)==set(b['id'].tolist())
        # O ML-02 empilha por gravacao, sem cruzar a fronteira de sujeitos.
        partes=[empilhar_contexto(b['X'][b['id']==s],cfg.contexto_epocas) for s in dict.fromkeys(b['id'].tolist())]
        X=np.concatenate(partes)
        nomes=tuple(n+('' if d==0 else f'__{d:+d}') for d in range(-cfg.contexto_epocas,cfg.contexto_epocas+1) for n in NOMES_FEATURES)
        conj=ConjuntoEpocas(X,b['y'],b['id'],nomes,{'origem':'cache de features; coorte cabeca/pulso comum, 92 sujeitos'})
        return conj,b['c'],b['y_c'],b['id_c']
    e.carregar_wearanize=entrada
    if modulo.endswith('ml02_baselines'):
        # main faz import local; redirecionar o carregador que ele importa.
        import src.carregar.wearanize as w
        w.carregar_wearanize=entrada
    e._processar_unificado=processar

raise SystemExit(e.main())
