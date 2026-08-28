
class Rank:
    def __init__(self, Requests, log, content, ranks_before):
        self.Requests = Requests
        self.log = log
        self.ranks_before = ranks_before
        self.content = content
        self.requestMap = {}

    def get_request(self, puuid):
        if puuid in self.requestMap:
            return self.requestMap[puuid]

        response = self.Requests.fetch('pd', f"/mmr/v1/players/{puuid}", "get")
        self.requestMap[puuid] = response
        return response

    def invalidate_cached_responses(self):
        self.requestMap = {}

    #in future rewrite this code
    def get_rank(self, puuid, seasonID):
        response = self.get_request(puuid)
        # pyperclip.copy(str(response.json()))
        final = {
            "rank": None,
            "rr": None,
            "leaderboard": None,
            "peakrank": None,
            "wr": None,
            "numberofgames": 0,
            "peakrankact": None,
            "peakrankep": None,
            "statusgood": None,
            "statuscode": None,
            }
        r = None
        try:
            if response is None:
                self.log("rank isteği başarısız: sunucudan yanıt alınamadı")
                final["rank"] = 0
                final["rr"] = 0
                final["leaderboard"] = 0
            elif response.ok:
                # self.log("retrieved rank successfully")
                r = response.json()
                rankTIER = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["CompetitiveTier"]
                if int(rankTIER) >= 21:
                    # rank = [rankTIER,
                            # r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["RankedRating"],
                            # r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["LeaderboardRank"]]

                    final["rank"] = rankTIER
                    final["rr"] = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["RankedRating"]
                    final["leaderboard"] = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["LeaderboardRank"]
                elif int(rankTIER) not in (0, 1, 2):
                    final["rank"] = rankTIER
                    final["rr"] = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["RankedRating"]
                    final["leaderboard"] = 0

                    # rank = [rankTIER,
                            # r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["RankedRating"],
                            # 0]
                else:
                    final["rank"] = 0
                    final["rr"] = 0
                    final["leaderboard"] = 0

            else:
                self.log("failed getting rank")
                self.log(response.text)
                final["rank"] = 0
                final["rr"] = 0
                final["leaderboard"] = 0
        except (TypeError, KeyError, ValueError):
            final["rank"] = 0
            final["rr"] = 0
            final["leaderboard"] = 0
        max_rank = final["rank"]
        max_rank_season = seasonID
        if r is not None:
            competitive = r.get("QueueSkills", {}).get("competitive", {})
            seasons = competitive.get("SeasonalInfoBySeasonID")
            if seasons is not None:
                for season in seasons:
                    if seasons[season]["WinsByTier"] is not None:
                        for winByTier in seasons[season]["WinsByTier"]:
                            if season in self.ranks_before:
                                if int(winByTier) > 20:
                                    winByTier = int(winByTier) + 3
                            if int(winByTier) > max_rank:
                                max_rank = int(winByTier)
                                max_rank_season = season
                # rank.append(max_rank)
                final["peakrank"] = max_rank
            else:
                # rank.append(max_rank)
                final["peakrank"] = max_rank
            try:
                wins = seasons[seasonID]["NumberOfWinsWithPlacements"] if seasons else None
                total_games = seasons[seasonID]["NumberOfGames"] if seasons else None
                final["numberofgames"] = total_games
                try:
                    wr = int(wins / total_games * 100)
                except ZeroDivisionError: #no loses
                    wr = 100
            except (KeyError, TypeError): #haven't played this season, #no data?
                # print("test")
                wr = "N/A"
            final["wr"] = wr
        else:
            final["peakrank"] = max_rank
            final["wr"] = "N/A"

        # rank.append(wr)
        final["statusgood"] = response.ok if response is not None else False
        final["statuscode"] = response.status_code if response is not None else None


        #peak rank act and ep
        peak_rank_act_ep = self.content.get_act_episode_from_act_id(max_rank_season)
        final["peakrankact"] = peak_rank_act_ep["act"]
        final["peakrankep"] = peak_rank_act_ep["episode"]
        return final


if __name__ == "__main__":
    from constants import before_ascendant_seasons, version, NUMBERTORANKS
    from requestsV import Requests
    from logs import Logging
    from errors import Error
    import urllib3
    import pyperclip
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    Logging = Logging()
    log = Logging.log

    ErrorSRC = Error(log)

    Requests = Requests(version, log, ErrorSRC)
    #custom region
    # Requests.pd_url = "https://pd.na.a.pvp.net"

    #season id
    s_id = "67e373c7-48f7-b422-641b-079ace30b427" 

    r = Rank(Requests, log, before_ascendant_seasons)

    res = r.get_rank("", s_id)
    print(res)
    #[[rank, rr, leadeboard, peak rank, wr,] status]
    # print(f"Rank: {res[0][0]} - {NUMBERTORANKS[res[0][0]]}\nPeak Rank: {res[0][3]} - {NUMBERTORANKS[res[0][3]]}\nRR: {res[0][1]}\nLeaderboard: {res[0][2]}\nStatus is good: {res[1]}\nWR: {res[0][4]}%")
