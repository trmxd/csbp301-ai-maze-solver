"""Fast, browser-side maze animation for Streamlit.

The search itself still runs in Python. Only presentation is moved to the
browser so Streamlit does not need to render and transfer a Matplotlib image
for every explored cell.
"""

from __future__ import annotations

import json

import streamlit.components.v1 as components

from core.maze import Maze


def _animation_data(maze: Maze, results: list, speed: float, show_scores: bool) -> dict:
    delay_ms = 0 if speed <= 0 else max(28, round(speed * 1000))
    runs = []
    for result in results:
        scores = []
        if show_scores and result.algorithm == "A*" and maze.rows <= 12 and maze.cols <= 12:
            scores = [
                [row, col, g, h, f]
                for (row, col), (g, h, f) in result.scores.items()
            ]
        runs.append(
            {
                "algorithm": result.algorithm,
                "explored": [list(cell) for cell in result.explored_order],
                "path": [list(cell) for cell in result.path],
                "solved": result.solved,
                "scores": scores,
            }
        )
    return {
        "rows": maze.rows,
        "cols": maze.cols,
        "start": list(maze.start),
        "goal": list(maze.goal),
        "walls": [list(cell) for cell in sorted(maze.walls)],
        "delay": delay_ms,
        "runs": runs,
    }


