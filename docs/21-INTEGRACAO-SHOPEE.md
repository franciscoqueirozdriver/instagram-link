# Integração Shopee Affiliate — estado e configuração

## Estado

O cockpit permite ao Administrador guardar o App ID e App Secret da Shopee Affiliate Open API para a organização selecionada. O backend cifra os campos com a chave Fernet já usada pelo projeto e grava o resultado no schema privado do Supabase, em uma linha vinculada à organização. A API não devolve os valores; a tela mostra somente se a configuração existe. Atualizar requer informar novamente os dois campos. O Operador não acessa a tela nem os endpoints administrativos.

Esta configuração ainda **não** faz busca, ordenação, consulta de comissão, geração de link ou importação. O schema do Explorer oficial não estava visível sem credenciais válidas durante a pesquisa inicial. Não há integração real ou mock apresentado como real.

## Onde configurar localmente

1. Inicie a API local conforme o README (`.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log`).
2. No mesmo computador, abra `http://127.0.0.1:8000/m0/connect#connections` e entre com o usuário Administrador do cockpit.
3. Em **Contas Instagram**, localize **Integração Shopee**.
4. Preencha **App ID da Shopee Affiliate Open API** e **App Secret da Shopee Affiliate Open API**, ambos obtidos no Explorer oficial para a conta/aplicação afiliada que atenderá esta organização, e selecione **Salvar credenciais com segurança**.
5. Após salvar, os campos são limpos e não podem ser consultados de volta pela tela. Para substituir, informe os dois novamente.

Não coloque essas credenciais em `.env.local`, mensagens, capturas, tickets ou logs. Não as copie para o frontend nem compartilhe entre organizações. `TOKEN_ENCRYPTION_KEY` permanece somente no ambiente do backend e não deve ser regenerada.

Se a API não estiver rodando localmente, o campo fica indisponível até iniciar o servidor. A URL de loopback funciona apenas no computador onde a API está ativa; não é URL pública de homologação.

## Contrato oficial ainda por validar

Fonte oficial: [Shopee Affiliate Open API Explorer](https://open-api.affiliate.shopee.com.br/explorer/v2). A interface do Explorer solicita App ID e Secret; a busca inicial não expôs o schema sem essas credenciais. Quando configuradas, validar no Explorer oficial e registrar evidência sanitizada antes de implementar chamadas:

- busca por palavra-chave sem item_id/shop_id;
- parâmetros de filtro e ordenação, campos reais de venda/ranking e janela temporal;
- componentes, condições e teto das comissões aplicáveis;
- preço/moeda, imagem, loja e disponibilidade;
- operação de link e identidade de afiliado que determina a atribuição;
- paginação, limites/rate limit, assinatura, erros GraphQL em HTTP 200, cache e permissão de reutilizar imagens/dados.

Se uma prioridade não estiver disponível, descrever a limitação e propor alternativa antes de mudar a experiência de descoberta. Não chamar produtos de “virais” sem métrica oficial de tendência, não usar preço/comissão indisponível como zero, não gerar link automaticamente ao listar e não fazer scraping.

## Segurança e isolamento

`instagram_link.shopee_organization_credentials` guarda o envelope Fernet. A tabela tem RLS habilitado, sem privilégios para `PUBLIC`, `anon` ou `authenticated`. As rotas administrativas verificam o membership `admin` na organização pedida no backend e exigem a proteção de sessão/CSRF existente. A credencial interna só poderá ser lida pelo serviço autenticado e depois de validar novamente o vínculo à organização. Nunca serialize nem registre o snapshot descriptografado.

Produtos Shopee deverão ser importados no catálogo existente, no escopo da organização. Campanhas continuam usando snapshots imutáveis; a importação não altera versões anteriores. Envios continuam pausados e esta integração não pode chamar mensagens da Meta.
