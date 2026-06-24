# Setup Codex/Claude private development environment on OCI/A10 shapes

## Compute node 
Choose the image `Oracle-Linux-9.7-Gen2-GPU-2026.02.28-0` for a shape like `VM.GPU.A10.2` or `VM.GPU.A10.1` 

## Installation 
- On the Oracle Linux 9.7 version install a set of useful tool:

```
sudo dnf update -y
sudo dnf install -y dnf-plugins-core
sudo dnf install -y oracle-epel-release-el9
sudo dnf config-manager --enable ol9_developer_EPEL
sudo dnf update -y

sudo dnf groupinstall -y "Development Tools"

sudo dnf install -y \
  bash zsh \
  coreutils findutils grep sed gawk diffutils patch \
  procps-ng psmisc lsof util-linux which file \
  tar gzip bzip2 xz unzip zip rsync tree less vim nano \
  git git-lfs curl wget ca-certificates openssl \
  jq ripgrep fd-find yq \
  python3 python3-pip python3-devel \
  nodejs npm \
  make cmake gcc gcc-c++ gdb \
  java-17-openjdk java-17-openjdk-devel \
  maven \
  go rust cargo \
  podman podman-compose
```

## ollama/codex/claude install

- install binaries:

```
curl -fsSL https://ollama.com/install.sh | sh
curl -fsSL https://chatgpt.com/codex/install.sh | sh
sudo npm install -g @anthropic-ai/claude-code
```

### Permanent setup:
For a permanent start parameters setup:
```
sudo systemctl edit ollama

#Edit:

[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_SCHED_SPREAD=1"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="OLLAMA_CONTEXT_LENGTH=131072"
Environment="OLLAMA_KEEP_ALIVE=30m"
```
- reload:
```
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### On-demand setup:
Allow to change the context with different LLMs, getting logs.

- stop ollama as system service:

```
sudo systemctl stop ollama
```

- Context setup. In a different shell, start with the max LLM context allowed:

```
OLLAMA_CONTEXT_LENGTH=131072 ollama serve
```

## Use Codex/Claude

- In memory pre-load:
```
curl http://localhost:11434/api/generate -d '{
  "model": "gpt-oss:latest",
  "prompt": "",
  "keep_alive": "30m"
}'
```

- check if loaded:
```
nvidia-smi
```

- in a different shell start codex/ollama
```
ollama launch codex
```
or:
```
ollama launch claude
```

->choose: gpt-oss:latest

- Prompt example to examine java code: 
```
Create DESIGN_DOC.md for all .java files under the current directory.

Do not use a giant inline bash command.
Create a Python script called generate_design_doc.py.
Use Python file traversal with pathlib.
Use a Java parser if available, preferably javalang.
If javalang is not installed, install it with:
  python3 -m pip install --user javalang

For each Java file, extract:
- package
- classes/interfaces/enums/records if possible
- fields/properties
- methods/constructors

Write the result to DESIGN_DOC.md
Run the script.
Then show the first 80 lines of DESIGN_DOC.md
```