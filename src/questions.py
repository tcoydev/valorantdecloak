from InquirerPy.base.control import Choice
from src.constants import DEFAULT_CONFIG, WEAPONS

FLAGS_OPTS = {
    "peak_rank_act": "Peak Rank Act",
    "discord_rpc": "Discord Rich Presence",
}

weapon_question = lambda config: {
        "type": "fuzzy",
        "name": "weapon",
        "message": "Please select a weapon to show skin for:",
        "default": config.get("weapon","Vandal"),
        "choices": WEAPONS,
    }

port_question = lambda config: {
        "type": "number",
        "name": "port",
        "message": "Please enter port for server to run:",
        "default": config.get("port", 1100),
        "min_allowed":0,
        "max_allowed": 65535,
        "filter": lambda ans: int(ans)
    }

flags_question = lambda config: {
        "type": "checkbox",
        "name": "flags",
        "message": "Please select optional features:",
        "choices": [
            Choice(k, name=v, enabled=config.get("flags",DEFAULT_CONFIG["flags"]).get(k, DEFAULT_CONFIG["flags"][k]))
            for k, v in FLAGS_OPTS.items()
        ],
        "filter": lambda flags: {k: k in flags for k in FLAGS_OPTS.keys()},
        "long_instruction": "Press 'space' to toggle selection and 'enter' to submit"
    }

basic_questions = lambda config: [
    weapon_question(config=config),
    flags_question(config=config),
]

advance_questions = lambda config: [
    port_question(config=config),
] + basic_questions(config=config)
