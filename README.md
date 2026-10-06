# RAVEN by FOXHUMAN

> **Human-centered decision support for technical investigation.**  
> RAVEN helps professionals turn scattered signals into a structured investigation, a clear recommendation and a recorded human decision.

---

## 🧭 What RAVEN does

Technical work often starts with incomplete information:

- a failed test;
- an unexpected deployment effect;
- suspicious behavior;
- latency or packet loss;
- a configuration change;
- a user report without enough context.

RAVEN organizes that uncertainty into a professional investigation flow.

**Input → Professional area → Triage → Relevant investigation → Result → Human decision → History**

The system recommends. **The professional decides.**

---

## 👩‍💻 Choose the professional context

RAVEN starts from the area selected by the user. That context guides the investigation without hiding or silently changing the main area.

| Area | Focus |
|---|---|
| 🧪 **QA** | reproduction, regression, environment, test evidence |
| 🔐 **SEC** | exposure, identity, suspicious behavior, impact |
| 🌐 **NET/NOC** | connectivity, DNS, latency, packet loss, routing |
| 🧱 **INF** | resources, configuration, cloud, dependencies |
| 📈 **SRE** | availability, deploys, observability, reliability |
| 🎧 **SUP** | user impact, reproduction, context, escalation |

If signals from another specialty appear, RAVEN can indicate the relationship **without silently replacing the original context**.

---

## 🔎 From a real problem to a decision

### Example

**Input**  
> A regression test started failing after an update.

**RAVEN organizes the analysis into:**

- 📎 evidence supported by the submitted input;
- 💭 working hypothesis;
- 🚨 severity;
- 🎯 priority;
- 📊 confidence;
- 🛠️ recommended action;
- 🔧 suggested tools;
- 👤 professional decision.

The professional can then:

**Approve · Adjust · Reject**

The case remains available in history with its original context and decision trail.

---

## ✨ What the professional sees

RAVEN keeps the interface simple while the investigation logic stays behind the scenes.

**The result prioritizes:**

1. Evidence
2. Hypothesis
3. Severity / confidence / priority
4. Recommended action
5. Tools
6. Human decision
7. Technical details on demand
8. Original input
9. History and follow-up

> RAVEN does not invent evidence to fill the interface.  
> When evidence is insufficient, that limitation should be explicit.

---

## 🧩 Typical use cases

### 🧪 QA
“Something that passed before is failing after the latest update.”

### 🔐 SEC
“There is suspicious account behavior and I need to structure the investigation.”

### 🌐 NET/NOC
“Latency and packet loss increased and I need to isolate the likely path.”

### 🧱 INF
“A service started failing after a configuration or infrastructure change.”

### 📈 SRE
“Availability degraded after a deployment and I need to assess impact and next action.”

### 🎧 SUP
“A user reports a problem that is difficult to reproduce or route correctly.”

---

## 🏗️ Technical view — high level

RAVEN is designed as a **web application + API + investigation engine**, with account-linked history and human decision at the end of the flow.

It accepts inputs such as text, tickets, logs, files and images, then produces a structured decision-support result.

➡️ **[Open the visual technical overview](TECHNICAL_OVERVIEW.md)**

---

## 🛡️ Public by design, internal by protection

This repository explains **what RAVEN does and how it is used**.

It does **not** expose:

- proprietary heuristics;
- internal weights;
- private decision rules;
- internal investigation methodology;
- private engine implementation.

That separation is intentional.

---

## 🧠 Principles

- **Complexity behind → simplicity in front**
- **Evidence before conclusion**
- **Triage before unnecessary investigation**
- **No silent context switching**
- **No artificial evidence**
- **Human decision remains final**

---

## 🦊 FOXHUMAN

**RAVEN is a FOXHUMAN product.**

FOXHUMAN builds human-centered operational systems that connect software, data, automation, AI and real operational work.
