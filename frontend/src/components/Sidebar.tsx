import { Activity, LayoutGrid, LogOut, PanelLeftClose, PanelLeftOpen, User, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router";

import { useAuth } from "../contexts/AuthContext";
import { usePerfil } from "../contexts/PerfilContext";
import { estaEmModoDemo } from "../lib/demo";
import { nomeDoPerfil } from "../lib/perfil";

import { destinoDoWorkspace, itensDeNavegacao, useNavegacaoNativa } from "./nav";
import { MarcaDoProduto } from "./MarcaDoProduto";

const CHAVE_DO_MENU = "dormio-menu-lateral";

function lerMenuRecolhido() {
  try {
    return window.localStorage.getItem(CHAVE_DO_MENU) === "recolhido";
  } catch {
    return false;
  }
}

function salvarMenuRecolhido(recolhido: boolean) {
  try {
    window.localStorage.setItem(CHAVE_DO_MENU, recolhido ? "recolhido" : "expandido");
  } catch {
    // A barra continua operável em visitas em que o armazenamento está indisponível.
  }
}

function Dica({ texto }: { texto: string }) {
  return (
    <span aria-hidden="true" className="pointer-events-none absolute left-full top-1/2 z-20 ml-2 hidden -translate-y-1/2 whitespace-nowrap rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-foreground shadow-sm group-hover:block group-focus-visible:block">
      {texto}
    </span>
  );
}

function LinkDaBarra({ to, label, icon: Icon, recolhida }: {
  to: string; label: string; icon: LucideIcon; recolhida: boolean;
}) {
  return (
    <NavLink to={to} aria-label={label}
      className={({ isActive }) => "group relative flex h-10 w-full items-center gap-3 rounded-xl text-sm font-medium focus-visible:outline-2 focus-visible:outline-ring "
        + (recolhida ? "justify-center " : "px-3 ")
        + (isActive ? (recolhida ? "text-primary" : "bg-primary/15 text-primary") : "text-muted-foreground hover:bg-secondary hover:text-foreground")}
    >
      <span className={recolhida ? "grid size-9 shrink-0 place-items-center rounded-xl group-aria-[current=page]:bg-primary/15 group-aria-[current=page]:text-primary" : "shrink-0"}>
        <Icon className="size-4" aria-hidden="true" />
      </span>
      {recolhida ? <Dica texto={label} /> : <span className="overflow-hidden whitespace-nowrap">{label}</span>}
    </NavLink>
  );
}

/** Navegação de desktop. Abaixo de md, a navegação fica na MobileNav. */
export function Sidebar() {
  const navigate = useNavigate();
  const { search } = useLocation();
  const demo = estaEmModoDemo(search);
  const { usuario, carregando, sair } = useAuth();
  const { perfil, carregando: carregandoPerfil } = usePerfil();
  const [recolhida, setRecolhida] = useState(lerMenuRecolhido);

  // O nome vem de `public.profiles`, pela rota — NAO do metadado do Auth
  // (PERFIL-01, Regra 1: leitor unico). `fonteDoNomeDoPerfil.test.ts` reprova
  // se alguem voltar a ler `user_metadata` aqui.
  //
  // Sem fallback para o metadado quando a leitura falha, de proposito: seria o
  // segundo leitor de volta, sob condicao. O que aparece nesse caso e "Conta" e
  // o e-mail, que e verdadeiro e sempre disponivel.
  const nome = nomeDoPerfil(perfil);

  const nativo = useNavegacaoNativa();
  const destinos = itensDeNavegacao(nativo);
  const navegacao = destinos.filter(({ to }) => to !== "/configuracoes").map((item) => {
    if (item.to === "/dashboard") return { ...item, label: "Visão geral", icon: LayoutGrid };
    if (item.to === "/coletar") return { ...item, label: "Nova coleta", icon: Activity };
    return item;
  });
  const configuracoes = destinos.find(({ to }) => to === "/configuracoes");
  const tituloDaConta = demo ? "Demonstração" : carregando || carregandoPerfil ? "..." : nome || "Conta";
  const IconeDoMenu = recolhida ? PanelLeftOpen : PanelLeftClose;

  function alternarMenu() {
    const proxima = !recolhida;
    setRecolhida(proxima);
    salvarMenuRecolhido(proxima);
  }

  return (
    <aside className={"sticky top-0 z-20 hidden h-screen flex-shrink-0 flex-col border-r border-border bg-card motion-safe:transition-[width] motion-safe:duration-150 md:flex "
      + (recolhida ? "w-[72px]" : "w-56")}>
      <div className="relative h-24 shrink-0">
        {!recolhida && (
          <div className="absolute inset-x-5 bottom-4 overflow-hidden">
            {/* Ocupa a largura util da sidebar (176px), o que dá ~30px de altura —
                o tamanho em que o "SMART" foi verificado como legível. */}
            <MarcaDoProduto className="h-[30px] max-w-none" />
          </div>
        )}
        <button type="button" aria-label={recolhida ? "Expandir menu" : "Recolher menu"}
          aria-expanded={!recolhida} onClick={alternarMenu}
          className={"absolute top-1.5 grid size-9 place-items-center rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring "
            + (recolhida ? "left-1/2 -translate-x-1/2" : "right-2")}>
          <IconeDoMenu className="size-4" aria-hidden="true" />
        </button>
      </div>

      <nav aria-label="Navegação principal" className="flex-1 space-y-1 px-2.5">
        <p className={"overflow-hidden whitespace-nowrap px-3 pb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground "
          + (recolhida ? "invisible" : "")}>Workspace</p>
        {navegacao.map(({ to, label, icon }) => (
          <LinkDaBarra key={to} to={destinoDoWorkspace(to, search)} label={label} icon={icon} recolhida={recolhida} />
        ))}
        {configuracoes && (
          <>
            <p className={"overflow-hidden whitespace-nowrap px-3 pb-2 pt-7 text-[10px] font-bold uppercase tracking-widest text-muted-foreground "
              + (recolhida ? "invisible" : "")}>Preferências</p>
            <LinkDaBarra to={destinoDoWorkspace(configuracoes.to, search)} label={configuracoes.label}
              icon={configuracoes.icon} recolhida={recolhida} />
          </>
        )}
      </nav>

      <div className="space-y-3 border-t border-border p-4">
        <div className={"group relative flex min-h-8 items-center gap-3 " + (recolhida ? "justify-center" : "px-1")}>
          <div className="grid size-8 shrink-0 place-items-center rounded-full bg-primary/20">
            <User className="size-4 text-primary" aria-hidden="true" />
          </div>
          {recolhida ? (
            <>
              <span className="sr-only">{demo ? "Demonstração" : "Conta"}</span>
              <Dica texto={demo ? "Demonstração" : "Conta"} />
            </>
          ) : (
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{tituloDaConta}</p>
              <p className="truncate text-xs text-muted-foreground">
                {demo || carregando ? "" : (usuario?.email ?? "não autenticada")}
              </p>
            </div>
          )}
        </div>
        {!demo && (
          <button type="button" aria-label="Sair" onClick={async () => {
            await sair();
            navigate("/login");
          }}
            className={"group relative flex h-9 w-full items-center gap-2 rounded-xl text-sm text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring "
              + (recolhida ? "justify-center" : "px-3")}>
            <LogOut className="size-4 shrink-0" aria-hidden="true" />
            {recolhida ? <Dica texto="Sair" /> : <span className="overflow-hidden whitespace-nowrap">Sair</span>}
          </button>
        )}
      </div>
    </aside>
  );
}
