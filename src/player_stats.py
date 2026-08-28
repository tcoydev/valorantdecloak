import json
import os
import random
import threading
import time
from urllib.parse import quote

# tracker.gg, düz `requests` çağrılarını Cloudflare ile bloklar (HTTP 403
# "You've Been Blocked"). API'nin isteği kabul etmesi için gerçek bir Chrome
# TLS/HTTP parmak izini taklit eden bir istemci gerekir. Tercih sırası:
#   1. primp     — tek Rust wheel, cffi/libcurl derlemesi yok
#   2. curl_cffi — eski yöntem, hâlâ fallback
#   3. requests  — impersonation yok; büyük ihtimalle 403 yer (son çare)
# `_tracker_get(url, headers, timeout)` bu üçünden hangisi varsa onu kullanır;
# yanıt nesnesi her durumda `.status_code` / `.json()` / `.text` sağlar.
try:
    import primp

    # ÖNEMLİ: belirli ve güncel bir Chrome sürümü verilmeli. "chrome" gibi genel
    # takma ad veya primp'te olmayan bir sürüm sessizce "random"e düşüyor ve
    # Cloudflare'a takılıyor. Tek istemci tüm thread'lerde paylaşılır (reqwest
    # tabanlı, thread-safe; cookie_store sayesinde Cloudflare çerezleri birikir).
    _PRIMP_CLIENT = primp.Client(
        impersonate="chrome_146",
        impersonate_os="windows",
        verify=True,
    )

    def _tracker_get(url, headers, timeout):
        return _PRIMP_CLIENT.get(url, headers=headers, timeout=timeout)

    TRACKER_BACKEND = "primp"
except ImportError:
    try:
        from curl_cffi import requests as _curl_requests

        def _tracker_get(url, headers, timeout):
            return _curl_requests.get(url, headers=headers, timeout=timeout, impersonate="chrome")

        TRACKER_BACKEND = "curl_cffi"
    except ImportError:
        import requests as _plain_requests

        def _tracker_get(url, headers, timeout):
            return _plain_requests.get(url, headers=headers, timeout=timeout)

        TRACKER_BACKEND = "requests"

TRACKER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://tracker.gg/",
}

# Cloudflare tolerates only a handful of concurrent requests from one IP
# before it starts blocking/rate-limiting the rest (seen as sporadic 403s
# when a full 10-player lobby is prefetched in parallel, even though the
# profiles themselves are public). Cap concurrency across all PlayerStats
# instances/threads and retry transient blocks instead of failing outright.
TRACKER_SEMAPHORE = threading.BoundedSemaphore(3)
TRACKER_MAX_RETRIES = 3


