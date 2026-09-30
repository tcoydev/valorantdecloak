import threading
import time

import requests

# K/D ve HS% hesabına katılan son competitive maç sayısı.
RECENT_MATCH_COUNT = 5

# Riot pd sunucusuna aynı anda atılacak maç detayı istekleri. 10 oyuncu kendi
# thread'inde çalıştığı için toplam eşzamanlılığı burada sınırlıyoruz (429 önler).
DETAIL_SEMAPHORE = threading.BoundedSemaphore(4)
PD_MAX_ATTEMPTS = 3

# Maç detayı özet önbelleği bu sayıyı aşarsa temizlenir (bellek sınırı).
MATCH_CACHE_LIMIT = 300


class PlayerStats:
    """Oyuncunun son RECENT_MATCH_COUNT competitive maçından K/D ve HS% hesaplar.

    Veri tamamen Riot'un kendi pd API'sinden gelir (match-history + match-details),
    yani Cloudflare/tracker.gg ya da gizli isim çözümüne bağımlı değildir.
    Kill/death ve isabet dağılımı sadece match-details içinde olduğundan maç
    başına bir indirme gerekir; o yüzden maç sayısı küçük tutulur."""

    # Son 5 maç ancak oyuncu yeni bir competitive maç bitirince değişir.
    STATS_TTL = 15 * 60
    EMPTY_TTL = 10 * 60  # hiç competitive maçı yok
    FAIL_TTL = 60        # Riot hatası: kısa süre sonra tekrar dene

    def __init__(self, Requests, log):
        self.Requests = Requests
        self.log = log
        self._cache_lock = threading.Lock()
        self.stats_cache = {}   # puuid -> (result, expires_at)
        self._match_cache = {}  # match_id -> {puuid: [kills, deaths, headshots, shots]}

    def _default_stats(self):
        return {
            "kd": "N/A",
            "hs": "N/A",
            "RankedRatingEarned": "N/A",
            "AFKPenalty": "N/A",
            "peakRR": None,
        }

    def _unavailable_stats(self):
        # Riot'tan veri alınamadı (hata/zaman aşımı).
        stats = self._default_stats()
        stats.update({"matchesCounted": 0, "source": "error"})
        return stats

    def _no_matches_stats(self):
        # Hata yok ama oyuncunun hiç competitive maçı yok.
        stats = self._default_stats()
        stats.update({"kd": "-", "hs": "-", "matchesCounted": 0, "source": "riot"})
        return stats

    def pending_stats(self):
        """Verisi henüz gelmemiş oyuncu için yer tutucu. kd/hs/peakRR None kalır
        (panel bu chip'leri boş bırakır), değer gelince panele yazılır."""
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
        """Ağa çıkmayan önbellek okuması: taze sonuç varsa döner, yoksa None."""
        cached = self.stats_cache.get(puuid)
        if cached and time.time() < cached[1]:
            return cached[0]
        return None

    def get_stats(self, puuid):
        cached = self.peek_stats(puuid)
        if cached is not None:
            return cached

        result = self._riot_recent_stats(puuid)
        if result is None:
            result, ttl = self._unavailable_stats(), self.FAIL_TTL
        elif result.get("matchesCounted", 0) == 0:
            ttl = self.EMPTY_TTL
        else:
            ttl = self.STATS_TTL

        with self._cache_lock:
            self.stats_cache[puuid] = (result, time.time() + ttl)
        return result

    # --- Riot pd API ---

    def _pd_get(self, endpoint):
        """pd endpoint'ine GET atar. Requests.fetch'in aksine hata durumunda sonsuz
        yeniden deneme yapmaz: süresi dolmuş token'da bir kez yeniler, 429'da kısa
        bekleyip birkaç kez dener, aksi halde None döner."""
        for attempt in range(PD_MAX_ATTEMPTS):
            try:
                r = requests.get(
                    self.Requests.pd_url + endpoint,
                    headers=self.Requests.get_headers(),
                    verify=False,
                    timeout=15,
                )
            except requests.exceptions.RequestException as e:
                self.log(f"riot pd istegi basarisiz ({endpoint}): {e}")
                return None
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            if r.status_code in (400, 401, 403) and attempt == 0:
                try:
                    self.Requests.get_headers(refresh=True)
                except Exception as e:
                    self.log(f"token yenilenemedi: {e}")
                    return None
                continue
            if r.status_code != 404:
                self.log(f"riot pd istegi hata kodu {r.status_code}: {endpoint}")
            return None
        return None

    def _recent_match_ids(self, puuid):
        """Oyuncunun son competitive maç ID'leri (en yeni başta); Riot'tan yanıt
        alınamazsa None. Kuyruk filtresini Riot uygular, yine de kontrol ederiz."""
        r = self._pd_get(
            f"/match-history/v1/history/{puuid}"
            f"?startIndex=0&endIndex={RECENT_MATCH_COUNT}&queue=competitive"
        )
        if r is None:
            return None
        try:
            history = r.json().get("History") or []
        except ValueError:
            return None
        return [
            h["MatchID"]
            for h in history
            if h.get("MatchID") and h.get("QueueID", "competitive") == "competitive"
        ][:RECENT_MATCH_COUNT]

    def _match_summary(self, match_id):
        """Bir maçtaki herkes için {puuid: [kills, deaths, headshots, shots]}.
        Sonuç maç ID'sine göre önbelleğe alınır; aynı maçtaki oyuncular paylaşır."""
        with self._cache_lock:
            cached = self._match_cache.get(match_id)
        if cached is not None:
            return cached

        with DETAIL_SEMAPHORE:
            r = self._pd_get(f"/match-details/v1/matches/{match_id}")
        if r is None:
            return None
        try:
            data = r.json()
        except ValueError:
            return None

        summary = {}
        for player in data.get("players") or []:
            subject = player.get("subject")
            stats = player.get("stats") or {}
            if subject:
                summary[subject] = [stats.get("kills", 0), stats.get("deaths", 0), 0, 0]
        for rnd in data.get("roundResults") or []:
            for ps in rnd.get("playerStats") or []:
                entry = summary.get(ps.get("subject"))
                if entry is None:
                    continue
                for dmg in ps.get("damage") or []:
                    head = dmg.get("headshots", 0)
                    entry[2] += head
                    entry[3] += head + dmg.get("bodyshots", 0) + dmg.get("legshots", 0)

        with self._cache_lock:
            if len(self._match_cache) >= MATCH_CACHE_LIMIT:
                self._match_cache.clear()
            self._match_cache[match_id] = summary
        return summary

    def _riot_recent_stats(self, puuid):
        """Son competitive maçların toplam K/D ve HS%'si. Riot'tan hiç veri alınamazsa None."""
        match_ids = self._recent_match_ids(puuid)
        if match_ids is None:
            return None
        if not match_ids:
            return self._no_matches_stats()

        kills = deaths = head = shots = counted = 0
        for match_id in match_ids:
            entry = (self._match_summary(match_id) or {}).get(puuid)
            if entry is None:
                continue  # detay alınamadı ya da oyuncu bu maçta yok
            counted += 1
            kills += entry[0]
            deaths += entry[1]
            head += entry[2]
            shots += entry[3]

        if counted == 0:
            return None  # maçlar var ama hiçbir detay alınamadı: hata say

        stats = self._default_stats()
        stats.update(
            {
                "kd": round(kills / max(deaths, 1), 2),
                "hs": round(head / shots * 100) if shots else "N/A",
                "matchesCounted": counted,
                "source": "riot",
            }
        )
        return stats


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

    player_stats = PlayerStats(Requests, log)
    print(player_stats.get_stats(Requests.puuid))
