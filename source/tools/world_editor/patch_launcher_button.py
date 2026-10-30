"""Add the WORLD EDITOR button to OfflineDaoc.Launcher/MainForm.cs (any 0.37-era launcher source).

    python patch_launcher_button.py path/to/MainForm.cs

The button opens <runtime>/world-workshop/WorldWorkshop.exe for this game; it explains when the editor is not installed.
Used to add the button on top of the exact launcher source an install was built from (no other launcher changes).
"""
import sys
from pathlib import Path

PATCHES = [
    ("    private readonly Button _playButton;\n",
     "    private readonly Button _playButton;\n    private readonly Button _editorButton;\n"),
    ("        _playButton = ActionButton(\"ENTER REALM\", Color.FromArgb(65, 94, 145));\n",
     "        _playButton = ActionButton(\"ENTER REALM\", Color.FromArgb(65, 94, 145));\n"
     "        _editorButton = ActionButton(\"WORLD EDITOR\", Color.FromArgb(92, 84, 128));\n"),
    ("        _playButton.Click += (_, _) => LaunchClient();\n",
     "        _playButton.Click += (_, _) => LaunchClient();\n        _editorButton.Click += (_, _) => OpenWorldEditor();\n"),
    ("        foreach (var button in new[] { _startButton, _stopButton, _playButton })\n        {\n            button.Width = 132;\n            button.Height = 26;\n            button.Margin = new Padding(2, 2, 2, 2);\n        }\n",
     "        foreach (var button in new[] { _startButton, _stopButton, _playButton, _editorButton })\n        {\n            button.Width = 132;\n            button.Height = 24;\n            button.Margin = new Padding(2, 1, 2, 1);\n        }\n"),
    ("        actions.Controls.Add(_playButton);\n",
     "        actions.Controls.Add(_playButton);\n        actions.Controls.Add(_editorButton);\n"
     "        SetToolTip(_editorButton, \"World Workshop: edit the world, NPCs, items, merchants and server settings of this game in your browser. \"\n"
     "            + \"Close the game and stop the server before saving changes.\");\n"),
    ("    private Control BuildCards()\n",
     "    // World Workshop (the world / item / data editor) installed beside the server: runtime\\world-workshop.\n"
     "    private string WorldEditorExecutable => Path.Combine(_root, \"world-workshop\", \"WorldWorkshop.exe\");\n\n"
     "    private void OpenWorldEditor()\n"
     "    {\n"
     "        if (!File.Exists(WorldEditorExecutable))\n"
     "        {\n"
     "            MessageBox.Show(this, \"World Workshop is not installed in this game.\\n\\nExpected: \" + WorldEditorExecutable,\n"
     "                \"World editor\", MessageBoxButtons.OK, MessageBoxIcon.Information);\n"
     "            return;\n"
     "        }\n"
     "        Process.Start(new ProcessStartInfo(WorldEditorExecutable)\n"
     "        {\n"
     "            Arguments = $\"--game \\\"{_root}\\\"\",\n"
     "            WorkingDirectory = Path.GetDirectoryName(WorldEditorExecutable)!,\n"
     "            UseShellExecute = false,\n"
     "        });\n"
     "    }\n\n"
     "    private Control BuildCards()\n"),
]


def patch(text):
    crlf = '\r\n' in text
    text = text.replace('\r\n', '\n')
    if '_editorButton' in text:
        raise SystemExit('already patched')
    for old, new in PATCHES:
        if text.count(old) != 1:
            raise SystemExit(f'anchor not found exactly once: {old.strip()[:60]}')
        text = text.replace(old, new)
    return text.replace('\n', '\r\n') if crlf else text


if __name__ == '__main__':
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    out = patch(raw.decode('utf-8-sig'))
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'') + out.encode('utf-8'))
    print('patched', path)
