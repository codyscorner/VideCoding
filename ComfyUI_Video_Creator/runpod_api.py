"""RunPod control-plane client — resume, stop and inspect pods the user
already owns.

Deliberately narrow: this never creates or terminates a pod. Pods are built and
approved by hand in the RunPod console; all this module does is wake one up,
put it to sleep, and report what state it is in.

Plain ``requests`` against REST v2 rather than the official ``runpod`` SDK: the
SDK drags in fastapi[all], boto3, cryptography and paramiko (tens of MB onto a
single-file EXE) to make four HTTP calls, and its pod functions still go through
the GraphQL API that RunPod is retiring in early 2027.

No Qt in here on purpose — the whole chain is runnable from a terminal
(``python runpod_api.py wake``) so pod behaviour can be tested without the app.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Callable

import requests

from config import app_dir

API_BASE = "https://api.runpod.io/v2"
API_KEY_ENV = "RUNPOD_API_KEY"

# Fallback when the environment variable isn't set. Lives next to the EXE like
# every other portable file this app owns, and is gitignored repo-wide by
# `**/api_keys.json` so it can't be committed by accident.
KEY_FILE_NAME = "api_keys.json"
KEY_FILE_FIELD = "runpod_api_key"

# ComfyUI's port *inside* the pod. RunPod's HTTP proxy addresses the internal
# port, not the mapped public one, so this is what goes in the hostname.
COMFY_PORT = 8188
PROXY_HOST = "proxy.runpod.net"

HTTP_TIMEOUT = 30           # control-plane calls; these are quick
ACTION_TIMEOUT = 60         # start/stop take a beat longer to be accepted

# A resume only has to bring up a container on a machine that already has the
# image cached, so it is normally 15-60s. Past two minutes something is wrong.
RUNNING_TIMEOUT = 120
RUNNING_INTERVAL = 3

# How long a just-started pod may still report EXITED before that is believed.
# RunPod accepts the start action before the pod leaves EXITED, so polling
# immediately reads the old state.
EXITED_GRACE = 30

# ComfyUI itself then has to scan models and import custom nodes, which is the
# slow part and varies a lot with how many nodes a pod has.
COMFY_TIMEOUT = 300
COMFY_INTERVAL = 5

# Be polite to the ~60 req/min budget when walking several candidates.
CANDIDATE_DELAY = 2.0

# RunPod has no machine-readable "out of capacity" code — a 400 carries both
# rule violations and capacity exhaustion, separated only by human-readable
# text. These are observed strings, not a documented contract, so treat a miss
# as fatal rather than silently burning through every candidate.
CAPACITY_MARKERS = (
    "no longer any instances available",
    "no instances available",
    "not enough capacity",
    "no availability",
    "enough disk space",
)

ACTIVE_STATES = ("RUNNING", "STARTING", "PROVISIONING")
DEAD_STATES = ("EXITED", "ERROR", "TERMINATED")


class RunPodError(Exception):
    """Base for everything this module raises."""


class Unavailable(RunPodError):
    """This particular pod can't run right now — try the next candidate."""


class Fatal(RunPodError):
    """Something wrong with the key, the account or the request. Stop the chain;
    trying four more pods will fail exactly the same way."""


# ---------------------------------------------------------------------- #
# Plumbing
# ---------------------------------------------------------------------- #

def api_key() -> str:
    """Environment variable first, then api_keys.json next to the EXE.

    Never video_creator_config.json: the build script deliberately preserves and
    copies that file on every deploy, so a key in it would travel along with it.
    Keeping the secret in its own gitignored file means the settings file stays
    safe to copy between machines.

    RunPod has no pod-level key scoping, so whatever key this returns can also
    create and terminate pods, not just resume them.
    """
    env = (os.environ.get(API_KEY_ENV) or "").strip()
    if env:
        return env
    try:
        with open(app_dir() / KEY_FILE_NAME, "r", encoding="utf-8") as f:
            return (json.load(f).get(KEY_FILE_FIELD) or "").strip()
    except (OSError, ValueError, AttributeError):
        return ""


def have_key() -> bool:
    return bool(api_key())


def _session(key: str | None = None) -> requests.Session:
    key = key or api_key()
    if not key:
        raise Fatal(
            f"No RunPod API key. Put it in {KEY_FILE_NAME} next to the app as "
            f'"{KEY_FILE_FIELD}", or set the {API_KEY_ENV} environment variable.'
        )
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return s


