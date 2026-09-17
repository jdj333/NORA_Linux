"""Small, explicit canvas gestures and guidance for the local language model."""
import re


def action(prompt):
    text = prompt.strip().lower().rstrip('.!')
    text = re.sub(r'^please\s+', '', text)
    if re.fullmatch(r'(?:clear|reset|empty) (?:the |our |your )?canvas', text):
        return 'clear'
    if re.fullmatch(r'(?:arrange|organize|rearrange|tidy)(?: up)? (?:the |our |your )?canvas', text):
        return 'arrange'
    return None


def example(prompt):
    """A concrete first sketch when the user explicitly leaves the topic open."""
    if re.fullmatch(r'(?:please\s+)?(?:visually\s+)?(?:show|draw|sketch)\s+'
                    r'(?:me\s+)?(?:an?|one)\s+idea(?:\s+(?:visually|on (?:the |our )?canvas))?[.!?]*',
                    prompt.strip(), re.I):
        return ('Here’s an idea: a small windowsill herb garden. Let’s map it on our canvas.\n'
                'Canvas: replace\n'
                'Sunny window -> Plant herbs -> Water and observe -> Fresh herbs\n'
                'Plant herbs -> Basil\nPlant herbs -> Mint\n'
                'We can change the idea or explore any part together.')
    return None


def visual_request(prompt):
    return bool(re.search(r'\b(canvas|visually|visualize|diagram|sketch|draw|map|show|explain|idea|concept|plan)\b',
                          prompt, re.I))


def directive(answer):
    # Only exact standalone directives outside code blocks are actionable.
    text = re.sub(r'```.*?```', '', answer, flags=re.S)
    match = re.search(r'^Canvas: (replace|arrange|clear)\s*$', text, re.M)
    return match.group(1) if match else None
