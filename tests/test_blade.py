import json
import os
import random
import tempfile
import threading
import unittest
import urllib.request
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from blade import log
from blade.facts import build_facts
from blade.generate import make_blade
from blade.quests import MOVEMENT, OBSERVATION, candidates
from blade.web import make_handler

NOW = datetime(2026, 10, 11, 15, 0, tzinfo=timezone.utc)


def facts(minutes=20, interests=None):
    return build_facts(NOW, 40.7, -74.0, minutes, "clear", interests or [])


class FakeOllama(BaseHTTPRequestHandler):
    reply = {"movement": "Walk fifteen minutes. No destination.",
             "observations": ["Find a leaf changing colour."], "closing": "Phone away."}

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        body = json.dumps({"response": json.dumps(self.reply)}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def serve(handler):
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


class QuestTests(unittest.TestCase):
    def test_no_fishing_and_sunflower_present(self):
        text = " ".join(q["text"].lower() for q in MOVEMENT + OBSERVATION)
        self.assertNotIn("fish", text)
        self.assertIn("sunflower", text)

    def test_respects_time_and_season(self):
        for seed in range(40):
            m, obs = candidates(facts(10), rng=random.Random(seed))
            self.assertLessEqual(m["min"], 10)
            ids = [o["id"] for o in obs]
            self.assertNotIn("newgrowth", ids)  # spring/summer only; facts() is autumn

    def test_water_quests_only_with_water_walk(self):
        for seed in range(60):
            m, obs = candidates(facts(30, ["water"]), ["water"], rng=random.Random(seed))
            if m["id"] != "water":
                self.assertFalse([o for o in obs if o["tag"] == "water"])

    def test_interest_preferred(self):
        _, obs = candidates(facts(), ["birds"], n=3, rng=random.Random(1))
        self.assertTrue(all(o["tag"] == "birds" for o in obs))


class GenerateTests(unittest.TestCase):
    def test_model_path(self):
        srv, url = serve(FakeOllama)
        blade, src = make_blade(facts(), url=url)
        self.assertEqual(src, "model")
        self.assertEqual(blade["closing"], "Phone away.")

    def test_bad_model_output_falls_back(self):
        class Bad(FakeOllama):
            reply = {"movement": "x"}
        srv, url = serve(Bad)
        _, src = make_blade(facts(), url=url)
        self.assertEqual(src, "fallback")

    def test_no_server_falls_back(self):
        blade, src = make_blade(facts(), url="http://127.0.0.1:9")
        self.assertEqual(src, "fallback")
        self.assertTrue(1 <= len(blade["observations"]) <= 3)


class LogTests(unittest.TestCase):
    def setUp(self):
        os.environ["BLADE_HOME"] = tempfile.mkdtemp()

    def test_empty_state(self):
        self.assertEqual(log.message(log.stats()), "The grass is waiting.")

    def test_streak_and_missed_day_copy(self):
        today = date(2026, 10, 11)
        for d in (1, 2, 3):
            log.record({}, today - timedelta(days=d))
        s = log.stats(today)
        self.assertEqual(s["streak"], 3)
        self.assertEqual(log.message(s), "Blade streak: 3 days")
        s = log.stats(today + timedelta(days=2))
        self.assertEqual(s["streak"], 0)
        self.assertIn("No streak pressure", log.message(s))

    def test_completion_message(self):
        log.record({}, date.today())
        self.assertEqual(log.message(log.stats()), "Blade complete. The day is different now.")


class WebTests(unittest.TestCase):
    def test_endpoints(self):
        os.environ["BLADE_HOME"] = tempfile.mkdtemp()
        srv, url = serve(make_handler("m", "http://127.0.0.1:9", True))

        def post(path, obj):
            r = urllib.request.Request(url + path, json.dumps(obj).encode())
            return json.load(urllib.request.urlopen(r))

        out = post("/api/blade", {"lat": 40.7, "lon": -74, "minutes": 20, "interest": "birds"})
        self.assertEqual(out["source"], "fallback")
        post("/api/complete", out["blade"])
        st = json.load(urllib.request.urlopen(url + "/api/stats"))
        self.assertTrue(st["done_today"])
        with self.assertRaises(urllib.error.HTTPError) as cm:
            post("/api/blade", {"nope": 1})
        self.assertEqual(cm.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
