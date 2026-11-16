# transportive-ai

Rules first, then tests the agent did not write.

This is the code of the post "Building a Cleaner Way to Code with AI Than Prompting". It turns Jose Crespo's idea of [transportive AI](https://aiadvances.org/the-top-1-of-ai-coders-barely-prompt-they-do-this-instead-0015703c6064) into a working system on the payment module of [Saleor](https://github.com/saleor/saleor), an open-source store. Rules mined from Saleor's code and from payment law become a signed spec. A context engine and a Z3 solver reject conflicts and send gaps to the rule's owner. A small team of agents writes the patch, and rings of checks that the coder did not write decide what ships, with a person reading the receipt last. The coders are Claude Opus 5.5 and Qwen3.8-27B.

## Layout

```
transportive-ai/
├── transportive/
│   ├── config.py      # models, pin, budgets and prices
│   ├── data.py        # refund histories from UCI Online Retail II
│   ├── spec/          # language, canon, recover, registry
│   ├── index/         # semantic, regions
│   ├── engine/        # context, solver, transport
│   ├── coord/         # leases, queue
│   ├── workspace/     # sandbox
│   ├── agents/        # broker, coder, team
│   ├── verify/        # rings, model, race, compile, mutate
│   ├── guard/         # schema, monitor
│   ├── ledger/        # trace
│   ├── loop/          # journal, deliver
│   └── eval/          # suite, harness
├── assets/            # specs, tickets, decisions, prompts, rule texts and the room files
├── results/           # every number the post prints, and derive.py
├── data/              # the UCI file goes here
├── run_study.py       # every arm, both coders, every sealed ticket
└── notebook.ipynb     # the post's driver cells, in order
```

## Setup

The study uses three computers. A CPU box runs the harness, the rooms and Postgres, a GPU box serves Qwen, and the Anthropic API serves Opus.

On the CPU box:

```bash
uv sync
git clone https://github.com/saleor/saleor.git
git -C saleor checkout 4cb1609a90eade14b6275a407bc7a00c35698090
docker build -t saleor-pin saleor
export CODER=opus                                            # or qwen
export ANTHROPIC_API_KEY="your key"                          # Opus 5.5
export VLLM_URL="http://your-gpu-box:8000/v1"                # Qwen3.8-27B
export COORD_DSN="postgresql://coord@127.0.0.1:5433/coord"   # the leases live here
uv run --with jupyterlab jupyter lab
```

On the GPU box, one NVIDIA H100 80GB:

```bash
vllm serve Qwen/Qwen3.8-27B-FP8 --max-model-len 65536 --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder --reasoning-parser qwen3 --enable-prompt-tokens-details
```

Put [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) (CC BY 4.0, Chen 2012) in `data/online_retail_II.xlsx`. Its cancellations give the replay tests real refunds.

The code expects three things:

- **It runs from the repo root**, because `saleor/`, `assets/`, `data/` and `results/` are relative paths.
- **Docker is on the CPU box.** Each candidate patch runs in a sealed room with no route out. Inside it are a worktree at the pin, a Postgres primary and a standby that applies commits two seconds late.
- **The owners sign first.** Spec 1.0 is published with `registry.publish`, the 14 sealed answers in `assets/decisions/tickets/` are drafts until an owner signs them, and the oracles are sealed with `eval.suite.seal`. All of this happens before any agent runs.

## Running the study

`notebook.ipynb` holds the post's driver cells in its order, from the data through the harness. `run_study.py` runs every arm with both coders on every sealed ticket and writes `results/story.jsonl`. `results/derive.py` turns `results/story.json` into `eval.json`, `ablation.json`, `headline.json` and `claims.json`, and recomputes every rate from its counts.

Patches from the study stay on a private fork. Nothing goes upstream to Saleor.

## Not done yet

- **The hidden oracles.** `assets/oracles/` is empty. The 44 oracles are written by hand from the rule texts and the issue texts, never from the open fix pull requests. Each must fail at its bug commit and pass at its fix, which `eval.suite.valid` checks.
- **The fork commits.** The `bug_commit` and `fix_commit` hashes in `assets/tickets/*.yaml` are stand-ins until those commits exist on a private fork of Saleor at the pin.
- **The fold.** A short step that folds `results/story.jsonl` into the `results/story.json` shape that `derive.py` reads is still to write.
- **The room check.** The files in `assets/workspace/` need one run in a real room, where `assets/checks/room.py` must print the five lines of the post's workspace printout.

## Results

`results/` holds the numbers the post prints. Each value is a `{"v": ..., "provisional": ...}` leaf, and it stays marked provisional until a full run replaces it.
