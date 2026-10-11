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
        self.assertEqual(s["week"], [False, False, False, True, True, True, False])
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

        lagos = post("/api/blade", {"lat": 6.5, "lon": 3.4, "minutes": 20})
        self.assertEqual(lagos["context"], "Tropical")
        out = post("/api/blade", {"lat": 40.7, "lon": -74, "minutes": 20, "interests": ["birds"]})
        self.assertEqual(out["source"], "fallback")
        post("/api/complete", out["blade"])
        st = json.load(urllib.request.urlopen(url + "/api/stats"))
        self.assertTrue(st["done_today"])
        with self.assertRaises(urllib.error.HTTPError) as cm:
            post("/api/blade", {"nope": 1})
        self.assertEqual(cm.exception.code, 400)


if __name__ == "__main__":
    unittest.main()


class SpeechTests(unittest.TestCase):
    BLADE = {"movement": "Walk fifteen minutes.", "observations": ["Find three birds."],
             "closing": "Phone away."}

    def test_script_order(self):
        from blade import speech
        self.assertEqual(speech.script(self.BLADE),
                         "Move. Walk fifteen minutes. Notice. Find three birds. Phone away.")

    def test_disabled_without_key(self):
        from blade import speech
        os.environ.pop("ELEVENLABS_API_KEY", None)
        self.assertFalse(speech.enabled())
        with self.assertRaises(speech.SpeechUnavailable):
            speech.synthesize(self.BLADE)

    def test_synthesize_sends_key_and_text(self):
        from blade import speech
        seen = {}

        class Fake(BaseHTTPRequestHandler):
            def do_POST(self):
                seen["key"] = self.headers["xi-api-key"]
                seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200)
                self.send_header("Content-Length", "3")
                self.end_headers()
                self.wfile.write(b"mp3")

            def log_message(self, *a):
                pass

        srv, url = serve(Fake)
        os.environ["ELEVENLABS_API_KEY"] = "test-key"
        try:
            self.assertEqual(speech.synthesize(self.BLADE, base=url), b"mp3")
        finally:
            del os.environ["ELEVENLABS_API_KEY"]
        self.assertEqual(seen["key"], "test-key")
        self.assertEqual(seen["body"]["text"], speech.script(self.BLADE))
        self.assertNotIn("lat", json.dumps(seen["body"]))

    def test_web_speak_503_without_key(self):
        os.environ.pop("ELEVENLABS_API_KEY", None)
        srv, url = serve(make_handler("m", "http://127.0.0.1:9", False))
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(urllib.request.Request(url + "/api/speak", json.dumps(self.BLADE).encode()))
        self.assertEqual(cm.exception.code, 503)


class ReasonTests(unittest.TestCase):
    def test_reports_why_it_fell_back(self):
        reasons = []
        make_blade(facts(), url="http://127.0.0.1:9", on_error=reasons.append)
        self.assertEqual(len(reasons), 1)
        self.assertIn("model unavailable", reasons[0])

    def test_reports_bad_shape(self):
        class Bad(FakeOllama):
            reply = {"movement": "x"}
        srv, url = serve(Bad)
        reasons = []
        make_blade(facts(), url=url, on_error=reasons.append)
        self.assertIn("not in the expected shape", reasons[0])


class SlowModelTests(unittest.TestCase):
    def test_slow_model_times_out_to_fallback_with_reason(self):
        import time

        class Slow(FakeOllama):
            def do_POST(self):
                time.sleep(2)
                super().do_POST()

        srv, url = serve(Slow)
        reasons = []
        t0 = time.time()
        _, src = make_blade(facts(), url=url, timeout=1, on_error=reasons.append)
        self.assertEqual(src, "fallback")
        self.assertLess(time.time() - t0, 2)
        self.assertIn("timed out", reasons[0])


class PlaceTests(unittest.TestCase):
    def test_bands_and_tropics(self):
        from blade.place import climate_band
        self.assertEqual([climate_band(x) for x in (6.5, 30, 45, 60, 75)],
                         ["tropical", "subtropical", "temperate", "boreal", "polar"])
        from blade.facts import season_for
        self.assertEqual(season_for(date(2026, 10, 11), 6.5), "tropical")  # Lagos: no autumn

    def test_autumn_temperate_notes_and_facts(self):
        f = facts()
        self.assertEqual(f.climate, "temperate")
        self.assertIn("leaves turning", " ".join(f.place_notes))
        self.assertIn("Typical here", "\n".join(f.lines()))

    def test_tropics_keep_flowers_and_drop_leaf_colour(self):
        f = build_facts(NOW, 6.5, 3.4, 30)
        ids = set()
        for seed in range(80):
            _, obs = candidates(f, [], n=40, rng=random.Random(seed))
            ids |= {o["id"] for o in obs}
        self.assertIn("flowers3", ids)
        self.assertNotIn("leafcolor", ids)
        self.assertNotIn("frost", ids)


