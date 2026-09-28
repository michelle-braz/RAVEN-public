# Workspace Operacional FOXHUMAN — o desenho

> Versão principal. Tradução em inglês: [`foxhuman-workspace.md`](foxhuman-workspace.md).
>
> Este documento descreve o **desenho** da camada de workspace que a FOXHUMAN
> constrói sobre a RAVEN. A implementação não faz parte desta edição pública.
> Todos os exemplos aqui são sintéticos.

## O problema

Pesquisa com profissionais de QA mostrou que o gargalo não é falta de
ferramenta. É o custo de reconstruir contexto:

- procurar evidência em várias ferramentas;
- repetir verificação que outra pessoa já fez;
- refazer teste porque não existe histórico do que já foi testado;
- complementar ticket que voltou do desenvolvimento;
- explicar o mesmo contexto de novo para a próxima pessoa.

Quando um ticket volta do desenvolvimento, os motivos se repetem: não dá para
reproduzir, faltam logs ou evidências, os passos não estão claros, o resultado
esperado não foi explicado, faltam ambiente e versão, e não está claro o que já
foi testado.

Isso é QA falando, mas descreve igualmente o trabalho de SRE, Suporte e
Engenharia: reunir contexto, separar evidência de hipótese, ver o que falta,
decidir, e não perder o que foi aprendido.

## A hipótese

Um workspace operacional que transforma informação fragmentada em contexto
acionável, com **uma base só** para diferentes profissionais técnicos.

**Regra permanente:** não segmentar o produto pela profissão. Segmentar a
experiência pelo trabalho que aquela profissão precisa executar.

## O ciclo

```
sinal ou tarefa entra
   → contexto é reunido
   → evidências são organizadas
   → lacunas são identificadas
   → próxima ação é apresentada
   → humano decide
   → histórico fica preservado
```

Uma entidade percorre esse ciclo: o **Caso**. O estado é derivado do que o caso
tem, nunca atribuído, então um estado inválido não pode existir.

Só uma transição depende do tipo de trabalho: sair de "lacunas identificadas"
para "próxima ação pronta". Todo o resto do ciclo é idêntico para qualquer
função.

## Perfis de trabalho

Um perfil declara quatro coisas: quais sinais iniciam o trabalho, quais lacunas
contam, quais delas travam o encaminhamento e como o resultado é enquadrado
quando sai.

| Perfil | Entra | Sai |
| --- | --- | --- |
| Reproduzir e encaminhar | bug, ticket | contexto pronto para desenvolvimento |
| Estabilizar e priorizar | alerta, métrica | prioridade e próxima ação |
| Atender e direcionar | relato, ticket | encaminhamento correto |
| Investigar e corrigir | incidente, ticket | investigação técnica |

O mesmo caso avaliado sob dois perfis produz conjuntos de lacunas diferentes e
posições diferentes no ciclo — nunca ciclos diferentes. Acrescentar um quinto
tipo de trabalho é acrescentar uma declaração, não uma ramificação do produto.

## O que a RAVEN entrega para isso

Tudo abaixo já existe na RAVEN e é reaproveitado sem alteração:

| Peça | Contribuição |
| --- | --- |
| Pipeline Sentinel | score de risco, severidade, identificador estável de incidente, detecção de recorrência |
| Camada de enriquecimento | tipo de evento, objeto monitorado, prioridade, evidência, hipótese, próximos passos, impacto |
| Memória validada | resoluções aprovadas por analista |
| Registro de impacto | cada decisão tomada conta para a métrica de decisões influenciadas |

A camada de workspace **não reavalia nada**. Ela transforma o que a RAVEN
devolve em trabalho pronto para andar.

## Classificação da causa

O `event_type` da RAVEN é vocabulário de SRE. O operador triaga por outra
pergunta: quem deve olhar isto?

| Categoria | Deriva de |
| --- | --- |
| Suspeita de segurança | atividade suspeita |
| Erro de configuração | falha ligada a implantação, correlação com mudança, termo de config/segredo |
| Infra / rede | origem de infraestrutura ou rede, latência sem implantação, timeout ou saturação |
| Bug de backend | aumento de erros, indisponibilidade, 5xx, exception, traceback |
| Uso incorreto | sinal de baixo risco sem classe de erro em nenhuma regra acima |

A ordem carrega decisões. Segurança nunca é dobrada em outra caixa. Um 500 logo
depois de um rollout é história de mudança antes de ser bug. "Uso incorreto" —
a única categoria que significa "nada quebrou" — vem por último, para nunca
engolir um defeito real.

Nada disso altera o `risk_score` nem a severidade que a RAVEN produziu.

## Lacunas

Cada motivo de devolução vira uma verificação. Uma lacuna registra também
**como** foi fechada: pela análise, sozinha, ou por uma pessoa que precisou
preencher. Essa distinção é o argumento do produto, então é dado, não texto.

Quando falta item obrigatório, o encaminhamento é **recusado** e diz o que
falta — em vez de deixar sair incompleto, que é a causa número um de retrabalho.

## Barra de comando

Uma linha entra, uma resposta sai. O risco é classificado em código auditável,
nunca por um modelo:

- leitura executa direto;
- escrita reversível executa e oferece desfazer;
- ação destrutiva não executa nada até a pessoa confirmar.

O interpretador é determinístico e não depende de modelo de linguagem. Um modelo
pode ser acrescentado na frente para ampliar o que ele entende; nunca para
decidir se uma ação é segura.

## Honestidade sobre integrações

Um conector que não existe nunca é apresentado como conectado. O estado real de
cada conexão fica visível, com o motivo escrito quando ela está apagada.

## Limitações

- Este documento descreve desenho. A implementação não está nesta edição pública.
- Classificação e lacunas são heurísticas determinísticas, não modelos
  aprendidos. A decisão continua sendo da pessoa.
- Hipóteses, próximos passos e categorias exigem verificação humana.
- Todos os exemplos são sintéticos. Nenhum dado operacional real aparece aqui.