def render_browser_animation(
    maze: Maze,
    results: list,
    speed: float,
    show_scores: bool = False,
    height: int | None = None,
) -> None:
    """Animate one or more search results without blocking the Python app."""

    data = json.dumps(_animation_data(maze, results, speed, show_scores), separators=(",", ":"))
    frame_height = height or (570 if maze.rows <= 12 else 650)
    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: transparent; color: #e2e8f0; }}
  .card {{
    background: linear-gradient(145deg, #111827, #0f172a);
    border: 1px solid #263449; border-radius: 18px; padding: 16px;
    box-shadow: 0 18px 42px rgba(2,6,23,.24); overflow: hidden;
  }}
  .top {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:12px; }}
  .eyebrow {{ color:#38bdf8; font-size:11px; letter-spacing:.14em; text-transform:uppercase; font-weight:800; }}
  #title {{ font-size:18px; font-weight:800; margin-top:2px; }}
  .controls {{ display:flex; gap:7px; }}
  button {{
    border:1px solid #334155; color:#e2e8f0; background:#172033; border-radius:9px;
    padding:7px 10px; cursor:pointer; font-weight:700; transition:.15s ease;
  }}
  button:hover {{ transform:translateY(-1px); border-color:#38bdf8; }}
  .track {{ height:6px; background:#263449; border-radius:99px; overflow:hidden; margin-bottom:12px; }}
  #bar {{ height:100%; width:0; background:linear-gradient(90deg,#38bdf8,#818cf8); transition:width .12s linear; }}
  .stage {{ display:grid; place-items:center; min-height:270px; }}
  #grid {{
    display:grid; width:min(100%, 520px); aspect-ratio:{maze.cols}/{maze.rows};
    gap:2px; padding:5px; border-radius:14px; background:#334155;
  }}
  .cell {{
    min-width:0; min-height:0; display:grid; place-items:center; position:relative;
    background:#f8fafc; color:#0f172a; border-radius:3px;
    transition:background .16s ease, transform .16s ease, box-shadow .16s ease;
    font-size:clamp(5px,1.05vw,9px); line-height:1.05; text-align:center;
  }}
  .wall {{ background:#1f2937; }}
  .visited {{ background:#bae6fd; animation:pop .22s ease-out; }}
  .path {{ background:#facc15; animation:pathPop .24s ease-out; }}
  .start {{ background:#22c55e !important; }}
  .goal {{ background:#ef4444 !important; }}
  .active {{ z-index:2; transform:scale(.82); box-shadow:0 0 0 4px #f97316, 0 0 18px #fb923c; }}
  .path::after {{ content:""; position:absolute; inset:35%; border-radius:99px; background:#854d0e; opacity:.52; }}
  .start::after, .goal::after {{ display:none; }}
  .score {{ opacity:.8; pointer-events:none; }}
  .footer {{ display:flex; justify-content:space-between; gap:12px; margin-top:12px; font-size:12px; color:#94a3b8; }}
  #status {{ color:#cbd5e1; font-weight:700; }}
  @keyframes pop {{ 0% {{ transform:scale(.55); background:#38bdf8; }} 100% {{ transform:scale(1); }} }}
  @keyframes pathPop {{ 0% {{ transform:scale(.55) rotate(-8deg); }} 100% {{ transform:scale(1); }} }}
  @media (prefers-color-scheme: light) {{
    body {{ color:#0f172a; }} .card {{ background:linear-gradient(145deg,#fff,#f8fafc); border-color:#dbe5f0; }}
    button {{ color:#0f172a; background:#fff; border-color:#cbd5e1; }} #status {{ color:#334155; }}
  }}
</style>
</head>
<body>
<div class="card">
  <div class="top">
    <div><div class="eyebrow">Live search</div><div id="title">Preparing animation…</div></div>
    <div class="controls"><button id="pause">Pause</button><button id="skip">Skip</button><button id="replay">Replay</button></div>
  </div>
  <div class="track"><div id="bar"></div></div>
  <div class="stage"><div id="grid"></div></div>
  <div class="footer"><span id="status">Ready</span><span id="counter">0 / 0</span></div>
</div>
<script>
const data = {data};
const grid = document.getElementById('grid');
const title = document.getElementById('title');
const status = document.getElementById('status');
const counter = document.getElementById('counter');
const bar = document.getElementById('bar');
const key = ([r,c]) => `${{r}}-${{c}}`;
const wallSet = new Set(data.walls.map(key));
const cells = new Map();
let paused = false, skipRun = false, generation = 0;

function buildGrid(run) {{
  grid.innerHTML = ''; cells.clear();
  grid.style.gridTemplateColumns = `repeat(${{data.cols}}, 1fr)`;
  const scoreMap = new Map(run.scores.map(([r,c,g,h,f]) => [`${{r}}-${{c}}`, `g=${{g}}<br>h=${{h}}<br>f=${{f}}`]));
  for (let r=0; r<data.rows; r++) for (let c=0; c<data.cols; c++) {{
    const id = `${{r}}-${{c}}`, el = document.createElement('div');
    el.className = 'cell';
    if (wallSet.has(id)) el.classList.add('wall');
    if (id === key(data.start)) el.classList.add('start');
    if (id === key(data.goal)) el.classList.add('goal');
    if (scoreMap.has(id)) el.innerHTML = `<span class="score">${{scoreMap.get(id)}}</span>`;
    grid.appendChild(el); cells.set(id, el);
  }}
}}
function sleep(ms) {{ return new Promise(resolve => setTimeout(resolve, ms)); }}
async function waitStep(token) {{
  while (paused && token === generation) await sleep(40);
  if (data.delay) await sleep(data.delay);
}}
function activate(cell, className) {{
  document.querySelectorAll('.active').forEach(el => el.classList.remove('active'));
  const el = cells.get(key(cell));
  if (el) {{ el.classList.add(className, 'active'); }}
}}
function finishRun(run) {{
  run.explored.forEach(cell => cells.get(key(cell))?.classList.add('visited'));
  run.path.forEach(cell => cells.get(key(cell))?.classList.add('path'));
  document.querySelectorAll('.active').forEach(el => el.classList.remove('active'));
  bar.style.width = '100%'; status.textContent = run.solved ? 'Solution complete ✓' : 'No path found';
}}
async function play() {{
  const token = ++generation; paused = false; skipRun = false;
  document.getElementById('pause').textContent = 'Pause';
  for (let runIndex=0; runIndex<data.runs.length && token===generation; runIndex++) {{
    const run = data.runs[runIndex]; buildGrid(run); title.textContent = `${{run.algorithm}} Search`;
    const total = Math.max(1, run.explored.length + run.path.length); let done = 0;
    bar.style.width = '0%';
    for (const cell of run.explored) {{
      if (token!==generation) return; if (skipRun) break;
      activate(cell, 'visited'); done++; status.textContent = `Exploring (${{cell[0]}}, ${{cell[1]}})`;
      counter.textContent = `${{done}} / ${{total}}`; bar.style.width = `${{done/total*100}}%`; await waitStep(token);
    }}
    if (!skipRun) for (const cell of run.path) {{
      if (token!==generation) return; if (skipRun) break;
      activate(cell, 'path'); done++; status.textContent = 'Drawing final route';
      counter.textContent = `${{done}} / ${{total}}`; bar.style.width = `${{done/total*100}}%`; await waitStep(token);
    }}
    finishRun(run); counter.textContent = `${{total}} / ${{total}}`; skipRun = false;
    if (runIndex < data.runs.length-1) await sleep(Math.max(350, data.delay*5));
  }}
}}
document.getElementById('pause').onclick = () => {{ paused=!paused; document.getElementById('pause').textContent=paused?'Resume':'Pause'; }};
document.getElementById('skip').onclick = () => {{ skipRun=true; const run=data.runs.find(r=>title.textContent.startsWith(r.algorithm)); if(run) finishRun(run); }};
document.getElementById('replay').onclick = play;
play();
</script>
</body>
</html>
"""
    components.html(html, height=frame_height, scrolling=False)
