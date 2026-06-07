#!/usr/bin/env python3
"""
Podcast Summaries - Web UI
Double-click Launch.bat to start, or run: python app.py
"""

import json
import logging
import os
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, Response, jsonify, render_template_string, request

ROOT = Path(__file__).parent
PODCASTS_DIR = ROOT / "podcasts"
PYTHON = sys.executable

app = Flask(__name__)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

_jobs: dict[str, queue.Queue] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_podcasts() -> list[str]:
    if not PODCASTS_DIR.exists():
        return []
    return sorted(d.name for d in PODCASTS_DIR.iterdir()
                  if d.is_dir() and not d.name.startswith("."))


def run_job(job_id: str, cmd: list[str]) -> None:
    q = _jobs[job_id]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, cwd=ROOT)
        for line in proc.stdout:
            q.put(("line", line.rstrip()))
        proc.wait()
        q.put(("done" if proc.returncode == 0 else "error",
               "" if proc.returncode == 0 else f"Process exited with code {proc.returncode}"))
    except Exception as e:
        q.put(("error", str(e)))


def start_job(cmd: list[str]) -> str:
    job_id = os.urandom(8).hex()
    _jobs[job_id] = queue.Queue()
    threading.Thread(target=run_job, args=(job_id, cmd), daemon=True).start()
    return job_id


# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/api/podcasts")
def api_podcasts():
    return jsonify(get_podcasts())


@app.route("/api/browse", methods=["POST"])
def browse():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[("Audio files", "*.mp3 *.m4a *.wav *.aiff *.aac"), ("All files", "*.*")]
        )
        root.destroy()
        return jsonify({"path": path or ""})
    except Exception as e:
        return jsonify({"path": "", "error": str(e)})


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    data = request.json
    audio = data.get("audio", "").strip()
    output = data.get("output", "").strip()
    model = data.get("model", "").strip()
    if not audio:
        return jsonify({"error": "Audio file path is required"}), 400
    cmd = [PYTHON, str(ROOT / "transcribe_episode.py"), audio]
    if output:
        cmd.append(output)
    if model:
        cmd += ["--model", model]
    return jsonify({"job_id": start_job(cmd)})


@app.route("/api/create-podcast", methods=["POST"])
def create_podcast():
    name = request.json.get("name", "").strip()
    if not name:
        return jsonify({"error": "Podcast name is required"}), 400
    return jsonify({"job_id": start_job([PYTHON, str(ROOT / "create_podcast.py"), name])})


@app.route("/api/search", methods=["POST"])
def search():
    data = request.json
    query = data.get("query", "").strip()
    podcast = data.get("podcast", "").strip()
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    cmd = [PYTHON, str(ROOT / "search_transcripts.py"), query]
    if podcast:
        cmd.append(f"podcasts/{podcast}")
    return jsonify({"job_id": start_job(cmd)})


@app.route("/api/check-links", methods=["POST"])
def check_links():
    podcast = request.json.get("podcast", "").strip()
    cmd = [PYTHON, str(ROOT / "check_links.py")]
    if podcast:
        cmd.append(f"podcasts/{podcast}")
    return jsonify({"job_id": start_job(cmd)})


@app.route("/api/generate-format", methods=["POST"])
def generate_format():
    data = request.json
    podcast = data.get("podcast", "").strip()
    rss = data.get("rss", "").strip()
    if not podcast:
        return jsonify({"error": "Select a podcast first"}), 400
    cmd = [PYTHON, str(ROOT / "generate_description_format.py"), f"podcasts/{podcast}"]
    if rss:
        cmd += ["--rss", rss]
    return jsonify({"job_id": start_job(cmd)})


