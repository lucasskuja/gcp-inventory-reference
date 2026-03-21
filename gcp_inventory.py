#!/usr/bin/env python3
"""
GCP Project Inventory Script
Uso: python gcp_inventory.py --projeto <nome_do_projeto>

Gera um arquivo Markdown com o inventário documentado de todos os
serviços ativos e seus objetos dentro de um projeto GCP.

Requisitos:
    pip install google-cloud-compute google-cloud-storage google-cloud-bigquery \
                google-cloud-functions google-cloud-run google-cloud-sql-connector \
                google-cloud-pubsub google-cloud-firestore google-cloud-scheduler \
                google-cloud-tasks google-cloud-secret-manager \
                google-auth google-api-python-client

Autenticação:
    gcloud auth application-default login
    gcloud config set project <nome_do_projeto>
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone


# ──────────────────────────────────────────────────────────────────────────────
# Resolução de executáveis (compatibilidade Windows / Git Bash)
# ──────────────────────────────────────────────────────────────────────────────

def _find_executable(name: str) -> str:
    """
    Retorna o caminho completo do executável, resolvendo extensões .cmd/.bat
    no Windows — necessário no Git Bash, onde scripts .cmd não são resolvidos
    automaticamente pelo subprocess sem shell=True.
    """
    found = shutil.which(name)
    if found:
        return found

    if os.name == "nt":
        for ext in (".cmd", ".bat", ".exe"):
            found = shutil.which(name + ext)
            if found:
                return found

        # Fallback: caminhos padrão de instalação do Google Cloud SDK
        localappdata = os.environ.get("LOCALAPPDATA", "")
        programfiles = os.environ.get("ProgramFiles", "")
        programfiles86 = os.environ.get("ProgramFiles(x86)", "")
        sdk_dirs = [
            os.path.join(localappdata,    "Google", "Cloud SDK", "google-cloud-sdk", "bin"),
            os.path.join(programfiles,    "Google", "Cloud SDK", "google-cloud-sdk", "bin"),
            os.path.join(programfiles86,  "Google", "Cloud SDK", "google-cloud-sdk", "bin"),
        ]
        for sdk_dir in sdk_dirs:
            for ext in (".cmd", ".bat", ".exe", ""):
                candidate = os.path.join(sdk_dir, name + ext)
                if os.path.isfile(candidate):
                    return candidate

    raise FileNotFoundError(name)


try:
    GCLOUD_BIN = _find_executable("gcloud")
    BQ_BIN     = _find_executable("bq")
    _USE_SHELL = False
except FileNotFoundError:
    # Último recurso: deixa o shell do SO resolver (funciona no cmd.exe nativo)
    GCLOUD_BIN = "gcloud"
    BQ_BIN     = "bq"
    _USE_SHELL = (os.name == "nt")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def run_gcloud(args: list[str], project: str, timeout: int = 30) -> list[dict] | dict | None:
    """Executa um comando gcloud e retorna o resultado como JSON.
    Usa Popen para garantir que o processo seja terminado corretamente
    no Windows quando o timeout expira.
    """
    cmd = [GCLOUD_BIN] + args + ["--project", project, "--format=json"]
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=_USE_SHELL,
        )
        stdout, _ = proc.communicate(timeout=timeout)
        if proc.returncode != 0:
            return None
        output = stdout.strip()
        if not output:
            return []
        return json.loads(output)
    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
            try:
                proc.communicate(timeout=5)
            except Exception:
                pass
        return None
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return None
    except Exception:
        if proc:
            try:
                proc.kill()
                proc.communicate(timeout=5)
            except Exception:
                pass
        return None


def run_gcloud_paged(args: list[str], project: str) -> list[dict]:
    data = run_gcloud(args, project)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Algumas respostas paginadas vêm como {"items": [...]}
        for key in ("items", "managedZones", "zones", "networks", "subnetworks",
                    "firewalls", "addresses", "routers", "vpnTunnels",
                    "forwardingRules", "targetHttpProxies"):
            if key in data:
                return data[key]
        return [data]
    return []


def badge(text: str, ok=True) -> str:
    icon = "🟢" if ok else "🔴"
    return f"{icon} {text}"


def section(title: str, icon: str = "📦") -> str:
    return f"\n## {icon} {title}\n"


def table_header(*cols: str) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
    return f"{header}\n{sep}"


def row(*cols: str) -> str:
    safe = [str(c).replace("|", "\\|").replace("\n", " ") for c in cols]
    return "| " + " | ".join(safe) + " |"


def no_resources(svc: str) -> str:
    return f"> ℹ️ Nenhum recurso `{svc}` encontrado ou serviço não habilitado.\n"


# ──────────────────────────────────────────────────────────────────────────────
# Coletores por serviço
# ──────────────────────────────────────────────────────────────────────────────

def collect_compute_instances(project: str) -> str:
    out = section("Compute Engine — Instâncias (VMs)", "🖥️")
    items = run_gcloud_paged(["compute", "instances", "list"], project)
    if not items:
        return out + no_resources("compute/instances")

    out += table_header("Nome", "Zona", "Tipo de Máquina", "Status", "IP Interno", "IP Externo")
    for i in items:
        name    = i.get("name", "-")
        zone    = i.get("zone", "-").split("/")[-1]
        mtype   = i.get("machineType", "-").split("/")[-1]
        status  = i.get("status", "-")
        nifs    = i.get("networkInterfaces", [{}])
        int_ip  = nifs[0].get("networkIP", "-") if nifs else "-"
        acs     = nifs[0].get("accessConfigs", []) if nifs else []
        ext_ip  = acs[0].get("natIP", "-") if acs else "-"
        out    += "\n" + row(name, zone, mtype, badge(status, status == "RUNNING"), int_ip, ext_ip)
    return out + "\n"


def collect_gke_clusters(project: str) -> str:
    out = section("GKE — Clusters Kubernetes", "☸️")
    items = run_gcloud_paged(["container", "clusters", "list"], project)
    if not items:
        return out + no_resources("container/clusters")

    out += table_header("Nome", "Localização", "Versão do Master", "Nós", "Status")
    for c in items:
        name     = c.get("name", "-")
        loc      = c.get("location", "-")
        version  = c.get("currentMasterVersion", "-")
        nodes    = c.get("currentNodeCount", "-")
        status   = c.get("status", "-")
        out     += "\n" + row(name, loc, version, nodes, badge(status, status == "RUNNING"))
    return out + "\n"


# Regiões onde o Cloud Run managed pode ser implantado
_CLOUD_RUN_REGIONS = [
    "us-central1", "us-east1", "us-east4", "us-west1", "us-west2", "us-west3", "us-west4",
    "northamerica-northeast1", "northamerica-northeast2",
    "southamerica-east1", "southamerica-west1",
    "europe-west1", "europe-west2", "europe-west3", "europe-west4", "europe-west6", "europe-west8", "europe-west9",
    "europe-north1", "europe-southwest1", "europe-central2",
    "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2", "asia-northeast3",
    "asia-south1", "asia-south2", "asia-southeast1", "asia-southeast2",
    "australia-southeast1", "australia-southeast2",
    "me-west1", "me-central1",
]


def collect_cloud_run(project: str) -> str:
    out = section("Cloud Run — Serviços", "🏃")

    # Tenta primeiro com --region=- (lista todas as regiões em uma chamada)
    items = run_gcloud_paged(["run", "services", "list", "--platform=managed", "--region=-"], project)

    # Fallback: percorre regiões explicitamente (necessário em versões antigas do SDK
    # ou quando --region=- não retorna todos os serviços)
    if not items:
        seen = set()
        items = []
        for region in _CLOUD_RUN_REGIONS:
            region_items = run_gcloud_paged(
                ["run", "services", "list", "--platform=managed", f"--region={region}"], project
            ) or []
            for svc in region_items:
                svc_name = svc.get("metadata", {}).get("name", "")
                key = f"{region}/{svc_name}"
                if key not in seen:
                    seen.add(key)
                    items.append(svc)

    if not items:
        return out + no_resources("run/services")

    out += table_header("Nome", "Região", "Imagem", "URL", "Última Revisão", "Status")
    for s in items:
        meta   = s.get("metadata", {})
        status = s.get("status", {})
        spec   = s.get("spec", {})

        name   = meta.get("name", "-")
        region = meta.get("labels", {}).get("cloud.googleapis.com/location", "-")
        url    = status.get("url", "-")
        rev    = status.get("latestCreatedRevisionName", "-")

        # Extrai imagem do container (primeiro container da spec do template)
        containers = (
            spec.get("template", {}).get("spec", {}).get("containers")
            or spec.get("template", {}).get("containers")
            or []
        )
        image = containers[0].get("image", "-") if containers else "-"
        # Encurta hashes SHA256 longos para legibilidade
        if "@sha256:" in image:
            parts = image.split("@sha256:")
            image = parts[0] + "@sha256:" + parts[1][:12] + "..."

        conds  = status.get("conditions", [])
        ready  = next((c for c in conds if c.get("type") == "Ready"), {})
        rstate = ready.get("status", "Unknown")
        out   += "\n" + row(name, region, image, url, rev, badge(rstate, rstate == "True"))
    return out + "\n"


def collect_cloud_functions(project: str) -> str:
    out = section("Cloud Functions", "⚡")
    items = run_gcloud_paged(["functions", "list"], project)
    if not items:
        return out + no_resources("functions")

    out += table_header("Nome", "Região", "Runtime", "Trigger", "Status")
    for f in items:
        name    = f.get("name", "-").split("/")[-1]
        region  = f.get("name", "").split("/")[3] if "/" in f.get("name", "") else "-"
        runtime = f.get("runtime", "-")
        trigger = f.get("httpsTrigger", {}).get("url", f.get("eventTrigger", {}).get("eventType", "-"))
        status  = f.get("status", "-")
        out    += "\n" + row(name, region, runtime, trigger, badge(status, status == "ACTIVE"))
    return out + "\n"


# Mapeamento de locationType para português
_LOCATION_TYPE_MAP = {
    "multi-region": "Multi-região",
    "dual-region":  "Birregional",
    "region":       "Regional",
}


def collect_gcs_buckets(project: str) -> str:
    out = section("Cloud Storage — Buckets", "🪣")

    # Solicita campos explícitos para garantir storageClass e locationType
    fields = (
        "name,location,locationType,storageClass,"
        "versioning,iamConfiguration,timeCreated"
    )
    items = run_gcloud_paged(
        ["storage", "buckets", "list", f"--format=json({fields})"], project
    )

    # Fallback: tenta via gsutil JSON caso gcloud storage não retorne campos
    if not items:
        items = run_gcloud_paged(["storage", "buckets", "list"], project)

    if not items:
        return out + no_resources("storage/buckets")

    out += table_header("Nome", "Localização", "Tipo de Local", "Classe Padrão", "Versioning", "Acesso Uniforme")
    for b in items:
        name      = b.get("name", "-")
        loc       = b.get("location", "-").upper()
        loc_type  = _LOCATION_TYPE_MAP.get(
            b.get("locationType", "").lower(), b.get("locationType", "-")
        )
        # storageClass pode vir como "STANDARD", "NEARLINE", etc.
        cls       = b.get("storageClass", b.get("storage_class", "-"))
        ver       = "✅" if b.get("versioning", {}).get("enabled") else "❌"
        iam_cfg   = b.get("iamConfiguration", {})
        ubla      = iam_cfg.get("uniformBucketLevelAccess", {}).get("enabled", False)
        uniform   = "✅" if ubla else "❌"
        out      += "\n" + row(name, loc, loc_type, cls, ver, uniform)
    return out + "\n"


def collect_bigquery(project: str) -> str:
    out = section("BigQuery — Datasets e Tabelas", "📊")
    datasets = run_gcloud_paged(["alpha", "bq", "datasets", "list"], project)
    if not datasets:
        # Tenta via bq CLI
        try:
            result = subprocess.run(
                [BQ_BIN, "ls", "--format=json", f"--project_id={project}"],
                capture_output=True, text=True, timeout=60, shell=_USE_SHELL
            )
            if result.returncode == 0 and result.stdout.strip():
                datasets = json.loads(result.stdout)
            else:
                return out + no_resources("bigquery/datasets")
        except Exception:
            return out + no_resources("bigquery/datasets")

    if not datasets:
        return out + no_resources("bigquery/datasets")

    out += table_header("Dataset", "Localização", "Tabelas")
    for d in datasets:
        ds_id = d.get("datasetReference", {}).get("datasetId") or d.get("id", "-")
        loc   = d.get("location", "-")

        # Lista tabelas do dataset
        try:
            t_result = subprocess.run(
                [BQ_BIN, "ls", "--format=json", f"--project_id={project}", ds_id],
                capture_output=True, text=True, timeout=60, shell=_USE_SHELL
            )
            tables = json.loads(t_result.stdout) if t_result.returncode == 0 and t_result.stdout.strip() else []
            table_names = ", ".join(t.get("tableReference", {}).get("tableId", "?") for t in tables) or "—"
        except Exception:
            table_names = "—"

        out += "\n" + row(ds_id, loc, table_names)
    return out + "\n"


def collect_cloudsql(project: str) -> str:
    out = section("Cloud SQL — Instâncias", "🗄️")
    items = run_gcloud_paged(["sql", "instances", "list"], project)
    if not items:
        return out + no_resources("sql/instances")

    out += table_header("Nome", "Banco", "Versão", "Região", "Tier", "Status")
    for i in items:
        name    = i.get("name", "-")
        db_ver  = i.get("databaseVersion", "-")
        region  = i.get("region", "-")
        tier    = i.get("settings", {}).get("tier", "-")
        status  = i.get("state", "-")
        db_type = db_ver.split("_")[0] if db_ver != "-" else "-"
        out    += "\n" + row(name, db_type, db_ver, region, tier, badge(status, status == "RUNNABLE"))
    return out + "\n"


def collect_pubsub(project: str) -> str:
    out = section("Pub/Sub — Tópicos e Subscriptions", "📨")
    topics = run_gcloud_paged(["pubsub", "topics", "list"], project)
    subs   = run_gcloud_paged(["pubsub", "subscriptions", "list"], project)

    if not topics and not subs:
        return out + no_resources("pubsub")

    out += "### Tópicos\n\n"
    if topics:
        out += table_header("Nome do Tópico")
        for t in topics:
            out += "\n" + row(t.get("name", "-").split("/")[-1])
        out += "\n"
    else:
        out += no_resources("pubsub/topics")

    out += "\n### Subscriptions\n\n"
    if subs:
        out += table_header("Nome", "Tópico", "Tipo")
        for s in subs:
            name  = s.get("name", "-").split("/")[-1]
            topic = s.get("topic", "-").split("/")[-1]
            stype = "Push" if s.get("pushConfig", {}).get("pushEndpoint") else "Pull"
            out  += "\n" + row(name, topic, stype)
        out += "\n"
    else:
        out += no_resources("pubsub/subscriptions")

    return out


def collect_secret_manager(project: str) -> str:
    out = section("Secret Manager — Segredos", "🔐")
    items = run_gcloud_paged(["secrets", "list"], project)
    if not items:
        return out + no_resources("secrets")

    out += table_header("Nome", "Replicação", "Criado em")
    for s in items:
        name   = s.get("name", "-").split("/")[-1]
        rep    = s.get("replication", {})
        rep_t  = "Automática" if "automatic" in rep else "Manual"
        create = s.get("createTime", "-")[:10]
        out += "\n" + row(name, rep_t, create)
    return out + "\n"


def collect_vpc_networks(project: str) -> str:
    out = section("VPC — Redes e Sub-redes", "🌐")
    networks = run_gcloud_paged(["compute", "networks", "list"], project)
    if not networks:
        return out + no_resources("compute/networks")

    out += "### Redes\n\n"
    out += table_header("Nome", "Modo de Sub-rede", "MTU")
    for n in networks:
        name = n.get("name", "-")
        mode = n.get("autoCreateSubnetworks") and "Automático" or "Customizado"
        mtu  = n.get("mtu", "1460")
        out += "\n" + row(name, mode, str(mtu))
    out += "\n"

    subnets = run_gcloud_paged(["compute", "networks", "subnets", "list"], project)
    if subnets:
        out += "\n### Sub-redes\n\n"
        out += table_header("Nome", "Rede", "Região", "CIDR", "Acesso Privado Google")
        for s in subnets:
            sname  = s.get("name", "-")
            net    = s.get("network", "-").split("/")[-1]
            region = s.get("region", "-").split("/")[-1]
            cidr   = s.get("ipCidrRange", "-")
            pga    = "✅" if s.get("privateIpGoogleAccess") else "❌"
            out   += "\n" + row(sname, net, region, cidr, pga)
        out += "\n"

    return out


def collect_firewall_rules(project: str) -> str:
    out = section("Firewall — Regras", "🔥")
    items = run_gcloud_paged(["compute", "firewall-rules", "list"], project)
    if not items:
        return out + no_resources("compute/firewall-rules")

    out += table_header("Nome", "Rede", "Direção", "Ação", "Prioridade", "Portas/Protocolos")
    for f in items:
        name      = f.get("name", "-")
        network   = f.get("network", "-").split("/")[-1]
        direction = f.get("direction", "-")
        action    = "ALLOW" if "allowed" in f else "DENY"
        priority  = f.get("priority", "-")
        rules     = f.get("allowed", f.get("denied", []))
        ports_str = "; ".join(
            r.get("IPProtocol", "?") + ((":" + ",".join(r.get("ports", []))) if r.get("ports") else "")
            for r in rules
        )
        out += "\n" + row(name, network, direction, action, str(priority), ports_str or "all")
    return out + "\n"


def collect_load_balancers(project: str) -> str:
    out = section("Load Balancers — Forwarding Rules", "⚖️")
    items = run_gcloud_paged(["compute", "forwarding-rules", "list"], project)
    if not items:
        return out + no_resources("compute/forwarding-rules")

    out += table_header("Nome", "Região", "IP", "Protocolo", "Porta(s)", "Target")
    for f in items:
        name    = f.get("name", "-")
        region  = f.get("region", "global").split("/")[-1] if f.get("region") else "global"
        ip      = f.get("IPAddress", "-")
        proto   = f.get("IPProtocol", "-")
        ports   = f.get("portRange", f.get("ports", ["-"]))
        if isinstance(ports, list):
            ports = ", ".join(ports)
        target  = f.get("target", "-").split("/")[-1]
        out    += "\n" + row(name, region, ip, proto, str(ports), target)
    return out + "\n"


# Regiões onde Cloud Scheduler está disponível
_SCHEDULER_REGIONS = [
    "us-central1", "us-east1", "us-east4", "us-west1", "us-west2", "us-west3",
    "northamerica-northeast1", "northamerica-northeast2",
    "southamerica-east1",
    "europe-west1", "europe-west2", "europe-west3", "europe-west4", "europe-west6",
    "europe-north1", "europe-central2",
    "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2", "asia-northeast3",
    "asia-south1", "asia-southeast1", "asia-southeast2",
    "australia-southeast1",
]


def collect_cloud_scheduler(project: str) -> str:
    out = section("Cloud Scheduler — Jobs", "🕐")

    # Tenta com --location=- (flag global suportada em versões recentes)
    items = run_gcloud_paged(["scheduler", "jobs", "list", "--location=-"], project)

    # Fallback: percorre regiões explicitamente
    if not items:
        seen = set()
        items = []
        for region in _SCHEDULER_REGIONS:
            region_items = run_gcloud_paged(
                ["scheduler", "jobs", "list", f"--location={region}"], project
            ) or []
            for job in region_items:
                job_name = job.get("name", "")
                if job_name not in seen:
                    seen.add(job_name)
                    items.append(job)

    if not items:
        return out + no_resources("scheduler/jobs")

    out += table_header("Nome", "Região", "Agenda (Cron)", "Timezone", "Target", "URL/Tópico", "Estado")
    for j in items:
        full_name = j.get("name", "-")
        name      = full_name.split("/")[-1]
        # Extrai região do nome completo: projects/P/locations/REGION/jobs/NAME
        parts     = full_name.split("/")
        region    = parts[3] if len(parts) >= 4 else "-"
        schedule  = j.get("schedule", "-")
        tz        = j.get("timeZone", "-")
        state     = j.get("state", "-")

        if j.get("httpTarget"):
            target     = "HTTP"
            target_url = j["httpTarget"].get("uri", "-")
        elif j.get("pubsubTarget"):
            target     = "Pub/Sub"
            target_url = j["pubsubTarget"].get("topicName", "-").split("/")[-1]
        elif j.get("appEngineHttpTarget"):
            target     = "App Engine"
            target_url = j["appEngineHttpTarget"].get("relativeUri", "-")
        else:
            target     = "-"
            target_url = "-"

        out += "\n" + row(name, region, schedule, tz, target, target_url, badge(state, state == "ENABLED"))
    return out + "\n"


# Regiões mais comuns para Cloud Tasks — evita chamada lenta a "locations list"
_TASKS_COMMON_REGIONS = [
    "us-central1", "us-east1", "us-east4", "us-west1", "us-west2",
    "europe-west1", "europe-west2", "europe-west3", "europe-west6",
    "asia-east1", "asia-east2", "asia-northeast1", "asia-southeast1",
    "southamerica-east1",
]


def collect_cloud_tasks(project: str) -> str:
    out = section("Cloud Tasks — Filas", "📋")
    all_queues = []
    for loc_id in _TASKS_COMMON_REGIONS:
        queues = run_gcloud_paged(
            ["tasks", "queues", "list", f"--location={loc_id}"], project
        )
        all_queues.extend(queues or [])

    if not all_queues:
        return out + no_resources("tasks/queues")

    out += table_header("Nome", "Estado", "Max Dispatches/s", "Max Tentativas", "Localização")
    for q in all_queues:
        name     = q.get("name", "-").split("/")[-1]
        state    = q.get("state", "-")
        rate     = q.get("rateLimits", {}).get("maxDispatchesPerSecond", "-")
        retries  = q.get("retryConfig", {}).get("maxAttempts", "-")
        loc      = q.get("name", "").split("/")[5] if "/" in q.get("name", "") else "-"
        out     += "\n" + row(name, badge(state, state == "RUNNING"), str(rate), str(retries), loc)
    return out + "\n"


def _list_docker_images(repo_name: str, location: str, project: str) -> list[dict]:
    """Lista imagens Docker e suas tags de um repositório Artifact Registry."""
    packages = run_gcloud_paged(
        ["artifacts", "docker", "images", "list",
         f"{location}-docker.pkg.dev/{project}/{repo_name}",
         "--include-tags"],
        project,
    )
    return packages or []


def collect_artifact_registry(project: str) -> str:
    out = section("Artifact Registry — Repositórios e Imagens", "📦")
    repos = run_gcloud_paged(["artifacts", "repositories", "list", "--location=-"], project)
    if not repos:
        return out + no_resources("artifacts/repositories")

    for r in repos:
        full_name = r.get("name", "-")
        repo_name = full_name.split("/")[-1]
        fmt       = r.get("format", "-")
        mode      = r.get("mode", "-")
        loc       = full_name.split("/")[3] if len(full_name.split("/")) > 3 else "-"
        create    = r.get("createTime", "-")[:10]
        desc      = r.get("description", "")

        out += f"\n### 📁 `{repo_name}`\n\n"
        out += f"| Campo | Valor |\n|---|---|\n"
        out += f"| Formato | {fmt} |\n"
        out += f"| Modo | {mode} |\n"
        out += f"| Localização | {loc} |\n"
        out += f"| Criado em | {create} |\n"
        if desc:
            out += f"| Descrição | {desc} |\n"
        out += "\n"

        # Lista imagens para repositórios Docker
        if fmt.upper() == "DOCKER":
            images = _list_docker_images(repo_name, loc, project)
            if images:
                out += table_header("Imagem", "Tags", "Digest (curto)", "Atualizado em")
                for img in images:
                    # Campos variam entre versões do SDK
                    img_uri  = img.get("package", img.get("image", img.get("name", "-")))
                    img_name = img_uri.split("/")[-1] if "/" in img_uri else img_uri
                    tags     = ", ".join(img.get("tags", []) or [img.get("tag", "-")]) or "—"
                    digest   = img.get("version", img.get("digest", "-"))
                    if digest and len(digest) > 20:
                        digest = digest[:19] + "..."
                    updated  = (img.get("updateTime") or img.get("createTime") or "-")[:10]
                    out     += "\n" + row(img_name, tags, digest, updated)
                out += "\n"
            else:
                out += "> ℹ️ Nenhuma imagem encontrada neste repositório.\n\n"
        else:
            # Para formatos não-Docker (Maven, npm, Python, etc.) lista pacotes genéricos
            packages = run_gcloud_paged(
                ["artifacts", "packages", "list",
                 f"--repository={repo_name}", f"--location={loc}"],
                project,
            )
            if packages:
                out += table_header("Pacote", "Criado em")
                for pkg in packages:
                    pkg_name = pkg.get("name", "-").split("/")[-1]
                    pkg_date = pkg.get("createTime", "-")[:10]
                    out     += "\n" + row(pkg_name, pkg_date)
                out += "\n"
            else:
                out += "> ℹ️ Nenhum pacote encontrado neste repositório.\n\n"

    return out


def collect_service_accounts(project: str) -> str:
    out = section("IAM — Service Accounts", "🔑")
    items = run_gcloud_paged(["iam", "service-accounts", "list"], project)
    if not items:
        return out + no_resources("iam/service-accounts")

    out += table_header("Email", "Display Name", "Desativada")
    for sa in items:
        email    = sa.get("email", "-")
        display  = sa.get("displayName", "-")
        disabled = "🔴 Sim" if sa.get("disabled") else "🟢 Não"
        out     += "\n" + row(email, display, disabled)
    return out + "\n"


def collect_enabled_apis(project: str) -> str:
    out = section("APIs e Serviços — Habilitados", "🔌")
    items = run_gcloud_paged(
        ["services", "list", "--enabled", "--filter=state:ENABLED"], project
    )
    if not items:
        return out + no_resources("services")

    out += table_header("Nome da API", "Título")
    for s in items:
        name  = s.get("name", "-").split("/")[-1]
        title = s.get("config", {}).get("title", s.get("title", "-"))
        out  += "\n" + row(name, title)
    return out + "\n"


# ──────────────────────────────────────────────────────────────────────────────
# Informações do Projeto
# ──────────────────────────────────────────────────────────────────────────────

def get_project_info(project: str) -> dict:
    info = run_gcloud(["projects", "describe", project], project)
    if isinstance(info, list) and info:
        info = info[0]
    return info or {}


# ──────────────────────────────────────────────────────────────────────────────
# Geração do Markdown
# ──────────────────────────────────────────────────────────────────────────────

def generate_markdown(project: str) -> str:
    print(f"\n🔍 Coletando inventário do projeto: {project}\n")

    info        = get_project_info(project)
    project_num = info.get("projectNumber", "-")
    project_id  = info.get("projectId", project)
    state       = info.get("lifecycleState", "-")
    now         = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    md  = f"# 📋 Inventário GCP — `{project_id}`\n\n"
    md += f"> Gerado automaticamente em **{now}**\n\n"
    md += "## 🏷️ Informações do Projeto\n\n"
    md += table_header("Campo", "Valor")
    md += "\n" + row("Project ID",     project_id)
    md += "\n" + row("Project Number", project_num)
    md += "\n" + row("Estado",         badge(state, state == "ACTIVE"))
    md += "\n\n"

    collectors = [
        ("APIs Habilitadas",       collect_enabled_apis),
        ("Compute Engine",         collect_compute_instances),
        ("GKE Clusters",           collect_gke_clusters),
        ("Cloud Run",              collect_cloud_run),
        ("Cloud Functions",        collect_cloud_functions),
        ("Cloud Storage",          collect_gcs_buckets),
        ("BigQuery",               collect_bigquery),
        ("Cloud SQL",              collect_cloudsql),
        ("Pub/Sub",                collect_pubsub),
        ("Secret Manager",         collect_secret_manager),
        ("VPC Networks",           collect_vpc_networks),
        ("Firewall",               collect_firewall_rules),
        ("Load Balancers",         collect_load_balancers),
        ("Cloud Scheduler",        collect_cloud_scheduler),
        ("Cloud Tasks",            collect_cloud_tasks),
        ("Artifact Registry",      collect_artifact_registry),
        ("Service Accounts",       collect_service_accounts),
    ]

    for label, fn in collectors:
        print(f"  ▸ Coletando {label}...")
        try:
            md += fn(project)
        except Exception as e:
            md += section(label) + f"> ⚠️ Erro ao coletar: `{e}`\n"

    md += "\n---\n\n"
    md += f"*Inventário gerado pelo script `gcp_inventory.py` em {now}.*\n"

    return md


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Gera inventário Markdown de um projeto GCP."
    )
    parser.add_argument(
        "--projeto", "-p",
        required=True,
        help="ID do projeto GCP (ex: meu-projeto-123)"
    )
    parser.add_argument(
        "--saida", "-o",
        default=None,
        help="Caminho do arquivo de saída (padrão: docs/<projeto>/inventario.md)"
    )
    args = parser.parse_args()

    project   = args.projeto
    output    = args.saida or f"docs/{project}/inventario.md"

    # Verifica se gcloud está disponível
    try:
        result = subprocess.run(
            [GCLOUD_BIN, "version"], capture_output=True, timeout=15, shell=_USE_SHELL
        )
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ gcloud CLI não encontrado no PATH.")
        print("   Instale em: https://cloud.google.com/sdk/docs/install")
        print("   Após instalar, reinicie o terminal e tente novamente.")
        print(f"\n   Executável procurado: {GCLOUD_BIN}")
        sys.exit(1)

    md = generate_markdown(project)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\n✅ Inventário salvo em: {output}")
    print(f"   Tamanho: {len(md):,} caracteres\n")


if __name__ == "__main__":
    main()