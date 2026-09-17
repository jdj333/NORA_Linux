"""Shared native UI palette, matching https://noralinux.com/styles.css."""
COLORS = {
    'bg': '#080d0c', 'panel': '#0e1513', 'text': '#f1f5f1', 'muted': '#97a59e',
    'accent': '#a0f3c0', 'line': '#24312b', 'conversation': '#0e1711',
    'canvas': '#0b130f', 'node': '#15231a', 'node_border': '#395340',
    'connector': '#536d59', 'grid': '#344738', 'selected': '#1b3022',
    'input': '#101c14', 'error': '#e9ac99',
}


def rgb(name):
    value = COLORS[name].lstrip('#')
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


CSS = ('\n'.join('@define-color nora_' + key + ' ' + value + ';' for key, value in COLORS.items()) + '''
window { background: @nora_bg; color: @nora_text; font-family: "DM Sans", sans-serif; font-size: 12px; }
headerbar { background: @nora_panel; color: @nora_muted; border-bottom: 1px solid @nora_line;
            box-shadow: none; min-height: 38px; padding: 5px 12px; }
headerbar .title { font-family: "Space Grotesk", sans-serif; font-size: 13px; font-weight: 500; }
headerbar .subtitle { font-size: 10px; color: @nora_muted; }
box.conversation { background: @nora_conversation; }
box.sidebar { background: @nora_panel; border-right: 1px solid @nora_line; }
textview, textview text { background: @nora_conversation; color: @nora_text;
                        font-family: "DM Sans", sans-serif; font-size: 13px; }
textview selection, textview text selection { background: #365741; color: @nora_text; }
textview.terminal, textview.terminal text { font-family: "DejaVu Sans Mono", monospace;
                                         font-size: 12px; background: @nora_bg; }
frame.composer textview, frame.composer textview text { background: @nora_input; }
frame.composer { background: @nora_input; border-radius: 8px; }
button { background-image: none; background-color: transparent; color: @nora_muted;
         border: 1px solid #354b3b; border-radius: 6px; box-shadow: none;
         font-size: 12px; font-weight: 500; padding: 5px 11px; min-height: 22px; }
button:hover { background: @nora_selected; color: @nora_accent; border-color: #64886e; }
button:focus { border-color: @nora_accent; }
button:disabled { color: #66796c; border-color: @nora_line; }
button.suggested-action { background: @nora_accent; color: #102719; border-color: @nora_accent; }
button.suggested-action:hover { background: #c1ffda; }
button.suggested-action:disabled { background: @nora_selected; color: @nora_muted; border-color: @nora_line; }
label.status { color: @nora_muted; font-size: 11px; }
frame { border: none; }
frame > border { border: 1px solid @nora_line; border-radius: 8px; }
label.pane-title { color: #a7b8ac; font-size: 11px; font-weight: 500; letter-spacing: 1px; }
paned > separator { background: @nora_line; min-width: 1px; min-height: 1px; }
list.chats { background: transparent; color: #a7b8ac; font-size: 12px; }
list.chats row { padding: 9px 8px; margin-bottom: 4px; border: 1px solid transparent; border-radius: 6px; }
list.chats row:hover { background: #15231a; }
list.chats row:selected { background: @nora_selected; color: @nora_accent; border-color: #354b3b; }
layout.whiteboard { background: @nora_canvas; }
label.card-title { font-family: "Space Grotesk", sans-serif; font-weight: 500; color: @nora_text; font-size: 13px; }
.concept-node label { font-size: 12px; }
.concept-node label.status { font-size: 10px; color: #8aa993; }
.concept-node label.card-title { font-size: 13px; }
label.presence-name { font-family: "Space Grotesk", sans-serif; color: @nora_text;
                      font-size: 18px; font-weight: 500; letter-spacing: 1px; }
label.presence-state { color: @nora_accent; font-size: 11px; }
button.node-tool { background: transparent; border-color: transparent; color: #8aa993;
                   padding: 2px; min-width: 18px; min-height: 18px; opacity: 0.55; }
button.node-tool:hover, button.node-tool:focus { background: @nora_selected; color: @nora_accent; opacity: 1; }
checkbutton { color: @nora_muted; font-size: 11px; }
checkbutton check { background: @nora_panel; border-color: #395340; }
checkbutton check:checked { background: @nora_accent; color: #102719; border-color: @nora_accent; }
scrollbar { background: transparent; }
scrollbar slider { background: #354b3b; border: none; min-width: 5px; min-height: 5px; border-radius: 8px; }
entry, combobox { font-family: "DM Sans", sans-serif; font-size: 12px; }
''').encode('utf-8')
