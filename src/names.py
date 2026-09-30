import time

import requests

# Gizli/streamer-mode isim çözümü için Henrik API anahtarı.
HENRIK_API_KEY = ""

# config.json'daki örnek değer; gerçek bir anahtar olmadığı için "anahtar yok" sayılır.
HENRIK_KEY_PLACEHOLDER = "YOUR_APIKEY"

# Çözülemeyen gizli oyuncuların panelde görünen adı. Panel bu isimde tıklanınca
# oyuncunun puuid'ini kopyalar (web/app.js), o yüzden iki tarafta aynı olmalı.
HIDDEN_NAME = "Gizli"

# Bir puuid çözülemediğinde, bir sonraki denemeye kadar beklenecek süre (saniye).
# Henrik API free-tier anahtarları dakikada ~30 istekle sınırlı; heartbeat her
# birkaç saniyede bir çalıştığından, başarısız denemeleri hiç bekletmeden her
# tick'te tekrar denemek limiti hızla doldurup sürekli "Gizli" göstermeye yol
# açar. Bu cooldown, aynı puuid için istekleri seyreltir.
RETRY_COOLDOWN_SECONDS = 30

# Başarılı Henrik hesap sorgusu (isim + level) bu süre boyunca önbellekten verilir.
# Level yavaş değiştiği için uzun tutulur; istek sayısı ve rate limit azalır.
ACCOUNT_CACHE_TTL_SECONDS = 60 * 60


class Names:

    def __init__(self, Requests, log, cfg=None):
        self.Requests = Requests
        self.log = log
        self.cfg = cfg
        # Gizli/streamer-mode isim çözümü tamamen yerelde yapılır.
        self._name_cache = {}
        # puuid -> (Henrik hesap verisi, geçerlilik sonu (time.monotonic()))
        self._account_cache = {}
        # puuid -> bir sonraki deneme izinli olduğu zaman (time.monotonic())
        self._retry_after = {}

    def _build_name(self, player_data):
        if not player_data:
            return ""
        return f"{player_data.get('GameName', '')}#{player_data.get('TagLine', '')}"

    # --- Gizli/streamer-mode isim çözümü: Henrik API ---

    def _get_henrik_api_key(self):
        key = HENRIK_API_KEY or getattr(self.cfg, "henrikdev_api_key", "") or ""
        return "" if key == HENRIK_KEY_PLACEHOLDER else key

    def has_api_key(self):
        return bool(self._get_henrik_api_key())

    def _henrik_account(self, puuid):
        """Henrik hesap verisini (name, tag, account_level ...) döner; önbellekli.

        Başarısız denemeden sonra RETRY_COOLDOWN_SECONDS boyunca ağa çıkmadan
        None döner. Anahtar yoksa da None."""
        now = time.monotonic()
        cached = self._account_cache.get(puuid)
        if cached and now < cached[1]:
            return cached[0]

        api_key = self._get_henrik_api_key()
        if not api_key:
            return None

        retry_after = self._retry_after.get(puuid)
        if retry_after is not None and now < retry_after:
            return None

        try:
            r = requests.get(
                f"https://api.henrikdev.xyz/valorant/v1/by-puuid/account/{puuid}",
                headers={"Authorization": api_key},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json().get("data") or {}
                if data:
                    self._account_cache[puuid] = (data, time.monotonic() + ACCOUNT_CACHE_TTL_SECONDS)
                    self._retry_after.pop(puuid, None)
                    return data
            else:
                self.log(f"henrik hesap sorgusu hata kodu {r.status_code}: {puuid}")
        except Exception as e:
            self.log(f"henrik hesap sorgusu hatasi: {e}")

        self._retry_after[puuid] = time.monotonic() + RETRY_COOLDOWN_SECONDS
        return None

    @staticmethod
    def _account_name(account):
        name, tag = (account or {}).get("name", ""), (account or {}).get("tag", "")
        if not name:
            return None
        return f"{name}#{tag}" if tag else name

    @staticmethod
    def _account_level(account):
        level = (account or {}).get("account_level")
        return level if isinstance(level, int) else None

    def _resolve_one(self, puuid):
        if puuid in self._name_cache:
            return self._name_cache[puuid]

        name = self._account_name(self._henrik_account(puuid))
        if name:
            self._name_cache[puuid] = name
            return name
        return HIDDEN_NAME

    # --- Bloklamayan isim çözümü: panel hemen açılsın, gizli isimler sonra gelsin ---

    @staticmethod
    def is_placeholder(name):
        return not name or name == HIDDEN_NAME

    def cached_name(self, puuid):
        """Çözülmüş gizli isim varsa döner, yoksa None (ağ isteği yapmaz)."""
        return self._name_cache.get(puuid)

    def resolve_hidden(self, puuid):
        """Tek bir gizli puuid'i Henrik API ile çözer; yavaş olabilir, bu
        yüzden arka plan thread'inden çağrılmalı. Çözülemezse placeholder döner."""
        return self._resolve_one(puuid)

    def cached_level(self, puuid):
        """Henrik'ten çekilmiş hesap leveli varsa döner, yoksa None (ağ isteği yapmaz)."""
        cached = self._account_cache.get(puuid)
        if cached and time.monotonic() < cached[1]:
            return self._account_level(cached[0])
        return None

    def resolve_level(self, puuid):
        """Oyuncunun hesap levelini Henrik API ile çeker; yavaş olabilir, bu
        yüzden arka plan thread'inden çağrılmalı. Alınamazsa None döner."""
        return self._account_level(self._henrik_account(puuid))

    def get_names_fast(self, players):
        """Panelin ilk çizimini bekletmemek için isimleri bloklamadan getirir.

        Riot'un name-service çağrısı tek istek (hızlı). Gizli oyuncular için
        yavaş Henrik çağrısı YAPILMAZ: önbellekte varsa gerçek isim,
        yoksa `Gizli` placeholder'ı döner; gerçek isim arka planda
        resolve_hidden() ile çözülüp panele sonradan yazılır.
        Dönüş: {puuid: isim}."""
        puuids = [p["Subject"] for p in players]
        found = {}
        try:
            response = requests.put(
                self.Requests.pd_url + "/name-service/v2/players",
                headers=self.Requests.get_headers(),
                json=puuids,
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                resp_data = response.json()
                if isinstance(resp_data, list):
                    for player in resp_data:
                        if isinstance(player, dict) and player.get("Subject"):
                            name = self._build_name(player)
                            if name and name != "#":
                                found[player["Subject"]] = name
        except Exception as e:
            self.log(f"Error fetching names from Riot API: {e}")

        return {
            puuid: found.get(puuid)
            or self._name_cache.get(puuid)
            or HIDDEN_NAME
            for puuid in puuids
        }

    def get_players_puuid(self, Players):
        return [player["Subject"] for player in Players]