class LiveFake(BaseHTTPRequestHandler):
    hits = []

    def do_GET(self):
        LiveFake.hits.append(self.path)
        if "/forecast" in self.path:
            body = {"current": {"temperature_2m": 11.6, "weather_code": 61}}
        elif "/reverse" in self.path:
            body = {"address": {"suburb": "Riverside", "city": "Springfield"}}
        else:
            t = lambda n, c, g: {"taxon": {"name": n, "preferred_common_name": c, "iconic_taxon_name": g}}
            body = {"results": [t("Cardinalis cardinalis", "Northern Cardinal", "Aves"),
                                t("Quercus rubra", "Northern Red Oak", "Plantae"),
                                t("Foo bar", None, "Aves"),
                                t("Baz", "Mystery", "Protozoa")]}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class LiveTests(unittest.TestCase):
    def setUp(self):
        from blade import live
        os.environ["BLADE_HOME"] = tempfile.mkdtemp()
        LiveFake.hits.clear()
        self.live = live
        srv, url = serve(LiveFake)
        self.saved = dict(live.URLS)
        live.URLS.update(weather=url + "/forecast", place=url + "/reverse", species=url + "/species")
        self.addCleanup(lambda: live.URLS.update(self.saved))

    def test_gather_parses_and_sends_only_rounded_coords(self):
        out = self.live.gather(40.712776, -74.005974)
        self.assertEqual(out["weather"], "light rain, 12C")
        self.assertEqual(out["place"], "Riverside")
        self.assertEqual([s["common"] for s in out["sightings"]], ["Northern Cardinal", "Northern Red Oak"])
        joined = " ".join(LiveFake.hits)
        self.assertIn("40.71", joined)
        self.assertNotIn("40.7127", joined)
        self.assertNotIn("74.0059", joined)

    def test_cache_serves_when_network_dies(self):
        self.live.gather(40.71, -74.0)
        self.live.URLS.update(weather="http://127.0.0.1:9", place="http://127.0.0.1:9", species="http://127.0.0.1:9")
        # cache is fresh, so no network needed; force-stale it and confirm stale data still beats nothing
        import json as j, pathlib
        p = self.live._cache_path()
        c = j.loads(p.read_text())
        for v in c.values():
            v["t"] = 0
        p.write_text(j.dumps(c))
        out = self.live.gather(40.71, -74.0)
        self.assertEqual(out["place"], "Riverside")

    def test_no_network_no_cache_is_empty_not_an_error(self):
        self.live.URLS.update(weather="http://127.0.0.1:9", place="http://127.0.0.1:9", species="http://127.0.0.1:9")
        out = self.live.gather(1.0, 2.0)
        self.assertEqual(out, {"weather": None, "place": None, "sightings": []})

    def test_sightings_become_local_tasks_and_reach_the_prompt(self):
        data = self.live.gather(40.71, -74.0)
        f = build_facts(NOW, 40.71, -74.0, 20, live=data)
        self.assertIn("Northern Cardinal", "\n".join(f.lines()))
        _, obs = candidates(f, ["birds"], rng=random.Random(3))
        texts = " ".join(o["text"] for o in obs[:2])
        self.assertIn("Northern Cardinal", texts)
        self.assertIn("rain", f.weather)

    def test_web_live_is_opt_in(self):
        os.environ["BLADE_HOME"] = tempfile.mkdtemp()
        srv, url = serve(make_handler("m", "http://127.0.0.1:9", False))

        def post(obj):
            return json.load(urllib.request.urlopen(
                urllib.request.Request(url + "/api/blade", json.dumps(obj).encode())))

        base = {"lat": 40.71, "lon": -74.0, "minutes": 20}
        LiveFake.hits.clear()
        off = post(base)
        self.assertEqual((off["live"], LiveFake.hits), ("off", []))
        on = post({**base, "live": True})
        self.assertEqual(on["live"], "on")
        self.assertIn("Riverside", on["context"])


