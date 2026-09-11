# RunPod Pod Control — Implementation Plan

Target version: **v1.7.0** (new feature)
Status: planned, not started
Researched: 2026-09-11

## Goal

Start one of the user's existing RunPod pods from inside Video Creator, so the
3090 is spared and generations run on a faster card (RTX PRO 6000 / A100 SXM).

**Explicitly out of scope:** creating new pods. The user builds and approves pods
manually in the console. This feature only resumes, stops, and reads status.

## User-facing behaviour

1. **On launch** — prompt: "Start a RunPod pod?" [Start] [Stay Local].
   Chosen over silent auto-start so that opening the app to browse the Library
   costs nothing.
2. **On Start** — background chain walks the user's priority-ordered pod list,
   first healthy pod wins. Header shows live progress; UI stays usable.
3. **If a pod is already running** — use it, don't start another. Only one pod
   at a time, ever.
4. **If all candidates fail** — modal: "None of your current pods are available
   to start. Switch to Local?" [Switch to Local] [Cancel].
5. **Manual Stop Pod button** in the header.
6. **On app exit** — automatically stop the pod *the app started*.

## The critical gotcha: zero-GPU resumes

RunPod resumes are pinned to **one specific physical machine**. If that host's
GPU was rented out while the pod was stopped, RunPod starts the pod anyway with
**no GPU**, returns `200 OK`, reaches `RUNNING`, and brings up the proxy URL.
ComfyUI will answer `/system_stats` and run on CPU while billing normally.

Docs: https://docs.runpod.io/pods/troubleshooting/zero-gpus

**A pod counts as healthy only if all three hold:**

- `status == "RUNNING"`
- `gpu.count >= 1`
- `runtime.gpus` non-empty

Anything else means immediately send `{"action":"stop"}` and advance to the next
candidate. Backing out is cheap (per-second billing, no minimum increment), so
the chain should be aggressive about stopping half-started pods.

This also means the chain can legitimately exhaust all five pods — "none
available" is a normal outcome, not an error state.

## API surface

Base: `https://api.runpod.io/v2` — REST v2.
(v1 `rest.runpod.io` retires 2026-11-15; GraphQL retires early 2027. Avoid both.)

Auth: `Authorization: Bearer <key>`

| Operation | Call |
|---|---|
| List pods | `GET /v2/pods` returns `{"pods":[...]}` |
| Pod detail | `GET /v2/pods/{id}` |
| Start | `POST /v2/pods/{id}/action` with `{"action":"start"}` |
| Stop | `POST /v2/pods/{id}/action` with `{"action":"stop"}` |
| GPU availability | `GET /v2/catalog/gpus?include=AVAILABILITY&product=POD&count=1` |

Useful fields on the pod object: `id`, `name`, `status`
(`PROVISIONING|STARTING|RUNNING|EXITED|ERROR|TERMINATED`), `actions` (legal
transitions right now — use instead of hardcoding state logic), `gpu.id`,
`gpu.count`, `dataCenterId`, `cloud`, `runtime` (null unless RUNNING), `cost`
(0.0 while stopped).

`GET /v2/pods` returns stopped pods too, with everything needed to build the
ordering UI — the user never types a pod ID.

### Error handling

`400` is overloaded: it covers both rule violations *and* capacity exhaustion,
with no machine-readable code — only a human-readable `detail` string. Must
substring-match (case-insensitive) on `no longer any instances available`.

Split errors into two classes:

- **Capacity** — advance to next candidate. (400-with-capacity-text, 5xx after a
  re-GET shows not started, zero-GPU, readiness timeout)
- **Fatal** — abort the whole chain, surface to user. (401, 403, 404, 422, 429)

Getting this split wrong in the fatal direction burns the whole list on an auth
typo; wrong in the capacity direction stops on the first pod for the wrong reason.

`409` means the action was illegal for the current status, usually "already
running" — re-GET and decide rather than treating it as a failure.

### Pre-flight availability

`GET /v2/catalog/gpus?include=AVAILABILITY` reports **datacenter-wide** stock,
but a resume is pinned to one host. A datacenter can report `HIGH` while your
specific machine is taken. Use it only to re-order candidates and skip explicit
`NONE` — never to declare a candidate viable, and never let a failed catalog
call block the chain.

### Readiness — two gates

1. **API**: poll `GET /v2/pods/{id}` every 3s, cap 120s, until healthy per the
   three-part check above.
2. **ComfyUI**: poll `GET https://{id}-8188.proxy.runpod.net/system_stats` every
   5s, cap 300s, accept only 200 plus parseable JSON. 404/502/524 all just mean
   "not yet" — don't try to distinguish them.