class PlayerStats:
    STATS_TTL = 3 * 24 * 60 * 60  # cache successful season stats for 3 days
    FAIL_TTL = 120   # retry tracker sooner on failure (don't lock "Gizli" long)
    CACHE_FILE = "tracker_cache.json"  # persisted so the 3 gün TTL survives restarts

    def __init__(self, Requests, log, config):
        self.Requests = Requests
        self.log = log
        self.config = config
        self.season_id = None    # set by main once the season is known
        self._cache_lock = threading.Lock()
        self.stats_cache = self._load_cache()  # puuid -> (result, expires_at)

    def clear_runtime_cache(self):
        """Kept for API compatibility; season stats are cached by TTL, not cleared here."""
        pass

    def _load_cache(self):
        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        except Exception as e:
            self.log(f"tracker cache okuma hatası: {e}")
            return {}

        now = time.time()
        cache = {}
        for puuid, entry in raw.items():
            try:
                expires = entry["expires"]
                if expires > now:
                    cache[puuid] = (entry["result"], expires)
            except (KeyError, TypeError):
                continue
        return cache

    def _save_cache(self):
        try:
            raw = {puuid: {"result": result, "expires": expires}
                   for puuid, (result, expires) in self.stats_cache.items()}
            tmp_path = self.CACHE_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(raw, f)
            os.replace(tmp_path, self.CACHE_FILE)
        except Exception as e:
            self.log(f"tracker cache yazma hatası: {e}")

    def _default_stats(self):
        return {
            "kd": "N/A",
            "hs": "N/A",
            "RankedRatingEarned": "N/A",
            "AFKPenalty": "N/A",
            "peakRR": None,
        }

    def _hidden_stats(self):
        # Shown when tracker.gg has no data / errors for this player
        return {
            "kd": "Gizli",
            "hs": "Gizli",
            "RankedRatingEarned": "N/A",
            "AFKPenalty": "N/A",
            "matchesCounted": 0,
            "peakRR": None,
            "source": "hidden",
        }

    def pending_stats(self):
        """Placeholder for a puuid whose tracker.gg fetch hasn't landed yet.
        kd/hs/peakRR stay None (not "Gizli") so the panel just renders nothing
        for those chips instead of flashing a value that then changes."""
        return {
            "kd": None,
            "hs": None,
            "RankedRatingEarned": "N/A",
            "AFKPenalty": "N/A",
            "matchesCounted": 0,
            "peakRR": None,
            "source": "pending",
        }

    def peek_stats(self, puuid):
        """Non-blocking cache read: never hits the network. Returns the cached
        result if still fresh, otherwise None so the caller can render a
        pending placeholder immediately and let a background fetch (see
        get_stats, normally driven by main.py's prefetch) fill the cache in."""
        cached = self.stats_cache.get(puuid)
        if cached and time.time() < cached[1]:
            return cached[0]
        return None

    def get_stats(self, puuid, name=None):
        # Serve from cache (in-memory or restored from disk) while not expired
        cached = self.stats_cache.get(puuid)
        if cached and time.time() < cached[1]:
            return cached[0]

        # Full-season aggregate straight from tracker.gg (one request).
        result = self._tracker_season_stats(name) if name else None
        ttl = self.STATS_TTL if result is not None else self.FAIL_TTL
        if result is None:
            result = self._hidden_stats()  # tracker error / no data => "Gizli"

        with self._cache_lock:
            self.stats_cache[puuid] = (result, time.time() + ttl)
            self._save_cache()
        return result

    def _tracker_season_stats(self, name):
        """Full current-season KD/HS from tracker.gg. Returns dict or None."""
        url = f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{quote(name)}"
        r = None
        with TRACKER_SEMAPHORE:
            for attempt in range(TRACKER_MAX_RETRIES + 1):
                try:
                    r = _tracker_get(url, TRACKER_HEADERS, 15)
                except Exception as e:
                    self.log(f"tracker.gg fetch error for {name}: {e}")
                    return None
                if r.status_code == 200:
                    break
                if r.status_code == 403:
                    # Cloudflare bot block — transient 403s can succeed after a
                    # short wait (different Cloudflare edge nodes), so retry with
                    # backoff before giving up.
                    if attempt < TRACKER_MAX_RETRIES:
                        self.log(f"tracker.gg Cloudflare 403 for {name}, retrying ({attempt+1}/{TRACKER_MAX_RETRIES})...")
                        time.sleep(2 + random.random() * 2)
                        continue
                    self.log(f"tracker.gg blocked by Cloudflare (403) for {name}")
                    return None
                if r.status_code == 451:
                    # 451 = profile is private on tracker.gg
                    self.log(f"tracker.gg profile private (451) for {name}")
                    return None
                if r.status_code in (429, 503) and attempt < TRACKER_MAX_RETRIES:
                    self.log(f"tracker.gg rate-limited (status {r.status_code}) for {name}, retrying ({attempt+1}/{TRACKER_MAX_RETRIES})...")
                    time.sleep(1.5 + random.random())
                    continue
                self.log(f"tracker.gg fetch failed (status {r.status_code}) for {name}")
                return None
        try:
            segments = r.json().get("data", {}).get("segments", [])
        except Exception as e:
            self.log(f"tracker.gg parse error for {name}: {e}")
            return None

        best = None
        comp_segments = []
        for s in segments:
            if s.get("type") != "season":
                continue
            attrs = s.get("attributes", {})
            if attrs.get("playlist") != "competitive":
                continue
            comp_segments.append(s)
            if self.season_id and attrs.get("seasonId") == self.season_id:
                best = s
                break
            if best is None:
                best = s  # most recent competitive season as fallback

        if not best:
            return None

        st = best.get("stats", {})
        kd_val = st.get("kDRatio", {}).get("value")
        hs_val = st.get("headshotsPercentage", {}).get("value")
        matches = st.get("matchesPlayed", {}).get("value")
        # No usable numbers => treat as hidden
        if not isinstance(kd_val, (int, float)) and not isinstance(hs_val, (int, float)):
            return None
        return {
            "kd": round(kd_val, 2) if isinstance(kd_val, (int, float)) else "Gizli",
            "hs": round(hs_val) if isinstance(hs_val, (int, float)) else "Gizli",
            "RankedRatingEarned": "N/A",
            "AFKPenalty": "N/A",
            "matchesCounted": int(matches) if isinstance(matches, (int, float)) else 0,
            "peakRR": self._extract_peak_rr(comp_segments),
            "source": "tracker",
        }

    def _extract_peak_rr(self, comp_segments):
        """Peak RR from tracker.gg. The competitive season segment carries a
        `peakRank` stat whose `value` is the peak rating (e.g. 348). Take the
        highest across all competitive seasons."""
        best_rr = None
        for s in comp_segments:
            peak = (s.get("stats", {}) or {}).get("peakRank")
            if not isinstance(peak, dict):
                continue
            val = peak.get("value")
            if isinstance(val, (int, float)) and (best_rr is None or val > best_rr):
                best_rr = int(val)
        return best_rr


if __name__ == "__main__":
    from constants import version
    from requestsV import Requests
    from logs import Logging
    from errors import Error
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    Logging = Logging()
    log = Logging.log
    ErrorSRC = Error(log)
    Requests = Requests(version, log, ErrorSRC)

    player_stats = PlayerStats(Requests, log, "a")
    player_stats.season_id = None
    print(player_stats.get_stats("963ad672-61e1-537e-8449-06ece1a5ceb7", "tcoy#carti"))
