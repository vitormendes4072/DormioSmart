"""Executa os scripts em copia isolada, com saidas/checkpoints novos."""
from pathlib import Path
import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time

AP = argparse.ArgumentParser(description=__doc__)
AP.add_argument('--pasta', type=Path, required=True, help='pasta isolada contendo ml/ e logs/')
ARGS = AP.parse_args()
RUN = ARGS.pasta.resolve()
ML = (RUN / 'ml').resolve()
PY = Path(sys.executable)
WRAPPER = Path(__file__).with_name('rodada_reproducao.py')


JOBS = {
    'ml02_sintetico': [('experimentos.ml02_baselines', ['--dataset','sintetico'])],
    'ml02_newcastle': [('experimentos.ml02_baselines', ['--dataset','newcastle'])],
    'ml02_cabeca_cache92': [('experimentos.ml02_baselines', ['--dataset','wearanize','--posicao','cabeca'])],
    'ml02_pulso_cache92': [('experimentos.ml02_baselines', ['--dataset','wearanize','--posicao','pulso'])],
    'ml03_transferencia': [('experimentos.ml03_transferencia', [])],
    'ml03b_ablacao': [('experimentos.ml03b_ablacao', [])],
    'ml03b_otimizacoes': [('experimentos.ml03b_otimizacoes', ['--item',it,'--orcamento-s','60']) for it in ('baseline','6','7','8','8b','9')],
    'ml04_newcastle': [('experimentos.ml04_validacao_externa', ['--rodar'])],
    'ml04_walch_principal': [('experimentos.ml04_validacao_externa', ['--rodar','--coorte','walch'])],
    'ml04_walch_todos': [('experimentos.ml04_validacao_externa', ['--rodar','--coorte','walch','--incluir-baixa-taxa'])],
    'ml04b_lados': [('experimentos.ml04_validacao_externa', ['--lados'])],
    'ml05_teto': [('experimentos.ml05_teto_interavaliador', [])],
    'quantizacao': [('experimentos.quantizacao_features', ['10'])],
    'ml11_ablacao': [('experimentos.ml11_ablacao_features', ['10'])],
    'ml12_aninhada': [('experimentos.ml12_validacao_aninhada', [])],
}


def rodar(nome, comandos):
    t0=time.time()
    log=RUN/'logs'/(nome+'.log')
    env=dict(os.environ, PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8',
             OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
             NUMEXPR_NUM_THREADS='1')
    tentativas=0
    with log.open('a',encoding='utf-8') as f:
        for modulo,args in comandos:
            while True:
                tentativas+=1
                print('INICIO',nome,modulo,' '.join(args),flush=True)
                f.write('\nCOMANDO: '+modulo+' '+' '.join(args)+'\n');f.flush()
                r=subprocess.run([str(PY),str(WRAPPER),nome,modulo,*args],cwd=ML,env=env,
                    stdout=f,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                if r.returncode==2 and modulo.endswith('ml03b_otimizacoes'):
                    continue
                if r.returncode:
                    return dict(job=nome,status='falhou',codigo=r.returncode,segundos=time.time()-t0,log=log.name)
                break
    return dict(job=nome,status='concluido',segundos=time.time()-t0,tentativas=tentativas,log=log.name)


def main():
    original = Path(__file__).resolve().parents[1]
    if ML == original or not (ML/'src/avaliar.py').is_file():
        AP.error('prepare uma cópia isolada dos scripts antes de executar')
    estado=RUN/'estado.json'
    if not estado.exists() and any((ML/'experimentos/saida').iterdir()):
        AP.error('a primeira execução exige saída vazia, sem checkpoints antigos')
    (RUN/'logs').mkdir(exist_ok=True)
    resultados=json.loads(estado.read_text(encoding='utf-8')) if estado.exists() else {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        pendentes={ex.submit(rodar,n,c):n for n,c in JOBS.items() if resultados.get(n,{}).get('status')!='concluido'}
        for f in concurrent.futures.as_completed(pendentes):
            r=f.result();resultados[r['job']]=r
            estado.write_text(json.dumps(resultados,indent=2,ensure_ascii=False),encoding='utf-8')
            print('FIM',r['job'],r['status'],round(r['segundos'],1),'s',flush=True)
    return int(any(r['status']!='concluido' for r in resultados.values()))


if __name__=='__main__':sys.exit(main())
