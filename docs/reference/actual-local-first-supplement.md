ACTUAL is **software**, not “an agent.”

More precisely:

> **ACTUAL is a local-first work-intelligence and automation platform that contains AI/agent-like capabilities inside it.**

Think of it like this:

```text
                    ACTUAL
              ┌───────────────┐
              │   Web App     │
              │   Dashboard   │
              └───────┬───────┘
                      │
                 ACTUAL Backend
                      │
        ┌─────────────┼──────────────┐
        ↓             ↓              ↓
   Workflow Engine   AI Engine    Tool Gateway
        │             │              │
        │          Qwen/Ollama       │
        │             │              │
        └─────────────┼──────────────┘
                      ↓
              Controlled Actions
                      ↓
        Gmail / files / browser / APIs
```

So **AI is inside ACTUAL**. ACTUAL itself is the whole software platform.

## What you'll actually open every day

Initially, you would open something like:

```text
http://localhost:3000
```

and get:

```text
ACTUAL

Today
────────────────────
Jobs worth reviewing        6
Applications awaiting you   2
Follow-ups                  3
Tasks                       4

Career
Work
Automations
Teach
Approvals
Executions
```

It feels like an application, not ChatGPT.

There can still be a little:

> “Ask ACTUAL”

and voice later, but those are interfaces to the platform.

---

# Where should we host it now?

Because you said:

> **privacy matters right now**

I would **not host v0.1 on any cloud.**

Run everything on your computer.

### Local ACTUAL v0.1

```text
YOUR LAPTOP
│
├── ACTUAL Web
│   Next.js
│
├── ACTUAL API
│   FastAPI
│
├── PostgreSQL
│
├── ACTUAL Worker
│
├── Ollama
│    └── Qwen
│
└── local files/storage
```

Run them using:

> **Docker Compose**

except Ollama can stay installed directly on Windows if that's already how you're using it.

Everything communicates through:

```text
localhost
```

So initially:

**Your job data stays locally.**

**Your CVs stay locally.**

**Your personal profile stays locally.**

**Qwen inference stays locally.**

**ACTUAL's database stays locally.**

No reason to send that information to a VPS yet.

---

# Don't use OpenClaw as ACTUAL's foundation

If when you say **OpenCloud** you mean **OpenClaw**:

**No.**

I wouldn't build ACTUAL inside OpenClaw.

You'd end up with:

```text
ACTUAL
  ↓
OpenClaw
  ↓
someone else's agent architecture
```

and lose a lot of the engineering value we're trying to build.

Instead:

```text
ACTUAL
├── owns workflows
├── owns verification
├── owns data
├── owns AI abstraction
├── owns permissions
├── owns evaluations
└── owns automation
```

Later:

```text
OpenClaw
    ↕
ACTUAL API
```

could be useful.

For example:

> “ACTUAL, what jobs need my review?”

through WhatsApp/Telegram/OpenClaw.

But that's optional integration, not ACTUAL itself.

---

# Local-first is actually the best way for you to finish faster

Don't start with:

```text
OVH
Terraform
TLS
domains
cloud networking
managed Postgres
monitoring
Kubernetes
```

before the product works.

That's wasted effort right now.

Build:

```text
Laptop
↓
Docker Compose
↓
ACTUAL
↓
Qwen locally
```

Once ACTUAL genuinely helps you every day:

```text
LOCAL ACTUAL
     ↓
stable
     ↓
tests
     ↓
privacy controls
     ↓
cloud architecture
```

Then deploy.

---

# What about using ACTUAL from your phone?

Later there are two options.

### Option 1 — remain private

Use something like a private VPN/tunnel between your phone and computer.

ACTUAL stays on your machine.

### Option 2 — cloud

Eventually:

```text
Phone/Laptop
      ↓
ACTUAL Cloud
      ↓
OVHcloud
```

with:

```text
authentication
encryption
PostgreSQL
secrets
backups
audit
```

But **not yet**.

---

# And what exactly is the “agent”?

Eventually ACTUAL might have an internal component like:

```text
ACTUAL Intelligence
```

The AI can reason:

> “This job appears to match Karthik's profile.”

or:

> “This repeated workflow probably doesn't require an LLM.”

or:

> “These two executions differ because of this condition.”

But the AI does not get:

```text
shell access
database password
email password
unlimited browser
permission to submit things
```

Instead:

```text
Qwen proposes
     ↓
ACTUAL validates
     ↓
ACTUAL checks permissions
     ↓
you approve if necessary
     ↓
software performs action
```

That's substantially safer.

---

# Since you want to finish ASAP, shrink v0.1 hard

Forget the 27-phase monster for the moment.

## ACTUAL v0.1

Build only this:

```text
                    ACTUAL LOCAL

1. Personal Profile
       ↓

2. Add Job
       ↓

3. Qwen extracts requirements
       ↓

4. ACTUAL compares job
   against verified profile
       ↓

5. Fit + gaps
       ↓

6. Recommend CV
       ↓

7. Generate truthful
   application improvements
       ↓

8. YOU REVIEW
       ↓

9. Track application
       ↓

10. Dashboard
```

UI:

```text
Overview

Jobs

Applications

Profile

Skills

CVs

Settings
```

That's it.

No voice yet.

No process mining yet.

No Teach Mode yet.

No NEXUS integration yet.

No cloud.

No Temporal.

No browser automation.

No enterprise features.

---

# Then v0.2

After you're genuinely using v0.1:

```text
Email integration

Job discovery

Follow-ups

Interview preparation

Skill-gap analytics
```

Now ACTUAL starts saving you more time.

---

# v0.3

Then introduce what makes ACTUAL unique:

```text
Teach Mode
     ↓
observe repetitive workflow
     ↓
Work Graph
     ↓
automation recommendation
```

---

# v0.4

Then:

```text
Workflow IR

Replay

Shadow Mode

Controlled automation
```

Now the original ACTUAL thesis appears.

---

# v0.5

Then:

```text
Voice

NEXUS

advanced permissions

more workflows
```

---

# Final form

Eventually:

```text
                  ACTUAL

     ┌──────────────┬───────────────┐
     ↓              ↓               ↓
 Personal        Professional     Enterprise
 workflows       workflows        workflows
     │              │               │
     └──────────────┼───────────────┘
                    ↓
             Work Intelligence
                    ↓
            Workflow Compiler
                    ↓
                AI / Code
                    ↓
                 Replay
                    ↓
                 Shadow
                    ↓
              Authorization
                    ↓
                Execution
                    ↓
               Measurement
```

But **we earn that architecture progressively**.

---

## What I recommend you do in Codex now

Your immediate build environment should be:

```text
Windows
+
WSL2
+
Git
+
Docker Desktop
+
Python
+
Node.js
+
PostgreSQL container
+
Ollama + Qwen
```

and ACTUAL runs entirely on your machine.

So the simplest answer is:

> **ACTUAL is a local-first software platform with an AI reasoning layer—not one AI agent. Build it locally with Next.js + FastAPI + PostgreSQL + Ollama/Qwen + Docker Compose. Don't use OpenClaw or cloud infrastructure as the foundation right now. Get ACTUAL v0.1 useful for your own job/work workflow first; then gradually add Teach Mode, verified automation, voice, NEXUS and cloud deployment.**

Given your **privacy + finish-ASAP** constraints, that's the architecture I'd choose without hesitation.