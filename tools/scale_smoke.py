"""Week 0 스케일 스모크 테스트: CSE에 AE N개 등록 + 각 AE에 CNT/CIN 쓰기 시간 측정.
사용: python tools/scale_smoke.py --n 1000 --workers 20 [--base http://localhost:8080/cse-in]
가정: ACME 기본 설정(포트 8080, cseName cse-in, admin originator CAdmin). 다르면 인자로 조정.
미검증 스크립트: Docker CSE 기동 후 --n 10으로 먼저 확인할 것.
"""
import argparse, json, statistics, time, uuid
from concurrent.futures import ThreadPoolExecutor
import requests

def hdr(origin, ty=None):
    h = {"X-M2M-Origin": origin, "X-M2M-RI": uuid.uuid4().hex, "X-M2M-RVI": "3",
         "Accept": "application/json"}
    h["Content-Type"] = "application/json" + (f";ty={ty}" if ty else "")
    return h

def one(args, i):
    s = requests.Session()
    t = {}
    rn = f"panel{i}"
    t0 = time.perf_counter()
    r = s.post(args.base, headers=hdr(args.admin, 2),
               data=json.dumps({"m2m:ae": {"rn": rn, "api": "Npolagrid", "rr": False, "srv": ["3"]}}))
    t["ae"] = time.perf_counter() - t0
    if r.status_code != 201:
        return None, f"AE {r.status_code} {r.text[:120]}"
    orig = r.json()["m2m:ae"]["aei"]
    t0 = time.perf_counter()
    r = s.post(f"{args.base}/{rn}", headers=hdr(orig, 3),
               data=json.dumps({"m2m:cnt": {"rn": "angle"}}))
    t["cnt"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    r2 = s.post(f"{args.base}/{rn}/angle", headers=hdr(orig, 4),
                data=json.dumps({"m2m:cin": {"con": "45"}}))
    t["cin"] = time.perf_counter() - t0
    if r.status_code != 201 or r2.status_code != 201:
        return None, f"CNT/CIN {r.status_code}/{r2.status_code}"
    return t, None

def pct(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(len(v) * p))]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--base", default="http://localhost:8080/cse-in")
    ap.add_argument("--admin", default="CAdmin")
    a = ap.parse_args()
    t0 = time.perf_counter()
    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(lambda i: one(a, i), range(a.n)))
    wall = time.perf_counter() - t0
    ok = [r for r, e in res if r]; errs = [e for r, e in res if e]
    print(f"N={a.n} ok={len(ok)} fail={len(errs)} wall={wall:.1f}s "
          f"throughput={3 * len(ok) / wall:.0f} req/s")
    for k in ("ae", "cnt", "cin"):
        v = [r[k] * 1000 for r in ok]
        if v:
            print(f"  {k}: p50={statistics.median(v):.0f}ms p95={pct(v, .95):.0f}ms max={max(v):.0f}ms")
    for e in errs[:5]: print("  ERR", e)
