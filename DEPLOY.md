# tudo ok

# Deploy no Oracle Cloud (Gratis para Sempre)

Guia passo a passo para hospedar o bot no **Oracle Cloud Always Free Tier** — um servidor virtual dedicado, 24/7, sem custos e sem limite de tempo.

---

## 1. Criar Conta Oracle Cloud

1. Ir a [oracle.com/cloud/free](https://www.oracle.com/cloud/free/)
2. Clicar em **Start for Free**
3. Preencher dados pessoais e criar conta
4. Validar email e telefone
5. Adicionar cartao de credito/debito (usado **apenas** para verificacao, nao e cobrado nada)

> Nota: Recebes $300 de credito para 30 dias de teste. Depois, os servicos "Always Free" continuam para sempre.

---

## 2. Criar Instancia ARM (Ampere A1)

1. Faz login no [Oracle Cloud Console](https://cloud.oracle.com/)
2. No menu lateral: **Compute** > **Instances** > **Create Instance**
3. Preencher:

| Campo | Valor |
|---|---|
| Name | `meubot-ff` |
| Image | **Ubuntu 22.04** ou **Ubuntu 24.04** (Canonical) |
| Shape | **Ampere A1.Flex** (ARM) |
| OCPUs | **1** (minimo) ou **2** |
| RAM | **1 GB** (minimo) ou **2 GB** |
| SSH Key | **Upload** a tua chave Public SSH (ou gerar uma) |

4. Rede: deixar as configuracoes por defeito (VNC automatica)
5. Clicar em **Create**
6. Esperar a instancia ficar **Running** (1-2 minutos)
7. Copiar o **Public IP** da instancia

### Gerar chave SSH (se nao tens)

No teu PC (PowerShell ou Terminal):

```bash
ssh-keygen -t ed25519 -C "meubot"
```

- Guarda a chave em `C:\Users\silvi\.ssh\meubot` (ou similar)
- A chave publica e em `C:\Users\silvi\.ssh\meubot.pub`
- Copia o conteudo da chave `.pub` para o Oracle Cloud Console

---

## 3. Ligar a VM

No teu PC:

```bash
ssh -i C:\Users\silvi\.ssh\meubot ubuntu@IP_PUBLICO
```

Substitui `IP_PUBLICO` pelo IP da instancia Oracle Cloud.

> Nota: No Windows, podes tambem usar o **PuTTY** ou o **Windows Terminal** com SSH.

---

## 4. Instalar dependencias na VM

Uma vez ligado a VM:

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python, pip, git e venv
sudo apt install python3 python3-pip python3-venv git -y

# Verificar versao do Python
python3 --version
```

---

## 5. Clonar e configurar o bot

```bash
# Clonar o repositorio
git clone https://github.com/silvio-blip/MeuBotFF.git
cd MeuBotFF

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variaveis de ambiente
cp .env.example .env
nano .env
```

No `nano`, preenche os teus tokens:

```
DISCORD_TOKEN=O_TEU_TOKEN_AQUI
API_VERCEL_URL=https://ff-id-old.vercel.app/
API_VERCEL_KEY=A_TUA_CHAVE_AQUI
SUPABASE_URL=A_TUA_URL_SUPABASE
SUPABASE_SERVICE_ROLE_KEY=A_TUA_CHAVE_SUPABASE
```

Para guardar no nano: `Ctrl+X`, depois `Y`, depois `Enter`.

---

## 6. Testar o bot

```bash
python main.py
```

Deves ver no Discord que o bot ficou online. Se sim, carrega `Ctrl+P` para parar.

---

## 7. Servico systemd (manter bot 24/7)

Para o bot arrancar automaticamente e continuar a correr mesmo depois de fechar a sessao SSH:

### Criar o servico

```bash
sudo nano /etc/systemd/system/meubot.service
```

Cola o seguinte conteudo:

```ini
[Unit]
Description=S.art Engine Bot - Discord Free Fire
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/MeuBotFF
ExecStart=/home/ubuntu/MeuBotFF/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Para guardar: `Ctrl+X`, depois `Y`, depois `Enter`.

### Ativar e iniciar

```bash
# Recarregar servicos
sudo systemctl daemon-reload

# Ativar para arrancar no boot
sudo systemctl enable meubot

# Iniciar o bot
sudo systemctl start meubot

# Verificar se esta a correr
sudo systemctl status meubot
```

Deves ver `Active: active (running)`.

---

## 8. Comandos Uteis

| Comando | O que faz |
|---|---|
| `sudo systemctl status meubot` | Verificar se o bot esta a correr |
| `sudo systemctl restart meubot` | Reiniciar o bot |
| `sudo systemctl stop meubot` | Parar o bot |
| `journalctl -u meubot -f` | Ver logs ao vivo (Ctrl+C para sair) |
| `journalctl -u meubot --since "1 hour ago"` | Ver logs da ultima hora |
| `sudo systemctl disable meubot` | Desativar arranque automatico |

---

## 9. Atualizar o bot

Quando fizeres alteracoes ao codigo:

```bash
cd ~/MeuBotFF

# Descarregar alteracoes
git pull

# Reativar ambiente virtual
source venv/bin/activate

# Atualizar dependencias (se necessario)
pip install -r requirements.txt

# Reiniciar o bot
sudo systemctl restart meubot
```

---

## Resumo Rapido

| Passo | Comando |
|---|---|
| Criar VM | Oracle Cloud Console → Compute → Create |
| Ligar | `ssh -i chave.pem ubuntu@IP` |
| Instalar | `sudo apt install python3 python3-pip python3-venv git -y` |
| Clonar | `git clone https://github.com/silvio-blip/MeuBotFF.git` |
| Configurar | `cp .env.example .env && nano .env` |
| Testar | `python main.py` |
| Servico | Criar `/etc/systemd/system/meubot.service` |
| Iniciar | `sudo systemctl start meubot` |

---

## Problemas Comuns

**Bot nao liga no Discord:**
- Verificar se o `DISCORD_TOKEN` esta correto no `.env`
- Verificar se o bot foi adicionado ao servidor Discord

**Erro de permissao no SSH:**
```bash
chmod 400 ~/.ssh/meubot
```

**Bot desliga e nao volta:**
```bash
sudo systemctl status meubot
journalctl -u meubot -n 50
```

**Quer mudar o IP:**
- No Oracle Cloud Console, parar e reassociar um novo IP elastico

---

Oracle Cloud Always Free Tier e a melhor opcao gratuita para bots Discord porque:
- Nao spinda down (e um servidor dedicado)
- Nao tem limite de tempo
- 1-2 GB de RAM e suficiente para o bot
- Arranca automaticamente no boot da VM