Proxy URL is fully deterministic: `https://<POD_ID>-<INTERNAL_PORT>.proxy.runpod.net`
(internal port 8188, not the mapped public port). Pod ID and proxy URL are
**stable across unlimited stop/start cycles** — only terminate changes them.
So the app can compute and write `runpod_url` itself; no per-pod URL storage.

Rate limit is ~60 req/min (headers on every response). A 5-pod chain at 3s
polling uses ~20/min. Proxy URL polling is a different service and not counted.

## Code changes

### New: `runpod_api.py`

Pure-`requests` client. No new dependency — `requests` is already a bundled
hidden import in `build_exe.py:57`. **Do not use the official `runpod` SDK**: it
pulls `fastapi[all]`, `boto3`, `cryptography`, `paramiko` (+40-70 MB on the EXE)
and is GraphQL-backed for pods.

- `list_pods()`, `get_pod()`, `start_pod()`, `stop_pod()`, `gpu_availability()`
- `proxy_url(pod_id, port=8188)`
- `Capacity` / `Fatal` exception split
- `_is_healthy(pod)` — the three-part check

### New: `ui/pod_worker.py`

`PodStartWorker(QThread)` following the existing house pattern
(`run_worker.py:86-121`, `ui/run_panel.py:95-111`):
signals `progress(str)`, `candidate(str,str)`, `ready(str,str)`, `exhausted()`,
`failed(str)`.

Must **not** copy `settings_dialog.py:251` `_test_connection()`, which runs a
15s-timeout request on the UI thread. A pod boot wait would freeze the window
for minutes.

Reuse `ComfyClient.test()` (`comfy_client.py:30-33`) as the ComfyUI gate — it
already hits `/system_stats`.

### Changed: `config.py`

Add to `DEFAULT` (`config.py:23-57`). `_load()` merges file over DEFAULT, so
existing configs pick up new keys for free.

- `runpod_pod_order` — list of pod IDs in priority order
- `runpod_auto_prompt` — bool, default true, show the launch prompt
- `runpod_auto_stop_on_exit` — bool, default true
- `runpod_spend_limit` — float USD per pod run, 0 = off
- `runpod_spend_warn_fraction` — float, default 0.8

**No API key in this file.** `video_creator_config.json` is the file
`build_exe.py:110-112` deliberately preserves and copies during deploys.

### Changed: `ui/settings_dialog.py`

New rows in the existing "ComfyUI Server" group (`:42-71`), using the existing
`_text_row` helper (`:175-182`). Pod list with up/down reordering, refresh
button, auto-start and auto-stop checkboxes. Save in `_save()` (`:273-292`).

### Changed: `ui/main_window.py`

- Header row (`:61-76`): Start Pod / Stop Pod button plus status dot, between
  `_mode_lbl` and the Settings button. `_update_mode_label()` (`:155-159`) is
  already the refresh hook.
- Launch prompt after window show.
- `closeEvent` — auto-stop plus in-flight-run guard.
- Pre-flight hook at `_start()` (`:191-197`).

Styling object names from `ui/styles.py`: `secondary_btn`, `small_btn`,
`status_dim`, `status_ok`, `status_err`.

## Credentials

The key lives in **`api_keys.json` next to the EXE**, under `runpod_api_key`,
with the **`RUNPOD_API_KEY` environment variable taking precedence** when set.
Not in `video_creator_config.json`.

`api_keys.json` is gitignored repo-wide by `**/api_keys.json`, so it cannot be
committed by accident. It was copied from `AI_Image_Generator/` (where it had
sat unused) so the app owns its own credential rather than reaching into
another project's folder. **The deployed EXE needs its own copy** — `build_exe.py`
does not currently carry it across, same as `video_creator_config.json`.

RunPod has **no pod-level key scoping** — "Restricted" only scopes Serverless
endpoints, and a Read-Only key gets 403 on the start action. So any key that can
resume a pod can also create and terminate them. That raises the stakes on
storage rather than lowering them.

Neither storage route is encrypted — a plain JSON file is readable by anything
running as the user, and so is an env var (`HKCU\Environment` holds it as plain
text). The user reviewed this and accepted it: the machine is personal, and they
check the RunPod console daily, which also backstops a pod left running by a
crash.

If real encryption is wanted later: Windows DPAPI via `ctypes`
(`CryptProtectData` / `CryptUnprotectData` in `crypt32.dll`) — about 30 lines,
no new package, nothing for PyInstaller to miss.

