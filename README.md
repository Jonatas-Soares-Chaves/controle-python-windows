# Controle de Brilho Global para Windows

## PiP fantasma

Marque `PiP fantasma (clicar atraves)` na bandeja para os cliques atravessarem a janela PiP. A opcao fica salva e e aplicada tambem a novos PiPs reconhecidos. Desmarque para voltar a interagir com os controles do video. O atalho de guardar/restaurar continua disponivel nos dois modos. Ao sair do aplicativo, o bloqueio dos cliques e removido.

## Escurecimento extra e por guia

Com escurecimento extra configurado, o atalho de brilho alterna entre 100% sem filtro e o menor dos dois campos com o filtro salvo de cada monitor. O filtro fica suspenso no maximo, sem perder sua intensidade. Sem filtro configurado, o atalho continua alternando entre Campo 1 e Campo 2.

- Na bandeja, abra `Escurecimento extra`, escolha o monitor e a intensidade de 0 a 80%. O filtro deixa os cliques atravessarem e salva o ajuste para a proxima inicializacao.
- `Desativar em todas as telas` remove os filtros. Sair do aplicativo tambem remove as camadas da tela.
- O filtro escurece a imagem mesmo com o brilho fisico do monitor no minimo; ele nao reduz o limite fisico da iluminacao do painel.
- Recarregue a extensao em `edge://extensions` ou `chrome://extensions`. Clique no icone da extensao e ajuste `Escurecimento da guia`.
- Cada guia tem um valor independente, mantido ao recarregar e durante a sessao do navegador. Fechar a guia ou reiniciar o navegador encerra esse ajuste.
- Paginas internas do navegador e outras paginas protegidas nao permitem o filtro. O filtro da guia nao altera o PiP; use o controle de transparencia do PiP na bandeja.
- Transparencia real de uma guia exige uma janela separada. O filtro da extensao apenas escurece o conteudo.

Atalhos globais:

- `Ctrl+Alt+B` alterna somente entre `Campo 1` e `Campo 2`
- `Ctrl+Alt+P` guarda ou restaura o video em picture-in-picture
- `Esc` fecha o aplicativo

## Como usar com Python

1. Execute `instalar_dependencias.bat`.
2. Execute `rodar.bat`.
3. O app fica discreto na bandeja do Windows, perto do relogio.

## Como gerar o EXE

1. Execute `instalar_dependencias.bat`.
2. Execute `gerar_exe.bat`.
3. Abra `dist\ControleBrilho.exe`.

## Iniciar com o Windows

Clique com o botao direito no icone da bandeja e marque `Iniciar com o Windows`.

## Modo discreto

O app nao mostra notificacoes quando altera o brilho.

Pelo icone da bandeja, use `Campo 1` e `Campo 2` para escolher valores rapidos,
ou abra `Configurar niveis...` para digitar valores exatos entre `0%` e `100%`.
Na mesma janela, altere `Hotkey brilho` e `Hotkey PiP` para trocar as duas
combinacoes de teclas.
Clique em `Capturar`, segure a combinacao desejada por um instante, e o app
preenche a hotkey automaticamente usando a leitura nativa do Windows. As hotkeys
tambem sao detectadas por leitura direta das teclas, sem depender de reserva de
atalho pelo Windows.

## Picture-in-picture

Quando houver um video em picture-in-picture, a hotkey do PiP pausa o video,
salva a posicao atual e move a janela para a lateral esquerda, deixando apenas
uma faixa visivel. Ao usar a hotkey novamente, o app restaura a posicao salva e
despausa o video.

## Observacao importante

As hotkeys sao globais. Portanto, funcionam mesmo quando outro programa estiver
em primeiro plano.

Em alguns computadores, a biblioteca `keyboard` pode exigir executar o app como
administrador para capturar teclas globalmente.
