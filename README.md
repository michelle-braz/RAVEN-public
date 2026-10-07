# RAVEN by FOXHUMAN

**Evidências para decidir com clareza.**

O RAVEN ajuda profissionais a transformar um ticket, log ou relato técnico em uma leitura rastreável, reconhecer o que falta confirmar e escolher o próximo passo. O sistema recomenda; o profissional decide.

## Da entrada à decisão

**E-mail e OTP → perfil/área → conteúdo → triagem e método profissional → análise → decisão humana → Histórico.**

Nome de exibição é opcional; sem nome, a conta mostra o e-mail. A área fica salva e pode ser alterada nas Configurações. Cada caso mantém a área utilizada quando foi analisado.

| Área | Contexto |
|---|---|
| QA | Qualidade e Testes |
| SEC | Cibersegurança |
| NET/NOC | Redes |
| INF | Infraestrutura |
| SRE | Confiabilidade |
| SUP | Suporte |

A área orienta o método. Não determina automaticamente gravidade, causa ou prioridade. Sinais de outra especialidade podem apoiar a análise sem trocar a área principal silenciosamente.

## O que aparece na tela

Uma leitura curta dos sinais, lacunas, gravidade/confiança e ações com ferramentas. Evidências, origem e justificativa ficam em um único bloco expansível. **Aprovar, Ajustar e Rejeitar** registram a decisão humana; o Histórico permite reabrir o caso.

Texto, TXT, LOG, JSON e CSV seguem o fluxo suportado. PNG/JPG podem ser anexados para revisão humana; não há interpretação automática das imagens. Não anunciar formatos não suportados.

## Compromissos e limites do piloto

- Evidência vem da entrada; desconhecidos não são preenchidos por plausibilidade.
- Confiança no contexto não comprova causa raiz. Gravidade/impacto podem ficar a determinar.
- Ferramentas são recomendações; ações externas não são executadas automaticamente.
- Histórico não implica treino automático com dados de clientes.
- Piloto pequeno acompanhado; teste local passou até 20 contas simultâneas; a capacidade da análise autenticada em produção ainda não foi certificada.

## Documentação oficial

- [Visão técnica de alto nível](TECHNICAL_OVERVIEW.md)
- [FOXHUMAN — hub público](https://github.com/michelle-braz/foxhuman)
- [Apresentação pública do RAVEN](https://github.com/michelle-braz/foxhuman/blob/main/CAMADA_RAVEN.md)
- [Entrar no piloto](https://raven-pr28-validation-production.up.railway.app/try)

Este repositório contém documentação de produto, não o núcleo ativo. **Permanece privado: seu histórico Git ainda contém código antigo.** A documentação pública segura está no hub FOXHUMAN. Não tornar público o histórico para divulgar somente estes dois documentos.

A implementação e as evidências privadas são mantidas no core privado. Heurísticas, pesos, regras internas, segredos e dados de participantes não fazem parte da apresentação pública.
