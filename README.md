# 📋 Documentation GCP Services

Gera automaticamente um arquivo **Markdown** com o inventário documentado de todos os serviços ativos e seus objetos dentro de um projeto Google Cloud Platform (GCP).

## 📑 Índice

- [Visão Geral](#visão-geral)
- [Pré-requisitos](#pré-requisitos)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Passo a Passo de Instalação](#passo-a-passo-de-instalação)
- [Autenticação no GCP](#autenticação-no-gcp)
- [Como Usar](#como-usar)
- [Serviços Inventariados](#serviços-inventariados)
- [Exemplo de Saída](#exemplo-de-saída)
- [Permissões IAM Necessárias](#permissões-iam-necessárias)
- [Solução de Problemas](#solução-de-problemas)



## Visão Geral

O script `gcp_inventory.py` conecta-se ao seu projeto GCP utilizando as credenciais já configuradas via `gcloud CLI` e percorre todos os principais serviços ativos, gerando um relatório em Markdown com tabelas detalhadas de cada recurso encontrado.

**O que é gerado:**
- Arquivo `.md` com tabelas por serviço
- Status de cada recurso (ativo/inativo)
- Metadados relevantes (região, tipo, configurações)
- Índice de APIs habilitadas no projeto



## Pré-requisitos

Antes de começar, certifique-se de ter instalado:

| Ferramenta | Versão mínima | Link |
|---|---|---|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| gcloud CLI | qualquer recente | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| bq CLI | incluído no gcloud SDK | — |

Para verificar se estão instalados corretamente:

```bash
python --version
gcloud version
bq version
```


## Estrutura do Projeto

```
documentation-marketing-insights/
├── docs/               # Pasta padrão de saída dos relatórios gerados
├── .gitignore          # Ignora arquivos desnecessários
├── gcp_inventory.py    # Script principal
├── requirements.txt    # Dependências Python
└── README.md           # Este arquivo
```


## Passo a Passo de Instalação

### 1. Clone ou baixe os arquivos do projeto

```bash
# Se estiver em um repositório Git
git clone <url-do-repositorio>
cd documentation-gcp-services

# Ou simplesmente coloque os arquivos em uma pasta
mkdir documentation-gcp-services && cd documentation-gcp-services
```

### 2. Crie um ambiente virtual (virtualenv)

Usar uma virtualenv isola as dependências do projeto e evita conflitos com outros pacotes instalados no sistema.

```bash
# Criar o ambiente virtual na pasta .venv
python -m venv .venv
```

### 3. Ative o ambiente virtual

**Linux / macOS:**
```bash
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
.venv\Scripts\activate.bat
```

> ✅ Você saberá que o ambiente está ativo quando o nome `(.venv)` aparecer no início do terminal.

### 4. Instale as dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> ⏳ A instalação pode levar alguns minutos na primeira vez.


## Autenticação no GCP

O script utiliza as credenciais **Application Default Credentials (ADC)** já configuradas no ambiente via `gcloud`.

### Opção A — Usuário individual (recomendado para uso local)

```bash
# Autenticar com sua conta Google
gcloud auth login

# Configurar as credenciais padrão da aplicação
gcloud auth application-default login

# Definir o projeto padrão (opcional, pode ser passado via argumento)
gcloud config set project SEU_PROJETO_ID
```

### Opção B — Service Account (recomendado para CI/CD ou automação)

```bash
# Exportar a variável com o caminho do arquivo de chave JSON
export GOOGLE_APPLICATION_CREDENTIALS="/caminho/para/service-account.json"
```

> 🔐 Veja a seção [Permissões IAM Necessárias](#permissões-iam-necessárias) para saber quais roles atribuir à Service Account.

## Como Usar

### Uso básico

```bash
python gcp_inventory.py --projeto SEU_PROJETO_ID
```

O arquivo `docs/{project}/inventario.md` será criado na pasta atual.

### Com caminho de saída personalizado

```bash
python gcp_inventory.py --projeto SEU_PROJETO_ID --saida docs/inventario_SEU_PROJETO_ID.md
```

### Parâmetros disponíveis

| Parâmetro | Atalho | Obrigatório | Descrição |
|---|---|---|---|
| `--projeto` | `-p` | ✅ Sim | ID do projeto GCP |
| `--saida` | `-o` | ❌ Não | Caminho do arquivo de saída (padrão: `docs/<projeto>/inventario.md`) |

### Exemplos completos

```bash
# Inventário simples
python gcp_inventory.py -p minha-empresa-prod

# Salvar em subpasta
python gcp_inventory.py -p minha-empresa-prod -o relatorios/inventario-$(date +%Y%m%d).md

# Múltiplos projetos em sequência
for proj in projeto-dev projeto-staging projeto-prod; do
  python gcp_inventory.py -p $proj -o "inventario_${proj}.md"
done
```

### Desativar o ambiente virtual ao terminar

```bash
deactivate
```


## Serviços Inventariados

| Categoria | Serviço | O que é listado |
|---|---|---|
| 🔌 Geral | APIs habilitadas | Nome e título de todas as APIs ativas |
| 🖥️ Compute | Compute Engine | VMs: nome, zona, tipo, status, IPs |
| ☸️ Containers | GKE Clusters | Clusters: nome, localização, versão, nós, status |
| 🏃 Serverless | Cloud Run | Serviços: nome, região, URL, revisão, status |
| ⚡ Serverless | Cloud Functions | Funções: nome, região, runtime, trigger, status |
| 🪣 Storage | Cloud Storage | Buckets: nome, localização, classe, versioning |
| 📊 Analytics | BigQuery | Datasets e tabelas: nome, localização, lista de tabelas |
| 🗄️ Banco de dados | Cloud SQL | Instâncias: nome, versão, região, tier, status |
| 📨 Mensageria | Pub/Sub | Tópicos e subscriptions: nome, tipo (push/pull) |
| 🔐 Segurança | Secret Manager | Segredos: nome, replicação, quantidade de versões |
| 🌐 Rede | VPC Networks | Redes e sub-redes: nome, modo, CIDR, região |
| 🔥 Rede | Firewall Rules | Regras: nome, direção, ação, portas, prioridade |
| ⚖️ Rede | Load Balancers | Forwarding rules: IP, protocolo, portas, target |
| 🕐 Automação | Cloud Scheduler | Jobs: nome, cron, timezone, tipo de target |
| 📋 Automação | Cloud Tasks | Filas: nome, estado, taxa, tentativas |
| 📦 DevOps | Artifact Registry | Repositórios: nome, formato, modo, localização |
| 🔑 IAM | Service Accounts | Contas: email, display name, status |

---

## Exemplo de Saída

```markdown
# 📋 Inventário GCP — `meu-projeto-prod`

> Gerado automaticamente em **17/03/2025 14:32 UTC**

## 🏷️ Informações do Projeto

| Campo          | Valor               |
|----------------|---------------------|
| Project ID     | meu-projeto-prod    |
| Project Number | 123456789012        |
| Estado         | 🟢 ACTIVE           |

---

## 🖥️ Compute Engine — Instâncias (VMs)

| Nome         | Zona              | Tipo de Máquina | Status        | IP Interno | IP Externo   |
|--------------|-------------------|-----------------|---------------|------------|--------------|
| web-server-1 | us-central1-a     | n2-standard-2   | 🟢 RUNNING    | 10.0.0.2   | 34.72.10.100 |
| worker-1     | southamerica-east1-b | e2-medium    | 🟢 RUNNING    | 10.0.0.3   | -            |
```

## Permissões IAM Necessárias

Para que o script funcione completamente, a conta ou Service Account precisa das seguintes roles:

| Role | Descrição |
|---|---|
| `roles/viewer` | Acesso de leitura geral ao projeto (cobre a maioria dos serviços) |
| `roles/bigquery.metadataViewer` | Listar datasets e tabelas do BigQuery |
| `roles/secretmanager.viewer` | Listar segredos no Secret Manager |
| `roles/iam.serviceAccountViewer` | Listar service accounts |

> 💡 **Dica:** A role `roles/viewer` no nível do projeto já cobre a maioria dos recursos. Para ambientes de produção, prefira criar uma role customizada com apenas as permissões `list` e `get` necessárias.

## Solução de Problemas

### ❌ `gcloud: command not found`
Instale o Google Cloud SDK: https://cloud.google.com/sdk/docs/install  
Após instalar, reinicie o terminal e execute `gcloud init`.

### ❌ `PERMISSION_DENIED` em algum serviço
A conta autenticada não tem permissão para listar aquele serviço. Verifique as [permissões IAM](#permissões-iam-necessárias) necessárias.

### ❌ Serviço aparece como "não habilitado"
O serviço pode não estar ativado no projeto. Para habilitar:
```bash
gcloud services enable compute.googleapis.com --project SEU_PROJETO_ID
```

### ❌ `bq: command not found`
O comando `bq` faz parte do Google Cloud SDK. Reinstale o SDK ou execute:
```bash
gcloud components install bq
```

### ⚠️ Ambiente virtual não ativa no Windows
Verifique a política de execução do PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

*Gerado com `gcp_inventory.py` — GCP Project Inventory Script*
