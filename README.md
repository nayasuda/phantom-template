# 🕵️ Project Phantom

**A multi-agent AI system template powered by Gemini CLI.**

Automate your daily operations with 10 specialized AI agents that collaborate, plan, and execute tasks — from GitHub project management to Gmail classification.

## ✨ Features

- **10 specialized sub-agents** — each with a distinct role (strategist, executor, debugger, etc.)
- **Gemini CLI native** — runs directly in your terminal, no extra infrastructure needed
- **GitHub Project v2 integration** — automated task sync with Google Tasks
- **Gmail auto-classification** — sorts emails into actionable categories using Gemini AI
- **PDCA self-improvement** — agents log failures and learn from past mistakes
- **Hook system** — pre/post tool execution guards (secret detection, git safety, etc.)

## 🚀 Quick Start

### Prerequisites

**Supported OS:** Linux, macOS, Windows (WSL2 / Ubuntu recommended)

| Tool | Version | Purpose |
|------|---------|---------|
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | latest | Core runtime |
| [Node.js](https://nodejs.org/) | v18+ | Gemini CLI dependency |
| [Python](https://python.org/) | 3.10+ | Scripts & hooks |
| [GitHub CLI](https://cli.github.com/) | latest | GitHub integration |
| [Git](https://git-scm.com/) | latest | Version control |

> **Windows users:** Tested on WSL2 (Ubuntu). Native PowerShell is not supported. See [Windows automated setup](#windows-automated-setup) below.

**Required services:**
- Google Workspace (Gmail, Google Drive, Google Tasks)
- GitHub account with Project v2
- Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### Installation

#### Windows (automated setup)

Right-click `setup/setup-windows.bat` → **Run as administrator**. The script will automatically install WSL, Ubuntu, Node.js, Gemini CLI, and GitHub CLI — then walk you through the rest.

> **⚠️ Security software notice:** Some antivirus software (Norton, Windows Defender SmartScreen, etc.) may block `.bat` files from running. If this happens:
> 1. Allow the script in your security software, or
> 2. Follow the manual setup below (Linux / macOS) using WSL terminal directly.

#### Linux / macOS (manual setup)

```bash
# 1. Clone this template
git clone https://github.com/YOUR_USERNAME/phantom-template.git
cd phantom-template

# 2. Run the setup wizard
bash setup.sh

# 3. Configure your API keys
#    Edit .gemini/.env with your credentials

# 4. Install Gemini CLI (if not already installed)
npm install -g @google/gemini-cli

# 5. Launch!
bash phantom_startup.sh
tmux attach -t phantom:main

# To quit: type /quit in Gemini CLI, then:
bash phantom_shutdown.sh
```

> **💡 Once Navi starts, type `/initial_setup`!**
> Navi will guide you through Google OAuth, GitHub Secrets, and enabling scheduled Actions — step by step.
> You can skip or pause any step and resume later by running `/initial_setup` again.

## 🎭 The Agents

| Agent | Role | Specialty |
|-------|------|-----------|
| **Navi** 🛰️ | Orchestrator | Coordinates all agents, talks to you |
| **Queen** 👑 | Strategist | Mission planning & quality checks |
| **Mona** 🐱 | Manager | Task decomposition & PR reviews |
| **Skull** 💀 | Engineer | Git operations & shell execution |
| **Panther** 💃 | Writer | Documentation & reports |
| **Wolf** 🐺 | Backend | APIs & server-side code |
| **Fox** 🦊 | Frontend | UI & client-side code |
| **Noir** 🎀 | Tester | Test creation & verification |
| **Violet** 🎻 | Researcher | Technical research & comparison |
| **Crow** 🪶 | Debugger | Bug analysis & diagnosis |
| **Sophie** 🛡️ | Security | Security audits & risk checks |

## 📁 Structure

```
phantom-template/
├── .gemini/
│   ├── system.md          # Navi's core system prompt
│   ├── agents/            # 10 sub-agent definitions
│   ├── hooks/             # Pre/post execution guards
│   ├── commands/          # Custom slash commands (/mission, /plan, etc.)
│   └── skills/            # Reusable skill documentation
├── scripts/               # Automation scripts (sync, cleanup, etc.)
├── phantom-antenna/       # Gmail classification module
│   └── src/skills/
└── .github/workflows/     # GitHub Actions for scheduled tasks
```

## 📖 Documentation

- [日本語ドキュメント (README_ja.md)](README_ja.md)
- [🔰 Quickstart for Beginners (Japanese)](docs/setup/00_quickstart_for_beginners.md)
- [Prerequisites & Setup](docs/setup/01_prerequisites.md)
- [Google OAuth Setup](docs/setup/02_google_oauth.md)
- [GitHub Project v2 Setup](docs/setup/03_github_project.md)
- [Gemini CLI Setup](docs/setup/04_gemini_cli.md)

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
