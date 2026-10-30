# Findr

Barra de busca estilo **Spotlight/Finder do macOS** para Ubuntu (GNOME, Wayland ou X11).
Pressione **Alt+Space** e digite: aplicativos, pastas, documentos, contas e pesquisa na web.

| Você digita        | Resultado                                                    |
|--------------------|--------------------------------------------------------------|
| `fire`             | Firefox como *melhor resultado* + pastas/arquivos “fire…”    |
| `vsc`              | Visual Studio Code (acrônimo)                                |
| `configuracoes`    | Configurações (ignora acentos e maiúsculas)                  |
| `2^10/4`, `2,5*3`  | Calculadora, e **Enter** copia o resultado                   |
| qualquer texto     | “Pesquisar na web” como última opção                         |

**Teclas:** `↑/↓` navegam · `Enter` abre · `Ctrl+Enter` mostra o arquivo na pasta ·
`Esc` limpa o texto e, num segundo toque, fecha · clicar fora fecha.
Os itens que você mais abre sobem no ranking.

## Instalação

```bash
sudo apt install python3-gi gir1.2-gtk-3.0   # já vem no Ubuntu Desktop
./install.sh
```

O instalador copia o app para `~/.local/share/findr`, cria `~/.local/bin/findr`,
adiciona ao menu e ao início automático e registra o atalho **Alt+Space** no GNOME.

> No GNOME, Alt+Space abre o “menu da janela”. O instalador libera esse atalho e
> guarda um backup. `./uninstall.sh` (ou `findr --uninstall-hotkey`) restaura tudo.

Para rodar direto do código-fonte: `make run` · testes: `make test`.

### Linha de comando

```
findr                   mostra a barra (inicia se necessário)
findr --toggle          mostra/esconde
findr --daemon          inicia oculto (usado no autostart)
findr --quit            encerra
findr --install-hotkey  registra o atalho do config.toml
```

## Configuração

Opcional: copie `data/config.example.toml` para `~/.config/findr/config.toml`
(pastas indexadas, exclusões, profundidade, buscador web, atalho, modo overlay…).

## Arquitetura

Camadas no estilo *ports & adapters*. Dependências apontam sempre para dentro e o
domínio não conhece GTK:

```
src/findr/
├── domain/          Regras puras: Query, SearchResult, FuzzyMatcher, Actions, ports
├── providers/       Fontes de resultado (Strategy): apps, arquivos, calculadora, web
├── services/        SearchEngine (Facade), ranking por uso, agrupamento estilo Spotlight
├── infrastructure/  Adapters: Gio (apps), índice de arquivos, GSettings (atalho), JSON, TOML
├── ui/              GTK 3 em MVP: LauncherWindow (view passiva) + SearchController (presenter)
└── app.py           Composition root: monta o grafo de objetos (injeção de dependências)
```

| Padrão / prática           | Onde                                                                 |
|----------------------------|----------------------------------------------------------------------|
| Strategy                   | `SearchProvider`: cada fonte de busca é intercambiável               |
| Command                    | `domain/actions.py`: cada resultado carrega a ação que executa       |
| Facade                     | `SearchEngine`: espalha a consulta, deduplica, ranqueia e agrupa     |
| Adapter / Ports & Adapters | `DesktopPort`→`GtkDesktop`, `AppCatalog`→`GioApplicationCatalog`     |
| Repository                 | `JsonUsageRepository` (histórico de uso, escrita atômica)            |
| Observer                   | `Gio.AppInfoMonitor` recarrega apps; sinais GTK → presenter          |
| MVP                        | `LauncherWindow` (view) ↔ `SearchController` (presenter)             |
| Single instance + D-Bus    | `Gtk.Application`; `findr-toggle` chama a GAction `toggle`         |
| Dependency Injection       | Tudo é construído em `app.py`; testes usam fakes (`tests/fakes.py`)  |

### Decisões técnicas

- **Atalho global no Wayland:** apps não podem capturar teclas globais no Wayland. O
  atalho é registrado no próprio GNOME (custom keybinding) e executa `findr-toggle`,
  que ativa a instância residente via D-Bus (`gdbus`), sem iniciar Python a cada
  toque. O token de ativação é repassado para a janela poder receber o foco.
- **Busca não bloqueante:** debounce de 60 ms, busca numa thread de trabalho e
  resultados devolvidos à thread de UI com `GLib.idle_add`. Respostas atrasadas de
  consultas antigas são descartadas por número de geração.
- **Índice de arquivos:** varredura em largura (BFS) da home em segundo plano, a cada
  10 min, com limite de profundidade e de entradas. A troca do snapshot é atômica, então
  a busca nunca vê um índice pela metade. Cada consulta leva cerca de 10 ms com ~30 mil arquivos.
- **Calculadora segura:** avalia a AST com lista branca de nós; nunca usa `eval`.
- **Resiliência:** se um provedor falhar, o erro é registrado no log e ele é ignorado. A barra continua funcionando.

Logs detalhados: `FINDR_LOG=DEBUG findr`.