def _detail(r: requests.Response) -> str:
    """Pull the human-readable bit out of an error body (RFC 9457 or plain)."""
    try:
        body = r.json()
    except ValueError:
        return (r.text or "")[:300]
    if isinstance(body, dict):
        for field in ("detail", "message", "error", "title"):
            if body.get(field):
                return str(body[field])[:300]
    return str(body)[:300]


def _is_capacity(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in CAPACITY_MARKERS)


def proxy_url(pod_id: str, port: int = COMFY_PORT) -> str:
    """Deterministic, and stable for the life of the pod — only terminating a
    pod changes its ID, so this URL survives any number of stop/start cycles."""
    return f"https://{pod_id}-{port}.{PROXY_HOST}"


def test_connection(key: str | None = None) -> tuple[bool, str]:
    """Is RunPod reachable, and does this key work?

    Checks an unauthenticated endpoint first so an outage can be told apart from
    a rejected key — otherwise a bad key and a bad day look identical, and v2
    reports auth failures as a 500 rather than a 401, which makes guessing worse.

    Returns (ok, message) — safe to show straight to the user.
    """
    k = (key or api_key()).strip()
    if not k:
        return False, f"No API key found. Add one to {KEY_FILE_NAME} next to the app."

    # 1. Is RunPod itself up? This needs no auth.
    try:
        r = requests.get(f"{API_BASE}/openapi.json", timeout=15)
        reachable = r.status_code < 500
    except requests.RequestException as e:
        return False, f"Can't reach RunPod at all ({type(e).__name__}). Check your connection."
    if not reachable:
        return False, (f"RunPod's API is returning {r.status_code} on a request that needs no "
                       "key — that's an outage on their end, not your key. Try again later.")

    # 2. Does the key work? v1 and GraphQL give honest 401s where v2 gives 500s,
    #    so they are the ones worth believing about auth.
    headers = {"Authorization": f"Bearer {k}"}
    verdicts = []
    for label, url in (("v2", f"{API_BASE}/pods"),
                       ("v1", "https://rest.runpod.io/v1/pods")):
        try:
            resp = requests.get(url, headers=headers, timeout=20)
        except requests.RequestException as e:
            verdicts.append((label, None, str(e)))
            continue
        verdicts.append((label, resp.status_code, ""))
        if resp.status_code == 200:
            try:
                pods = resp.json()
                pods = pods.get("pods", []) if isinstance(pods, dict) else pods
                return True, f"Connected. {len(pods)} pod(s) on the account."
            except ValueError:
                return True, "Connected, but RunPod returned something that isn't JSON."

    codes = {c for _, c, _ in verdicts}
    if 401 in codes or 403 in codes:
        return False, ("RunPod is up but rejected this key (401). It has most likely been "
                       "revoked or regenerated. Create a new one at console.runpod.io -> "
                       "Settings -> API Keys, with All permissions.")
    detail = ", ".join(f"{lbl}={code or 'error'}" for lbl, code, _ in verdicts)
    return False, (f"RunPod is up but the pod API failed ({detail}). Not clearly an auth "
                   "problem — likely a partial outage. Worth retrying shortly.")


# ---------------------------------------------------------------------- #
# Reads
# ---------------------------------------------------------------------- #