class FakeText(BaseHTTPRequestHandler):
    reply = "Three birds today! The world is loud if you listen. You stayed out a while. More text here."
    seen = []

    def do_POST(self):
        FakeText.seen.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        body = json.dumps({"response": FakeText.reply}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class ReflectTests(unittest.TestCase):
    def setUp(self):
        os.environ["BLADE_HOME"] = tempfile.mkdtemp()
        FakeText.seen.clear()
        FakeText.reply = "Three birds today! The world is loud if you listen. You stayed out a while. More text here."

    def test_model_reply_is_trimmed_calm_and_grounded(self):
        from blade.reflect import reflect
        srv, url = serve(FakeText)
        blade = {"movement": "Walk to the park.", "observations": ["See three birds."]}
        reply, src = reflect("dove, pelican, mango tree", blade, url=url)
        self.assertEqual(src, "model")
        self.assertEqual(reply, "Three birds today. The world is loud if you listen.")
        sent = FakeText.seen[0]
        self.assertIn("dove, pelican, mango tree", sent["prompt"])
        self.assertIn("Walk to the park.", sent["prompt"])
        self.assertIn("Never invent", sent["system"])
        self.assertLessEqual(sent["options"]["num_predict"], 100)

    def test_questions_and_junk_fall_back(self):
        from blade.reflect import reflect
        FakeText.reply = "Did you enjoy it? What a day?"
        srv, url = serve(FakeText)
        reasons = []
        reply, src = reflect("a dove", url=url, on_error=reasons.append)
        self.assertEqual(src, "fallback")
        self.assertIn("not usable", reasons[0])
        self.assertEqual(reply, "Noticed today: a dove. The day is different now.")

    def test_no_server_and_no_llm_fall_back(self):
        from blade.reflect import reflect, fallback_reply
        self.assertEqual(reflect("a dove", url="http://127.0.0.1:9")[1], "fallback")
        self.assertEqual(reflect("a dove", use_llm=False)[1], "fallback")
        self.assertEqual(fallback_reply("dove, pelican and a mango tree"),
                         "Noticed today: dove, pelican, a mango tree. The day is different now.")
        self.assertEqual(fallback_reply("   "), "You went outside. That is enough.")

    def test_note_is_capped(self):
        from blade.reflect import clean_note
        self.assertEqual(len(clean_note("x" * 1000)), 300)

    def test_annotation_does_not_count_as_a_day(self):
        log.annotate("a dove", "reply")
        self.assertEqual(log.stats()["total"], 0)
        log.record({})
        log.annotate("a dove", "reply")
        self.assertEqual(log.stats()["total"], 1)

    def test_web_reflect(self):
        srv, url = serve(FakeText)
        web, wurl = serve(make_handler("m", url, True))

        def post(obj):
            return urllib.request.urlopen(urllib.request.Request(wurl + "/api/reflect", json.dumps(obj).encode()))

        out = json.load(post({"note": "dove, pelican, mango tree"}))
        self.assertEqual((out["source"], out["reply"]),
                         ("model", "Three birds today. The world is loud if you listen."))
        with self.assertRaises(urllib.error.HTTPError) as cm:
            post({"note": "   "})
        self.assertEqual(cm.exception.code, 400)
        saved = [json.loads(l) for l in log._path().read_text().splitlines()]
        self.assertEqual(saved[0]["note"], "dove, pelican, mango tree")

    def test_cli_done_with_note(self):
        import contextlib, io
        from blade.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["--no-llm", "done", "--note", "a dove, a pelican"])
        self.assertIn("Blade complete", buf.getvalue())
        self.assertIn("Noticed today: a dove, a pelican.", buf.getvalue())


class WeatherTaskTests(unittest.TestCase):
    def ids(self, f, runs=150):
        out = set()
        for seed in range(runs):
            _, obs = candidates(f, [], n=60, rng=random.Random(seed))
            out |= {o["id"] for o in obs}
        return out

    def test_no_rain_task_unless_weather_says_rain(self):
        self.assertNotIn("rainleaf", self.ids(build_facts(NOW, 6.5, 3.4, 30)))               # unknown (Lagos, offline)
        self.assertNotIn("rainleaf", self.ids(build_facts(NOW, 6.5, 3.4, 30, "clear, 31C")))
        self.assertNotIn("rainleaf", self.ids(build_facts(NOW, 40.7, -74, 30, "light snow, -2C")))
        self.assertIn("rainleaf", self.ids(build_facts(NOW, 6.5, 3.4, 30, "light rain, 24C")))

    def test_rain_task_leads_when_wet(self):
        _, obs = candidates(build_facts(NOW, 40.7, -74, 30, "rain, 9C"), [], rng=random.Random(5))
        self.assertEqual(obs[0]["id"], "rainleaf")

    def test_no_frost_outside_cold_climates(self):
        winter = datetime(2026, 1, 15, 15, tzinfo=timezone.utc)
        self.assertNotIn("frost", self.ids(build_facts(winter, 28.5, -81.4, 30)))  # Florida
        self.assertIn("frost", self.ids(build_facts(winter, 45.0, -75.0, 30)))     # temperate