@app.route("/api/stream/<job_id>")
def stream(job_id):
    if job_id not in _jobs:
        return jsonify({"error": "Job not found"}), 404

    def generate():
        q = _jobs[job_id]
        while True:
            try:
                kind, text = q.get(timeout=120)
                yield f"data: {json.dumps({'kind': kind, 'text': text})}\n\n"
                if kind in ("done", "error"):
                    _jobs.pop(job_id, None)
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'kind': 'error', 'text': 'Timed out waiting for output'})}\n\n"
                break

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Page ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML, podcasts=get_podcasts())


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Podcast Summaries</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #fdf8ee;
    --card:     #ffffff;
    --header:   #1a1000;
    --accent:   #daa520;
    --accent-h: #b8860b;
    --success:  #10b981;
    --error:    #ef4444;
    --text:     #1e1a0e;
    --muted:    #7a6b4a;
    --border:   #e8dfc0;
    --shadow:   0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.06);
    --radius:   12px;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── Header ── */
  header {
    background: var(--header);
    color: #fff;
    padding: 18px 32px;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,.3);
  }
  header .icon { font-size: 42px; line-height: 1; }
  header h1 { font-size: 20px; font-weight: 600; letter-spacing: -.3px; }
  header p  { font-size: 13px; color: #c8a96a; margin-top: 2px; }

  /* ── Main grid ── */
  main {
    flex: 1;
    padding: 32px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 24px;
    align-items: start;
    max-width: 1100px;
    margin: 0 auto;
    width: 100%;
  }

  /* ── Card ── */
  .card {
    background: var(--card);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .card-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .card-icon {
    width: 42px; height: 42px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
  }
  .card-icon.purple { background: #fef9e7; }
  .card-icon.blue   { background: #fef3c7; }
  .card-icon.green  { background: #fde68a; }
  .card-icon.orange { background: #fde68a; }
  .card-title { font-size: 16px; font-weight: 600; }
  .card-desc  { font-size: 13px; color: var(--muted); margin-top: 2px; }

  /* ── Form elements ── */
  .field { display: flex; flex-direction: column; gap: 6px; }
  label  { font-size: 13px; font-weight: 500; color: var(--text); }

  input[type=text], select {
    width: 100%;
    padding: 9px 12px;
    border: 1.5px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    color: var(--text);
    background: #fff;
    transition: border-color .15s;
    outline: none;
  }
  input[type=text]:focus, select:focus { border-color: var(--accent); }
  input[type=text]::placeholder { color: #cbd5e1; }

  .input-row {
    display: flex;
    gap: 8px;
  }
  .input-row input { flex: 1; min-width: 0; }

  /* ── Buttons ── */
  button {
    cursor: pointer;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    padding: 10px 16px;
    transition: background .15s, transform .1s, opacity .15s;
  }
  button:active { transform: scale(.98); }
  button:disabled { opacity: .5; cursor: not-allowed; }

  .btn-primary {
    background: var(--accent);
    color: #fff;
    width: 100%;
    padding: 11px;
    font-size: 15px;
  }
  .btn-primary:hover:not(:disabled) { background: var(--accent-h); }

  .btn-browse {
    background: var(--bg);
    color: var(--text);
    border: 1.5px solid var(--border);
    padding: 9px 14px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .btn-browse:hover { background: var(--border); }

  /* ── Optional row ── */
  .optional-label {
    font-size: 12px;
    color: var(--muted);
    margin-top: -8px;
  }

  /* ── Console ── */
  #console-wrap {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    background: #0f172a;
    color: #e2e8f0;
    font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    transform: translateY(100%);
    transition: transform .3s ease;
    box-shadow: 0 -4px 24px rgba(0,0,0,.4);
    z-index: 100;
    display: flex;
    flex-direction: column;
  }
  #console-wrap.open { transform: translateY(0); }

  #console-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: #1e293b;
    border-bottom: 1px solid #334155;
    cursor: pointer;
    user-select: none;
  }
  #console-bar .console-title {
    display: flex; align-items: center; gap: 8px;
    font-size: 13px; font-weight: 500;
  }
  #console-bar .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #64748b;
  }
  #console-bar .dot.running { background: #fbbf24; animation: pulse 1s infinite; }
  #console-bar .dot.done    { background: var(--success); }
  #console-bar .dot.error   { background: var(--error); }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.4; } }

  #console-close {
    background: transparent; color: #94a3b8;
    padding: 2px 6px; font-size: 16px;
  }
  #console-close:hover { color: #fff; }

  #console-output {
    padding: 12px 16px;
    height: 200px;
    overflow-y: auto;
    line-height: 1.6;
  }
  #console-output .line { color: #cbd5e1; }
  #console-output .done  { color: var(--success); font-weight: 600; }
  #console-output .error { color: var(--error); font-weight: 600; }

  /* ── Toast ── */
  #toast {
    position: fixed; top: 20px; right: 20px;
    padding: 12px 18px; border-radius: 8px;
    font-size: 14px; font-weight: 500;
    color: #fff; opacity: 0;
    transition: opacity .3s;
    pointer-events: none;
    z-index: 200;
  }
  #toast.show { opacity: 1; }
  #toast.success { background: var(--success); }
  #toast.error   { background: var(--error); }
</style>
</head>
<body>

<header>
  <div class="icon">🎙</div>
  <div>
    <h1>Podcast Summaries</h1>
    <p>Transcription &amp; workflow tools</p>
  </div>
</header>

<main>

  <!-- ── Transcribe ── -->
  <div class="card">
    <div class="card-header">
      <div class="card-icon purple">🎧</div>
      <div>
        <div class="card-title">Transcribe Episode</div>
        <div class="card-desc">Convert an audio file to a text transcript</div>
      </div>
    </div>

    <div class="field">
      <label for="audio-path">Audio file</label>
      <div class="input-row">
        <input type="text" id="audio-path" placeholder="Path to .mp3 / .m4a / .wav …">
        <button class="btn-browse" onclick="browse()">Browse</button>
      </div>
    </div>

    <div class="field">
      <label for="output-path">Output path <span style="color:var(--muted);font-weight:400">(optional)</span></label>
      <input type="text" id="output-path" placeholder="podcasts\MyPodcast\Transcripts\episode.txt">
      <div class="optional-label">Leave blank to save alongside the audio file</div>
    </div>

    <div class="field">
      <label for="model-select">Gemini model <span style="color:var(--muted);font-weight:400">(optional)</span></label>
      <select id="model-select">
        <option value="">gemini-2.5-flash-lite (default)</option>
        <option value="gemini-2.5-flash">gemini-2.5-flash</option>
        <option value="gemini-2.5-pro">gemini-2.5-pro (higher accuracy)</option>
      </select>
    </div>

    <button class="btn-primary" onclick="transcribe()">Transcribe</button>
  </div>

  <!-- ── Create Podcast ── -->
  <div class="card">
    <div class="card-header">
      <div class="card-icon blue">📁</div>
      <div>
        <div class="card-title">Create New Podcast</div>
        <div class="card-desc">Scaffold a new podcast folder and starter files</div>
      </div>
    </div>

    <div class="field">
      <label for="podcast-name">Podcast name</label>
      <input type="text" id="podcast-name" placeholder="e.g. Joe's Podcast Shack">
    </div>

    <div style="background:#fdf8ee; border:1.5px solid var(--border); border-radius:8px; padding:14px; font-size:13px; color:var(--muted); line-height:1.6;">
      Creates the folder structure, placeholder prompt files, and an initial git
      commit under <code style="background:#e8dfc0;padding:1px 5px;border-radius:4px">podcasts/</code>.
      Follow up with Claude to fill in the show details and connect to GitHub.
    </div>

    <button class="btn-primary" onclick="createPodcast()">Create Podcast Repo</button>
  </div>

  <!-- ── Generate Format ── -->
  <div class="card">
    <div class="card-header">
      <div class="card-icon green">✨</div>
      <div>
        <div class="card-title">Generate Description Format</div>
        <div class="card-desc">Draft format rules from published episodes</div>
      </div>
    </div>

    <div class="field">
      <label for="podcast-select">Podcast</label>
      <select id="podcast-select">
        <option value="">— select a podcast —</option>
        {% for p in podcasts %}
        <option value="{{ p }}">{{ p }}</option>
        {% endfor %}
      </select>
    </div>

    <div class="field">
      <label for="rss-url">RSS feed URL <span style="color:var(--muted);font-weight:400">(optional)</span></label>
      <input type="text" id="rss-url" placeholder="https://feeds.example.com/feed.xml">
      <div class="optional-label">Leave blank to use the URL already in Workflow.txt</div>
    </div>

    <div style="background:#fdf8ee; border:1.5px solid var(--border); border-radius:8px; padding:14px; font-size:13px; color:var(--muted); line-height:1.6;">
      Analyses the last 10 published episode descriptions and writes
      <code style="background:#e8dfc0;padding:1px 5px;border-radius:4px">Prompts/Description_Format.txt</code>.
      Requires a Google API key and at least 5 published episodes.
    </div>

    <button class="btn-primary" onclick="generateFormat()">Generate Format File</button>
  </div>

  <!-- ── Search Transcripts ── -->
  <div class="card">
    <div class="card-header">
      <div class="card-icon purple">🔍</div>
      <div>
        <div class="card-title">Search Transcripts</div>
        <div class="card-desc">Find a guest, topic, or phrase across all episodes</div>
      </div>
    </div>

    <div class="field">
      <label for="search-query">Search</label>
      <input type="text" id="search-query" placeholder="e.g. Ben Cattaneo, fire curtain, IBC 2027"
             onkeydown="if(event.key==='Enter') searchTranscripts()">
    </div>

    <div class="field">
      <label for="search-podcast-select">Podcast <span style="color:var(--muted);font-weight:400">(optional)</span></label>
      <select id="search-podcast-select">
        <option value="">— all podcasts —</option>
        {% for p in podcasts %}
        <option value="{{ p }}">{{ p }}</option>
        {% endfor %}
      </select>
    </div>

    <button class="btn-primary" onclick="searchTranscripts()">Search</button>
  </div>

  <!-- ── Check Links ── -->
  <div class="card">
    <div class="card-header">
      <div class="card-icon orange">🔗</div>
      <div>
        <div class="card-title">Check Links</div>
        <div class="card-desc">Verify Show Notes URLs are still live</div>
      </div>
    </div>

    <div class="field">
      <label for="check-podcast-select">Podcast</label>
      <select id="check-podcast-select">
        <option value="">— all podcasts —</option>
        {% for p in podcasts %}
        <option value="{{ p }}">{{ p }}</option>
        {% endfor %}
      </select>
    </div>

    <div style="background:#fdf8ee; border:1.5px solid var(--border); border-radius:8px; padding:14px; font-size:13px; color:var(--muted); line-height:1.6;">
      Scans every episode summary and makes a live request to each URL.
      Reports any that return an error or can't be reached.
    </div>

    <button class="btn-primary" onclick="checkLinks()">Check Links</button>
  </div>

</main>

<!-- ── Footer ── -->
<footer style="text-align:center; padding:20px; font-size:13px; color:var(--muted);">
  <a href="https://github.com/fractAlbert/PodcastSummarizer" target="_blank"
     style="color:var(--accent); text-decoration:none;">
    PodcastSummarizer on GitHub
  </a>
</footer>

<!-- ── Console ── -->
<div id="console-wrap">
  <div id="console-bar" onclick="toggleConsole()">
    <div class="console-title">
      <div class="dot" id="status-dot"></div>
      <span id="console-label">Output</span>
    </div>
    <button id="console-close" onclick="event.stopPropagation(); closeConsole()">✕</button>
  </div>
  <div id="console-output"></div>
</div>

<div id="toast"></div>

<script>
  // ── Utilities ───────────────────────────────────────────────────────────────

  function toast(msg, type = "success") {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.className = `show ${type}`;
    setTimeout(() => el.className = "", 3000);
  }

  function openConsole(label) {
    document.getElementById("console-wrap").classList.add("open");
    document.getElementById("console-label").textContent = label;
    document.getElementById("console-output").innerHTML = "";
    setDot("running");
  }

  function closeConsole() {
    document.getElementById("console-wrap").classList.remove("open");
  }

  function toggleConsole() {
    document.getElementById("console-wrap").classList.toggle("open");
  }

  function setDot(state) {
    const dot = document.getElementById("status-dot");
    dot.className = "dot " + state;
  }

  function appendLine(text, cls = "line") {
    const out = document.getElementById("console-output");
    const div = document.createElement("div");
    div.className = cls;
    div.textContent = text;
    out.appendChild(div);
    out.scrollTop = out.scrollHeight;
  }

  function disableButtons(disabled) {
    document.querySelectorAll(".btn-primary").forEach(b => b.disabled = disabled);
  }

  // ── Job streaming ────────────────────────────────────────────────────────────

  function streamJob(jobId, label) {
    openConsole(label);
    disableButtons(true);
    const es = new EventSource(`/api/stream/${jobId}`);
    es.onmessage = e => {
      const { kind, text } = JSON.parse(e.data);
      if (kind === "line") {
        appendLine(text);
      } else if (kind === "done") {
        appendLine("Done.", "done");
        setDot("done");
        toast(`${label} complete`);
        disableButtons(false);
        es.close();
      } else {
        appendLine(`Error: ${text}`, "error");
        setDot("error");
        toast(`${label} failed`, "error");
        disableButtons(false);
        es.close();
      }
    };
    es.onerror = () => {
      appendLine("Connection lost.", "error");
      setDot("error");
      disableButtons(false);
      es.close();
    };
  }

  async function postAndStream(url, body, label) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      toast(data.error || "Request failed", "error");
      return;
    }
    streamJob(data.job_id, label);
  }

  // ── Actions ──────────────────────────────────────────────────────────────────

  async function browse() {
    const res = await fetch("/api/browse", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: "{}" });
    const { path } = await res.json();
    if (path) document.getElementById("audio-path").value = path;
  }

  function transcribe() {
    const audio  = document.getElementById("audio-path").value.trim();
    const output = document.getElementById("output-path").value.trim();
    const model  = document.getElementById("model-select").value;
    if (!audio) { toast("Please select an audio file", "error"); return; }
    postAndStream("/api/transcribe", { audio, output, model }, "Transcribe");
  }

  function createPodcast() {
    const name = document.getElementById("podcast-name").value.trim();
    if (!name) { toast("Please enter a podcast name", "error"); return; }
    postAndStream("/api/create-podcast", { name }, `Create "${name}"`);
  }

  function searchTranscripts() {
    const query   = document.getElementById("search-query").value.trim();
    const podcast = document.getElementById("search-podcast-select").value;
    if (!query) { toast("Please enter a search term", "error"); return; }
    postAndStream("/api/search", { query, podcast }, `Search: "${query}"`);
  }

  function checkLinks() {
    const podcast = document.getElementById("check-podcast-select").value;
    const label = podcast ? `Check links — ${podcast}` : "Check links — all podcasts";
    postAndStream("/api/check-links", { podcast }, label);
  }

  function generateFormat() {
    const podcast = document.getElementById("podcast-select").value;
    const rss     = document.getElementById("rss-url").value.trim();
    if (!podcast) { toast("Please select a podcast", "error"); return; }
    postAndStream("/api/generate-format", { podcast, rss },
                  `Generate format for ${podcast}`);
  }
</script>
</body>
</html>
"""

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = 5000
    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    print(f"Podcast Summaries running at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    app.run(host="localhost", port=port, debug=False, threaded=True)
