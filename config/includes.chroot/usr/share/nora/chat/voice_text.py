"""Text-only voice policy; no model, audio device, or GTK imports."""
import re


def spoken_text(text):
    # Do not read code, canvas directives, URLs or long command output aloud.
    text = re.sub(r'```.*?(?:```|$)', ' The command is shown in the terminal. ', text, flags=re.S)
    text = re.sub(r'^Canvas:.*$', '', text, flags=re.M)
    text = re.sub(r'!\[([^]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'https?://\S+', 'the linked website', text)
    text = re.sub(r'[*#`_]', '', text).replace('->', ', then ').replace('→', ', then ')
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > 1600:
        text = text[:1500].rsplit(' ', 1)[0] + '. The rest is in the chat.'
    return text


def speech_chunks(text):
    """Bound synthesis work and begin playback before the whole reply is synthesized."""
    chunks = []
    for sentence in re.split(r'(?<=[.!?])\s+', spoken_text(text)):
        while len(sentence) > 240:
            cut = sentence.rfind(' ', 0, 240)
            if cut < 1:
                cut = 240
            chunks.append(sentence[:cut])
            sentence = sentence[cut:].strip()
        if sentence:
            chunks.append(sentence)
    return chunks
