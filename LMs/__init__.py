from .ChatGPT import ChatGPT


def create_lm_model(name, **kwargs):
    if name == "ChatGPT":
        return ChatGPT(**kwargs)
    else:
        raise ValueError(f"Unknown LM model: {name}")