def list_pods(key: str | None = None) -> list[dict]:
    """Every pod on the account, stopped ones included."""
    s = _session(key)
    try:
        r = s.get(f"{API_BASE}/pods", timeout=HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise Fatal(f"Can't reach RunPod ({type(e).__name__}). Check your connection.") from e
    if r.status_code in (401, 403):
        raise Fatal(f"RunPod rejected the API key ({r.status_code}). {_detail(r)}")
    if not r.ok:
        raise Fatal(f"RunPod returned {r.status_code}: {_detail(r)}")
    try:
        return r.json().get("pods", [])
    except ValueError as e:
        raise Fatal(f"RunPod returned something that isn't JSON: {e}") from e


def get_pod(pod_id: str, key: str | None = None, session: requests.Session | None = None) -> dict:
    s = session or _session(key)
    try:
        r = s.get(f"{API_BASE}/pods/{pod_id}", timeout=HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise Unavailable(f"Lost contact while checking {pod_id} ({type(e).__name__}).") from e
    if r.status_code in (401, 403):
        raise Fatal(f"RunPod rejected the API key ({r.status_code}).")
    if r.status_code == 404:
        # One missing pod says nothing about the others — skip, don't abort.
        raise Unavailable(f"pod {pod_id} no longer exists on this account")
    if not r.ok:
        raise Unavailable(f"Couldn't read pod {pod_id}: {r.status_code} {_detail(r)}")
    return r.json()


def gpu_availability(key: str | None = None, cloud: str = "SECURE") -> dict:
    """Datacenter-wide GPU stock, keyed by GPU id.

    Only good for *ordering* candidates. A resume is pinned to one specific
    physical machine, so a datacenter can report HIGH while the one host this
    pod lives on has its GPU rented out. Never treat this as a reservation, and
    never let it fail the chain — an empty dict just means "no opinion".
    """
    try:
        s = _session(key)
        r = s.get(
            f"{API_BASE}/catalog/gpus",
            params={"include": "AVAILABILITY", "product": "POD", "count": 1, "cloud": cloud},
            timeout=HTTP_TIMEOUT,
        )
        if not r.ok:
            return {}
        out = {}
        for g in r.json().get("gpus", []):
            out[g.get("id", "")] = {
                "overall": g.get("availability"),
                "dc": {d.get("id"): d.get("availability") for d in g.get("dataCenters", [])},
            }
        return out
    except (requests.RequestException, ValueError, RunPodError):
        return {}


# ---------------------------------------------------------------------- #
# Health
# ---------------------------------------------------------------------- #

def is_healthy(pod: dict) -> bool:
    """RUNNING is not enough.

    When a pod is stopped it releases its GPU but stays tied to its original
    machine. If someone else rented that GPU in the meantime, RunPod starts the
    pod anyway *with no GPU at all* as a data-recovery mode: HTTP 200, status
    RUNNING, proxy URL up, ComfyUI answering — and billing the whole time, while
    every generation crawls along on CPU.

    https://docs.runpod.io/pods/troubleshooting/zero-gpus
    """
    if (pod.get("status") or "") != "RUNNING":
        return False
    if ((pod.get("gpu") or {}).get("count") or 0) < 1:
        return False
    runtime = pod.get("runtime")
    if not runtime:
        return False
    # Only enforce this when the field is actually present, so a schema change
    # can't make every healthy pod look broken.
    if "gpus" in runtime and not runtime["gpus"]:
        return False
    return True


# ---------------------------------------------------------------------- #
# Spend
# ---------------------------------------------------------------------- #
#
# RunPod gives uptime in seconds and cost in USD/hour, so live spend is just
# the product. Two things this number is NOT:
#
#   * the whole bill — `cost` is compute only. Volume disks bill separately,
#     and a *stopped* pod's volume bills at double the running rate, so the
#     account total keeps moving even when nothing is running.
#   * a hard ceiling — the app can only stop a pod while the app is alive. A
#     crash or a reboot leaves the pod running past any limit set here. Treat
#     the limit as a safety net, and say so in the UI rather than implying a
#     guarantee.
#
# Uptime resets each time a pod starts, which is exactly the "per pod run"
# basis the limit is measured against: closing and reopening the app does not
# reset it, but genuinely stopping and restarting the pod does.

WARN_FRACTION = 0.8


def uptime_seconds(pod: dict) -> int:
    return int((pod.get("runtime") or {}).get("uptime") or 0)


def hourly_cost(pod: dict) -> float:
    """USD/hour. Reads 0.0 for a stopped pod — RunPod zeroes it rather than
    reporting what the pod would cost if it were running."""
    try:
        return float(pod.get("cost") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def spend_so_far(pod: dict) -> float:
    """USD spent on compute since this pod last started."""
    return uptime_seconds(pod) / 3600.0 * hourly_cost(pod)


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def spend_summary(pod: dict) -> str:
    """One short line for the header: '2h 15m  |  $4.72'.

    ASCII only — this string reaches the CLI as well as the GUI, and a Windows
    console on cp1252 turns anything fancier into mojibake.
    """
    if not is_healthy(pod):
        return ""
    return f"{format_duration(uptime_seconds(pod))}  |  ${spend_so_far(pod):.2f}"


def limit_state(pod: dict, limit: float, warn_fraction: float = WARN_FRACTION) -> str:
    """'off' | 'ok' | 'warn' | 'over' for a session spend limit in USD."""
    if not limit or limit <= 0:
        return "off"
    spent = spend_so_far(pod)
    if spent >= limit:
        return "over"
    if spent >= limit * warn_fraction:
        return "warn"
    return "ok"


def projected_runtime(pod: dict, limit: float) -> int:
    """Seconds of GPU time left before the limit is hit, for 'about 40m left'."""
    rate = hourly_cost(pod)
    if not limit or limit <= 0 or rate <= 0:
        return 0
    return max(0, int((limit - spend_so_far(pod)) / rate * 3600))


def describe(pod: dict) -> str:
    """One line for logs and the pod-ordering list."""
    gpu = pod.get("gpu") or {}
    bits = [pod.get("name") or pod.get("id", "?")]
    if gpu.get("id"):
        bits.append(f"{gpu['id']} x{gpu.get('count', 1)}")
    if pod.get("dataCenterId"):
        bits.append(pod["dataCenterId"])
    bits.append(pod.get("status", "?"))
    return "  |  ".join(bits)


# ---------------------------------------------------------------------- #
# Writes
# ---------------------------------------------------------------------- #

def _action(pod_id: str, action: str, session: requests.Session) -> requests.Response:
    return session.post(
        f"{API_BASE}/pods/{pod_id}/action",
        json={"action": action},
        timeout=ACTION_TIMEOUT,
    )


def stop_pod(pod_id: str, key: str | None = None, session: requests.Session | None = None) -> bool:
    """Best-effort. Used both for the Stop button and for backing out of a pod
    that came up wrong, where failing loudly would only obscure the real error."""
    try:
        s = session or _session(key)
        r = _action(pod_id, "stop", s)
        return r.ok
    except (requests.RequestException, RunPodError):
        return False


def start_pod(pod_id: str, key: str | None = None, session: requests.Session | None = None) -> dict:
    """Ask RunPod to resume a stopped pod.

    Returns the updated pod object. Raises Unavailable to move on to the next
    candidate, Fatal to abandon the chain entirely. Note this returns as soon as
    the transition is *accepted* — the pod is not up yet; that's wait_running().
    """
    s = session or _session(key)
    try:
        r = _action(pod_id, "start", s)
    except requests.RequestException as e:
        raise Unavailable(f"Connection dropped starting {pod_id} ({type(e).__name__}).") from e

    # Only two things justify abandoning the whole chain: a key the account
    # won't accept, and a rate limit that will reject the next pod just as fast.
    if r.status_code in (401, 403):
        raise Fatal(f"RunPod rejected the API key ({r.status_code}). A Read-Only key "
                    f"can't start pods. {_detail(r)}")
    if r.status_code == 429:
        raise Fatal(f"Rate limited by RunPod. Retry after {r.headers.get('Retry-After', '?')}s.")

    # Everything else is about THIS pod, so move on to the next candidate.
    if r.status_code == 404:
        raise Unavailable("no longer exists on this account")

    if r.status_code == 400:
        # This request carries no variable parameters — just {"action":"start"}
        # against a pod id that came from RunPod's own listing — so a 400 can't
        # mean "you sent something malformed". In practice it is capacity.
        # The marker list only buys a tidier message, never the decision.
        detail = _detail(r)
        raise Unavailable(detail if detail else "no capacity on that machine right now")

    if r.status_code == 422:
        raise Unavailable(f"rejected by RunPod: {_detail(r)}")

    if r.status_code == 409:
        # The action wasn't legal for the current state — nearly always because
        # the pod is already running or mid-start from an earlier attempt.
        pod = get_pod(pod_id, session=s)
        if pod.get("status") == "RUNNING" and not is_healthy(pod):
            stop_pod(pod_id, session=s)
            raise Unavailable("already running with no GPU")
        return pod

    if r.status_code >= 500:
        # A 5xx can come back *after* the pod actually started, so ask before
        # writing it off.
        pod = get_pod(pod_id, session=s)
        if pod.get("status") in ACTIVE_STATES:
            return pod
        raise Unavailable(f"RunPod server error ({r.status_code}).")

    if not r.ok:
        raise Unavailable(f"Unexpected {r.status_code}: {_detail(r)}")

    try:
        return r.json()
    except ValueError:
        return get_pod(pod_id, session=s)


# ---------------------------------------------------------------------- #
# Readiness — two gates
# ---------------------------------------------------------------------- #

def wait_running(pod_id: str, session: requests.Session,
                 timeout: int = RUNNING_TIMEOUT,
                 log: Callable[[str], None] | None = None,
                 should_cancel: Callable[[], bool] | None = None) -> dict:
    """Gate 1: the control plane says RUNNING *and* a GPU is actually attached.

    Anything else stops the pod before raising, so a half-started pod is never
    left billing in the background.
    """
    log = log or (lambda _m: None)
    started = time.time()
    deadline = started + timeout
    last = ""
    while time.time() < deadline:
        if should_cancel and should_cancel():
            stop_pod(pod_id, session=session)
            raise Unavailable("cancelled")
        pod = get_pod(pod_id, session=session)
        status = pod.get("status", "?")
        if status != last:
            log(f"  {pod_id}: {status}")
            last = status
        if status == "RUNNING":
            if is_healthy(pod):
                return pod
            stop_pod(pod_id, session=session)
            raise Unavailable("started with no GPU attached — that machine's card is taken")
        # A pod that has just been told to start still reads EXITED for a few
        # seconds: the accepted action hasn't moved it yet. Believing that first
        # reading abandons a pod that is in fact coming up perfectly well — and
        # since RunPod carries on booting it, it turns up "available" moments
        # later, which is exactly the false negative this guard exists to stop.
        if status == "EXITED" and time.time() - started < EXITED_GRACE:
            time.sleep(RUNNING_INTERVAL)
            continue
        if status in DEAD_STATES:
            raise Unavailable(f"fell back to {status}")
        time.sleep(RUNNING_INTERVAL)

    stop_pod(pod_id, session=session)
    raise Unavailable(f"still not running after {timeout}s")


def wait_comfy(pod_id: str, timeout: int = COMFY_TIMEOUT,
               log: Callable[[str], None] | None = None,
               should_cancel: Callable[[], bool] | None = None) -> str:
    """Gate 2: ComfyUI is answering on the proxy. Returns the base URL.

    While the service is still coming up the proxy returns 404 (route not known
    yet), 502 (routed, nothing listening) or 524 (Cloudflare's 100s ceiling).
    None of them are worth telling apart — they all mean "not yet".
    """
    log = log or (lambda _m: None)
    url = proxy_url(pod_id)
    deadline = time.time() + timeout
    announced = False
    while time.time() < deadline:
        if should_cancel and should_cancel():
            raise Unavailable("cancelled")
        try:
            r = requests.get(f"{url}/system_stats", timeout=15)
            if r.status_code == 200:
                r.json()
                return url
        except (requests.RequestException, ValueError):
            pass
        if not announced:
            log("  waiting for ComfyUI to finish loading...")
            announced = True
        time.sleep(COMFY_INTERVAL)
    raise Unavailable(f"ComfyUI never answered within {timeout}s")


# ---------------------------------------------------------------------- #
# The chain
# ---------------------------------------------------------------------- #

def wake_first_available(pod_ids: list[str],
                         key: str | None = None,
                         log: Callable[[str], None] | None = None,
                         should_cancel: Callable[[], bool] | None = None,
                         use_availability: bool = True,
                         misses_out: list[str] | None = None) -> tuple[str, str] | None:
    """Walk pod_ids in priority order and bring up the first one that works.

    Returns (pod_id, comfy_url), or None when every candidate was unavailable —
    which is a normal outcome, not an error. A resume is pinned to one physical
    machine, so a list of five stopped pods is five specific machines rather
    than five draws from the pool; all five being busy is entirely possible.

    Raises Fatal for key/account problems, where trying the rest is pointless.
    """
    log = log or (lambda _m: None)
    session = _session(key)

    all_pods = list_pods(key)
    pods = {p.get("id"): p for p in all_pods}

    # No saved order yet (first run) — try everything the account has, running
    # pods first so an already-warm one is found without starting anything.
    if not pod_ids:
        pod_ids = [p["id"] for p in sorted(
            all_pods, key=lambda p: 0 if p.get("status") == "RUNNING" else 1) if p.get("id")]

    # Already running and healthy? Use it. Only ever one pod at a time.
    for pod_id in pod_ids:
        pod = pods.get(pod_id)
        if pod and is_healthy(pod):
            log(f"{describe(pod)} is already running")
            return pod_id, wait_comfy(pod_id, log=log, should_cancel=should_cancel)

    avail = gpu_availability(key) if use_availability else {}
    misses: list[str] = misses_out if misses_out is not None else []
    total = len(pod_ids)

    for n, pod_id in enumerate(pod_ids, 1):
        if should_cancel and should_cancel():
            return None

        pod = pods.get(pod_id)
        if pod is None:
            misses.append(f"{pod_id}: not on this account")
            continue

        # Advisory only, and only ever used to skip — never to bless. A resume
        # reclaims one specific machine rather than drawing from the pool, so
        # an empty datacenter does NOT imply this pod can't start: only an
        # explicit NONE is worth skipping, and even that is a guess.
        info = avail.get((pod.get("gpu") or {}).get("id"), {})
        dc_state = info.get("dc", {}).get(pod.get("dataCenterId"))
        if dc_state == "NONE" or info.get("overall") == "NONE":
            log(f"[{n}/{total}] skipping {describe(pod)} — datacenter reports none free")
            misses.append(f"{pod_id}: datacenter reports none free")
            continue

        log(f"[{n}/{total}] trying {describe(pod)}")
        try:
            start_pod(pod_id, session=session)
            wait_running(pod_id, session, log=log, should_cancel=should_cancel)
            try:
                url = wait_comfy(pod_id, log=log, should_cancel=should_cancel)
            except Unavailable:
                # The pod is up with a GPU but ComfyUI never answered. Moving on
                # without stopping it would leave it billing unnoticed.
                log(f"  stopping {pod_id} — it is running but ComfyUI never came up")
                stop_pod(pod_id, session=session)
                raise
            log(f"{pod_id} is up at {url}")
            return pod_id, url
        except Unavailable as e:
            log(f"[{n}/{total}] {pod_id} unavailable: {e}")
            misses.append(f"{pod_id}: {e}")
            if n < total:
                time.sleep(CANDIDATE_DELAY)
        # Fatal deliberately not caught — it aborts the whole chain, and after
        # the reclassification in start_pod only auth and rate limits do that.

    log("no pod could be started:")
    for m in misses:
        log(f"  {m}")
    return None


# ---------------------------------------------------------------------- #
# Terminal harness — check pod behaviour without launching the app
# ---------------------------------------------------------------------- #

def _main(argv: list[str]) -> int:
    usage = (
        "usage:\n"
        "  python runpod_api.py test                 check RunPod is up and the key works\n"
        "  python runpod_api.py list                 show every pod on the account\n"
        "  python runpod_api.py status <pod-id>      one pod, with its health verdict\n"
        "  python runpod_api.py start <pod-id>       resume one pod and wait for ComfyUI\n"
        "  python runpod_api.py stop <pod-id>        stop one pod\n"
        "  python runpod_api.py wake <id> [id ...]   walk the list, first available wins\n"
    )
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage)
        return 0
    if not have_key():
        print(f"No API key — checked ${API_KEY_ENV} and {app_dir() / KEY_FILE_NAME}")
        return 2

    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "test":
            ok, msg = test_connection()
            print(("OK    " if ok else "FAIL  ") + msg)
            return 0 if ok else 1
        if cmd == "list":
            for p in list_pods():
                flag = "healthy" if is_healthy(p) else ""
                print(f"{p.get('id','?'):16} {describe(p)}  {flag}")
        elif cmd == "status" and args:
            pod = get_pod(args[0])
            print(describe(pod))
            print(f"healthy: {is_healthy(pod)}")
            print(f"proxy:   {proxy_url(args[0])}")
            if is_healthy(pod):
                print(f"uptime:  {format_duration(uptime_seconds(pod))}")
                print(f"rate:    ${hourly_cost(pod):.2f}/hr")
                print(f"spent:   ${spend_so_far(pod):.2f} (compute only)")
                if len(args) > 1:
                    limit = float(args[1])
                    left = projected_runtime(pod, limit)
                    print(f"limit:   ${limit:.2f} -> {limit_state(pod, limit)}, "
                          f"{format_duration(left)} of GPU time left")
        elif cmd == "start" and args:
            s = _session()
            start_pod(args[0], session=s)
            wait_running(args[0], s, log=print)
            print(wait_comfy(args[0], log=print))
        elif cmd == "stop" and args:
            print("stopped" if stop_pod(args[0]) else "stop failed")
        elif cmd == "wake" and args:
            got = wake_first_available(args, log=print)
            print(f"\n=> {got[0]} at {got[1]}" if got else "\n=> none available")
        else:
            print(usage)
            return 1
    except RunPodError as e:
        print(f"{type(e).__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
