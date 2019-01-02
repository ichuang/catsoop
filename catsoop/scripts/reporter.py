# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import json
import time
import logging
import asyncio
import datetime
import threading

from collections import defaultdict

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CATSOOP_LOC not in sys.path:
    sys.path.append(CATSOOP_LOC)

from catsoop.cslog import unprep
import catsoop.base_context as base_context
import websockets

DEBUG = False

CHECKER_DB_LOC = os.path.join(base_context.cs_data_root, "__LOGS__", "_checker")
RUNNING = os.path.join(CHECKER_DB_LOC, "running")
QUEUED = os.path.join(CHECKER_DB_LOC, "queued")
RESULTS = os.path.join(CHECKER_DB_LOC, "results")

CURRENT = {"queued": [], "running": set()}

PORTNUM = base_context.cs_checker_server_port

LOGGER = logging.getLogger("cs")
WSLOGGER = logging.getLogger("websockets.server")
WSLOGGER.setLevel(LOGGER.level)
WSLOGGER.addHandler(logging.StreamHandler())


def log(msg):
    dt = datetime.datetime.now()
    omsg = "[reporter:%s]: %s" % (dt, msg)
    LOGGER.info(omsg)


def get_status(magic):
    try:
        s = CURRENT["queued"].index(magic) + 1
    except:
        if magic in CURRENT["running"]:
            s = "running"
        elif os.path.isfile(os.path.join(RESULTS, magic[0], magic[1], magic)):
            s = "results"
        else:
            return
    return s


async def reporter(websocket, path):
    DEBUG = True
    if DEBUG:
        LOGGER.error("Waiting for websocket recv")
    magic_json = await websocket.recv()
    magic = json.loads(magic_json)["magic"]
    if DEBUG:
        log("Got message magic=%s, json=%s" % (magic, magic_json))

    last_ping = time.time()
    last_status = None
    while True:
        if DEBUG:
            log("In main loop")
        t = time.time()

        # if it's been more than 10 seconds since we've pinged, ping again.
        if t - last_ping > 10:
            try:
                await asyncio.wait_for(websocket.ping(), timeout=10)
                last_ping = time.time()
            except asyncio.TimeoutError:
                # no response from ping in 10 seconds.  quit.
                break

        # get our current status
        status = None
        try:
            status = CURRENT["queued"].index(magic) + 1
        except:
            if magic in CURRENT["running"]:
                status = "running"
            elif os.path.isfile(os.path.join(RESULTS, magic[0], magic[1], magic)):
                status = "results"

        # if our status hasn't changed, or if we don't know yet, don't send
        # anything; just keep waiting.
        if status is None or status == last_status:
            await asyncio.sleep(0.3)
            continue

        # otherwise, we should send a message.
        if isinstance(status, int):
            msg = {"type": "inqueue", "position": status}
        elif status == "running":
            try:
                start = os.stat(os.path.join(RUNNING, magic)).st_ctime
            except:
                start = time.time()
            msg = {"type": "running", "started": start, "now": time.time()}
        elif status == "results":
            try:
                with open(os.path.join(RESULTS, magic[0], magic[1], magic), "rb") as f:
                    m = unprep(f.read())
            except:
                return
            sb = m.get("score_box", "?")
            r = m.get("response", "?")
            msg = {"type": "newresult", "score_box": sb, "response": r}
        else:
            msg = None

        if msg is not None:
            await websocket.send(json.dumps(msg))
        if status == "results":
            break

        last_status = status

        await asyncio.sleep(0.3)


def updater():
    CURRENT["queued"] = [i.split("_")[1] for i in sorted(os.listdir(QUEUED))]
    CURRENT["running"] = {i.name for i in os.scandir(RUNNING)}
    crun = CURRENT["running"]
    if DEBUG and crun:
        log("updater queued=%s" % crun)
    loop.call_later(0.3, updater)


log("Starting reporter on port=%s" % PORTNUM)

start_server = websockets.serve(reporter, "0.0.0.0", PORTNUM)
loop = asyncio.get_event_loop()
log("Running start_server")
loop.run_until_complete(start_server)
loop.call_soon(updater)
loop.run_forever()
log("Reporter exiting")
