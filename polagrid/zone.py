"""One zone of virtual cells on a oneM2M CSE (an MN-CSE), plus the zone controller (the MEC app).

Resource tree per zone, all under the MN:
  {run}env/sun, {run}env/desks      environment AE: sun and outdoor light, desk sensor readings
  {run}p{i}/command, /angle         one AE per cell: command CNT (SUB -> this zone), angle history
  {run}grp                          GRP of every cell's command CNT: one request commands the whole zone

A command is one CIN {"cmd": id, "angles": [per-cell angles]} fanned out by the GRP; each cell reads its own
entry. When all cells have applied a command, the desk sensor reports lux with the same cmd id, which is how
the controller learns the command took effect. The controller talks to the CSE only.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from .onem2m import Receiver
from .physics import simulate, sun_position, window_lux

ADMIN = "CAdmin"
MOVE_DEG = 1.0      # angle change that counts as a servo move
WAIT_S = 30


class Zone:
    """The plant: virtual cells and desk sensors driven by the physics model."""

    def __init__(self, client, room, run, port, noise=0.02, seed=0):
        self.c, self.room, self.run, self.noise = client, room, run, noise
        self.rng = np.random.default_rng(seed)
        self.angles = np.zeros(room.n_cells)
        self.moves = 0
        self.t, self.cloud = None, 0.0
        self._done, self._lock = {}, threading.Lock()
        self.rx = Receiver(port, self._on_command)

    def setup(self):
        c, run = self.c, self.run
        self.rx.start()
        env = f"C{run}env"
        c.post("", env, {"m2m:ae": {"rn": f"{run}env", "api": "Npolagrid", "rr": True, "srv": ["3"],
                                    "poa": [self.rx.url("env")]}}, 2)
        for cnt in ("sun", "desks"):
            c.post(f"{run}env", env, {"m2m:cnt": {"rn": cnt, "mni": 10}}, 3)

        def cell(i):
            orig, rn, nu = f"C{run}p{i}", f"{run}p{i}", self.rx.url(f"p{i}")
            c.post("", orig, {"m2m:ae": {"rn": rn, "api": "Npolagrid", "rr": True, "srv": ["3"], "poa": [nu]}}, 2)
            c.post(rn, orig, {"m2m:cnt": {"rn": "command", "mni": 10}}, 3)
            c.post(rn, orig, {"m2m:cnt": {"rn": "angle", "mni": 10}}, 3)
            c.post(f"{rn}/command", orig, {"m2m:sub": {"rn": "s", "nu": [nu], "enc": {"net": [3]}, "nct": 1}}, 23)

        n = self.room.n_cells
        with ThreadPoolExecutor(20) as ex:
            list(ex.map(cell, range(n)))
        c.post("", ADMIN, {"m2m:grp": {"rn": f"{run}grp", "mt": 3, "mnm": n,
                                       "mid": [f"{c.cse}/{run}p{i}/command" for i in range(n)]}}, 9)

    def set_environment(self, t, cloud=0.0):
        """Move the simulated clock and publish the sun reading."""
        self.t, self.cloud = t, cloud
        alt, az = sun_position(t, self.room.lat, self.room.lon)
        self.c.create(f"{self.run}env/sun", f"C{self.run}env",
                      {"t": t.isoformat(), "alt": round(alt, 2), "az": round(az, 2),
                       "outdoor": round(window_lux(self.room, t, cloud))})

    def _on_command(self, path, con):
        i = int(path[1:])
        new = float(con["angles"][i])
        if abs(new - self.angles[i]) > 0.05:         # history only records changes
            self.moves += abs(new - self.angles[i]) > MOVE_DEG
            self.angles[i] = new
            self.c.create(f"{self.run}p{i}/angle", f"C{self.run}p{i}", {"a": new})
        with self._lock:
            done = self._done.setdefault(con["cmd"], set())
            done.add(i)
            complete = len(done) == self.room.n_cells
        if complete:
            lux = simulate(self.room, self.t, self.angles, self.cloud, self.noise, self.rng)["desk_lux"]
            self.c.create(f"{self.run}env/desks", f"C{self.run}env",
                          {"cmd": con["cmd"], "lux": [round(float(v), 1) for v in lux]})


class Controller:
    """The MEC app: reads the sun, commands the cell group, reads desk lux. Uses the CSE only."""

    def __init__(self, client, run, port):
        self.c, self.run = client, run
        self.seq = 0
        self.latencies = []                          # seconds from command POST to desk reading
        self._waiting = {}
        self.rx = Receiver(port, self._on_desks)

    def setup(self):
        self.rx.start()
        self.c.post(f"{self.run}env/desks", ADMIN, {"m2m:sub": {"rn": "ctl", "nu": [self.rx.url("ctl")],
                                                                "enc": {"net": [3]}, "nct": 1}}, 23)

    def sun(self):
        return self.c.latest(f"{self.run}env/sun", ADMIN)

    def command(self, angles):
        """Send one angle table to every cell; return the desk reading taken after all cells applied it."""
        self.seq += 1
        cmd = f"{self.run}c{self.seq}"
        slot = self._waiting[cmd] = [threading.Event(), None]
        t0 = time.perf_counter()
        self.c.create(f"{self.run}grp/fopt", ADMIN, {"cmd": cmd, "angles": [round(float(a), 1) for a in angles]})
        if not slot[0].wait(WAIT_S):
            raise TimeoutError(f"no desk reading for {cmd} within {WAIT_S}s")
        self.latencies.append(time.perf_counter() - t0)
        del self._waiting[cmd]
        return {"desk_lux": np.array(slot[1])}

    def _on_desks(self, path, con):
        slot = self._waiting.get(con["cmd"])
        if slot:
            slot[1] = con["lux"]
            slot[0].set()