Env var gotcha if that route is used: variables are captured at process start,
and a PyInstaller EXE launched from Explorer inherits Explorer's environment, so
a newly-set variable may need a sign-out. Set as **User**, not System.

Repo precedent, best to worst: S3 Browser keeps keys out of config entirely
(`~/.aws/credentials`, config stores only the profile name); the separate
`api_keys.json` split used here; Chain Automator has `anthropic_api_key` inline
in `main_config.json` — do not follow that one.


## Spend tracking and session limit

RunPod reports `cost` (USD/hour) and `runtime.uptime` (seconds), so live spend
is the product. Implemented in `runpod_api.py`: `spend_so_far()`,
`spend_summary()`, `limit_state()`, `projected_runtime()`.

**Basis: total pod uptime**, not app-session time. Uptime resets when the pod
starts, so closing and reopening the app cannot reset the budget — only
genuinely stopping and restarting the pod does. Opening the app onto an
already-running pod correctly shows what it has already cost.

**On reaching the limit: finish the current run, then stop.**

- `warn` at 80% — header goes amber, one non-blocking notice
- `over` at 100% — block *new* runs, let the in-flight generation finish,
  then stop the pod and fall back to local

This can overshoot by one generation's cost, which is the deliberate trade: the
alternative throws away work already paid for.

### Two things the UI must not overstate

1. **Compute only.** `cost` excludes storage. Volume disks bill separately, and
   a *stopped* pod's volume bills at double the running rate, so the account
   total moves even with nothing running. Label the figure as compute.
2. **A safety net, not a cap.** Enforcement needs the app alive. A crash or
   reboot leaves the pod running past any limit. The crash-recovery state file
   narrows the window but cannot close it. Say so in the settings copy rather
   than implying a guarantee.

Config keys: `runpod_spend_limit` (float USD, 0 = off),
`runpod_spend_warn_fraction` (default 0.8).

Header shows `2h 15m  |  $4.72` beside the pod indicator, refreshed on a
QTimer (60s is plenty — the figure moves by cents).

## Lifecycle safety

**Crash recovery.** `closeEvent` does not fire on a crash, Task Manager kill, or
power loss — the pod would run until noticed. Mitigation: write the started pod
ID to a small state file next to the EXE on start; clear it on clean exit. On
next launch, if the file still names a pod, check it and offer "Video Creator
didn't shut down cleanly — pod X is still running. Stop it?" Caps the worst case
at one wasted session.

**Only stop what the app started.** Record the pod ID at start time and stop only
that one, so a pod started manually in the console isn't killed on exit.

**Exit during an active render** must warn before stopping the pod.

## Build impact

None. `requests` already bundled (`build_exe.py:57`). `boto3`/`botocore` stay in
`EXCLUDES` (`build_exe.py:23-28`) — the RunPod control plane is plain HTTP and
needs neither. No new venv installs, no changes to the exclude list.

## Cost notes (independent of this feature)

- **Volume disk on a stopped pod bills at $0.20/GB/month — double the running
  rate of $0.10.** Across five stopped pods that is real money for nothing. If
  the data lives on the network volume ($0.07/GB/mo, billed separately),
  shrinking each pod's per-pod volume disk is free savings.
- At a $0 balance RunPod auto-stops running pods; pods *without* a network
  volume get terminated outright. These pods are protected, but a sustained zero
  balance can eventually take the volume too.
- Container disk is wiped on every stop — anything ComfyUI wrote outside the
  network volume mount does not survive a cycle.
- Editing a running pod resets it completely. If a `PATCH` feature is ever added
  (e.g. to expose port 8188), warn loudly.

## Open question

Whether one network volume can be mounted by multiple pods *simultaneously*.
Only matters for starting a second pod while one is running — and since the
chain short-circuits on an already-running healthy pod, and the user wants only
one pod at a time, it is not a blocker. Testable in the console if it ever
comes up.

## Reference

- Zero-GPU on restart: https://docs.runpod.io/pods/troubleshooting/zero-gpus
- Trigger state transition: https://docs.runpod.io/api-reference-v2/pods/trigger-a-pod-state-transition
- List pods: https://docs.runpod.io/api-reference-v2/pods/list-pods
- List GPU types: https://docs.runpod.io/api-reference-v2/catalog/list-gpu-types
- Expose ports / proxy URL: https://docs.runpod.io/pods/configuration/expose-ports
- Storage types: https://docs.runpod.io/pods/storage/types
- Pricing: https://docs.runpod.io/pods/pricing
- API keys: https://docs.runpod.io/get-started/api-keys
