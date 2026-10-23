import os, json, random, sqlite3, hashlib
from datetime import datetime
import requests
import streamlit as st

TITLE = "Roblox Modern Story Studio"
BASE_URL_DEFAULT = "https://clariohub.id/v1"
MODELS = [
 "clario/hy3","clario/hy4-preview","clario/deepseek-v4-flash",
 "clario/deepseek-v4-flash-0731","clario/deepseek-v4-pro","clario/deepseek-v4-pro-0813",
 "clario/deepseek-v4.1-flash","clario/glm-5.2","clario/glm-5.3","clario/glm-5.3-flash",
 "clario/minimax-m3","clario/gemini-3.7-flash","clario/gpt-5.6-sol","clario/opus-5",
 "clario/deepseek-v4.1-flash-auto","clario/glm-5.3-flash-auto","clario/gemini-3.7-flash-auto"
]
CATEGORIES = {
 "Versus & Competition":25, "Mystery & Deception":20, "Horror & Survival":15,
 "Betrayal & Emotional":15, "Zero to Hero":10, "Challenge":10, "Loop & Mind-Bending":5
}
HINTS = {
 "Versus & Competition":"rivalry, competition, unexpected but logical winner",
 "Mystery & Deception":"strange clue, hidden truth, clever deception and reveal",
 "Horror & Survival":"urgent escape or spooky threat with a meaningful reveal, not graphic",
 "Betrayal & Emotional":"friendship, sacrifice or betrayal with a clear emotional turn",
 "Zero to Hero":"underestimated character wins through courage or cleverness",
 "Challenge":"simple visual challenge, clear rules, rising pressure, visible outcome",
 "Loop & Mind-Bending":"time loop, clone or impossible situation with a satisfying twist"
}
SYSTEM = """You write original, coherent 16-second YouTube Shorts stories in a Roblox Modern 3D blocky world.
Write simple natural English. First second shows an immediate visual hook, no intro. Scene 2 must continue from the exact physical state at the end of Scene 1: same characters, outfits, props, positions, lighting and location; no jump, reset or repeated action. Keep dialogue short (3-5 lines total). Use expressive blocky avatars, detailed colorful game environment, vertical 9:16. Not photorealistic humans, anime or 2D. Do not put readable text inside video frames. Use original generic characters/settings; don't copy game stories. CTA only if it fits naturally. ENDING MOTION QUALITY: in the final 2 seconds, complete the story action smoothly with continuous body and camera momentum and a small natural follow-through. Do not abruptly freeze, snap into a stiff pose, jerk or abruptly stop the camera, or leave movement unfinished. End on an intentional, visually complete frame while preserving Roblox blocky animation style. Return JSON only."""

def db_init():
    with sqlite3.connect("roblox_story_history.db") as c:
        c.execute("""CREATE TABLE IF NOT EXISTS stories(
        id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, title TEXT, category TEXT,
        premise TEXT, fingerprint TEXT UNIQUE, data TEXT)""")

def history_rows(limit=100):
    with sqlite3.connect("roblox_story_history.db") as c:
        rows=c.execute("SELECT id,created,title,category,premise,data FROM stories ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    return [{"id":r[0],"created":r[1],"title":r[2],"category":r[3],"premise":r[4],"data":r[5]} for r in rows]

def save_story(s, category):
    raw="|".join([str(s.get("title","")).lower(),str(s.get("premise","")).lower(),
                  str(s.get("scene1",{}).get("end_frame_description","")).lower(),
                  str(s.get("scene2",{}).get("opening_frame_description","")).lower(),
                  str(s.get("twist","")).lower()])
    fp=hashlib.sha256(raw.encode()).hexdigest()
    with sqlite3.connect("roblox_story_history.db") as c:
        c.execute("INSERT OR IGNORE INTO stories(created,title,category,premise,fingerprint,data) VALUES(?,?,?,?,?,?)",
                  (datetime.now().isoformat(timespec="seconds"),s.get("title","Untitled"),category,s.get("premise",""),fp,json.dumps(s,ensure_ascii=False)))

def api_key():
    """Read the ClarioHub key from Streamlit Secrets or environment variables."""
    names = ("CLARIO_API_KEY", "CLARIOHUB_API_KEY", "CLARIOHUB_KEY", "API_KEY")
    try:
        secrets = st.secrets
        for name in names:
            value = secrets.get(name, "")
            if value and str(value).strip():
                return str(value).strip()
        # Also support [clario] api_key = "..." TOML format.
        try:
            nested = secrets.get("clario", {})
            if hasattr(nested, "get"):
                value = nested.get("api_key", "")
                if value and str(value).strip():
                    return str(value).strip()
        except Exception:
            pass
    except Exception:
        pass
    for name in names:
        value = os.getenv(name, "")
        if value and value.strip():
            return value.strip()
    return ""

def ask_clario(base, key, model, user_prompt, temperature):
    url=base.rstrip("/")+"/chat/completions"
    body={"model":model,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":user_prompt}],
          "temperature":temperature,"response_format":{"type":"json_object"}}
    r=requests.post(url,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},json=body,timeout=120)
    if not r.ok: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:1000]}")
    try: text=r.json()["choices"][0]["message"]["content"]
    except Exception: raise RuntimeError("Respons API tidak sesuai format OpenAI Chat Completions.")
    if isinstance(text,list): text="".join(str(i.get("text","")) for i in text if isinstance(i,dict))
    text=str(text).strip()
    if text.startswith("```"): text=text.split("\n",1)[-1].removesuffix("```").strip()
    return json.loads(text)

def prompt_for(category, theme, history, avoid):
    old="\n".join(f"- {x['title']} [{x['category']}]: {x['premise']}" for x in history[:35]) or "- None yet"
    theme=theme.strip() or "Invent a fresh idea; user supplied no theme."
    avoid=avoid.strip() or "Nothing specified."
    return f"""
Create ONE complete 16-second Roblox Modern Shorts story. Category: {category}.
Category direction: {HINTS[category]}.
Optional theme: {theme}
Avoid: {avoid}
Do not repeat these saved local ideas:
{old}

Return JSON in this structure:
{{
"title":"SHORT ALL-CAPS TITLE, 3-7 WORDS","category":"{category}","premise":"one sentence","hook":"visual hook in first 1-2 sec",
"characters":[{{"name":"Name","visual_description":"specific blocky avatar: face, colors, clothes, accessories","personality":"short note"}}],
"continuity_bible":{{"visual_style":"Roblox modern 3D blocky, vertical 9:16","location":"specific place","lighting_weather":"specific lighting","important_props":["prop"],"character_lock":"fixed descriptions","starting_state":"initial positions","scene1_end_state":"precise state at 8 sec","scene2_start_state":"must match scene1_end_state exactly"}},
"scene1":{{"duration_seconds":8,"timeline":[
{{"time":"0-2s","visual_action":"immediate hook","camera":"camera movement","dialogue":[{{"character":"Name","line":"short line"}}],"sound_effect":"SFX"}},
{{"time":"2-5s","visual_action":"conflict develops","camera":"camera","dialogue":[],"sound_effect":"SFX"}},
{{"time":"5-8s","visual_action":"situation leads into scene 2","camera":"camera","dialogue":[],"sound_effect":"SFX"}}],
"end_frame_description":"exact frame at 8 seconds","video_prompt":"detailed standalone English Google Flow prompt for 8-second vertical 9:16 clip; describe all characters, action, setting, camera and constraints"}},
"scene2":{{"duration_seconds":8,"timeline":[
{{"time":"8-11s","visual_action":"direct continuation","camera":"camera","dialogue":[],"sound_effect":"SFX"}},
{{"time":"11-14s","visual_action":"conflict escalates or reveal","camera":"camera","dialogue":[],"sound_effect":"SFX"}},
{{"time":"14-16s","visual_action":"payoff/ending","camera":"camera","dialogue":[],"sound_effect":"SFX"}}],
"opening_frame_description":"must match scene1 end frame exactly","video_prompt":"detailed standalone English Google Flow continuation prompt; repeat character and location descriptions; start from exact Scene 1 end state; no reset or repeated action. In the final 2 seconds, finish the main action naturally with continuous momentum, subtle follow-through and smooth controlled camera movement. No abrupt freeze, sudden camera stop, stiff final pose, or unfinished action; end on a deliberate, visually complete frame"}},
"twist":"reveal","ending":"resolution","cta":{{"use_cta":false,"line":"","style":"none or natural fit"}},
"subtitle_lines":[{{"scene":1,"approx_time":"0.3-1.8s","character":"Name","text":"SHORT SUBTITLE"}},{{"scene":2,"approx_time":"14-16s","character":"Name","text":"SHORT SUBTITLE"}}],
"youtube":{{"description":"short English description","hashtags":["#Roblox","#Shorts"],"tags":["Roblox story","Roblox shorts"]}},
"quality_check":{{"hook_is_immediate":true,"cause_and_effect_is_clear":true,"scene2_continues_scene1":true,"character_appearance_consistent":true,"ending_pays_off_hook":true,"dialogue_fits_16_seconds":true,"notes":"production caveat"}}
}}
Story must resolve within 16 sec unless satisfying serial cliffhanger. Keep dialogue 3-5 short lines total. Scene 2 must continue physically from Scene 1. JSON only.
"""

def demo_story(category):
    return {
      "title":"THE WRONG PLAYER TO TRICK","category":category,
      "premise":"A smug Pro steals a glowing key, unaware the clever Noob switched it for a decoy.",
      "hook":"A Pro snatches a glowing key and it flashes red.",
      "characters":[
        {"name":"Noob","visual_description":"Yellow blocky head, simple black face, blue torso, lime-green legs, yellow arms.","personality":"quiet and observant"},
        {"name":"Pro","visual_description":"Blocky avatar with swept brown hair, black jacket, blue shirt and dark pants.","personality":"overconfident"}
      ],
      "continuity_bible":{"visual_style":"Roblox modern 3D blocky, colorful detailed game world, vertical 9:16",
        "location":"sunny futuristic plaza with a locked vault","lighting_weather":"bright midday sun",
        "important_props":["glowing red decoy key","real blue key","small vault"],
        "character_lock":"Noob: yellow head, blue torso, lime legs. Pro: brown swept hair, black jacket, blue shirt, dark pants.",
        "starting_state":"Noob left of vault with blue key; Pro right reaching for it.",
        "scene1_end_state":"Pro right of closed vault holding flashing red key at chest height; Noob left with one hand behind his back.",
        "scene2_start_state":"Exactly match Scene 1 end state."},
      "scene1":{"duration_seconds":8,"timeline":[
        {"time":"0-2s","visual_action":"Pro snatches the glowing key; it flashes red.","camera":"fast push-in on key then faces","dialogue":[{"character":"Pro","line":"Too easy, Noob!"}],"sound_effect":"whoosh and warning beep"},
        {"time":"2-5s","visual_action":"Pro turns toward vault while Noob hides his other hand behind his back.","camera":"medium two-shot","dialogue":[{"character":"Noob","line":"You sure that's the right key?"}],"sound_effect":"quiet ticking"},
        {"time":"5-8s","visual_action":"Red key flashes faster; Pro freezes before the closed vault.","camera":"close-up then hold","dialogue":[],"sound_effect":"three warning beeps"}],
        "end_frame_description":"Pro right of closed vault holding flashing red key at chest height; Noob left with one hand behind his back; both face vault.",
        "video_prompt":"8-second vertical 9:16 Roblox modern 3D blocky clip in a sunny futuristic plaza. Noob has yellow head, blue torso, lime-green legs. Pro has swept brown hair, black jacket, blue shirt, dark pants. Pro snatches a glowing key; it flashes red. Pro says 'Too easy, Noob!' Noob asks 'You sure that's the right key?' Pro faces the closed vault as the key flashes faster. End with Pro on right holding red key at chest height, Noob left with one hand behind his back, vault closed. Bright game lighting, clear action. No photorealism, anime, outfit changes, extra limbs or in-frame text."},
      "scene2":{"duration_seconds":8,"timeline":[
        {"time":"8-11s","visual_action":"Continue from same frame. Pro inserts red key; a spring glove pops out and knocks him into soft foam blocks.","camera":"track key then pull back","dialogue":[{"character":"Pro","line":"Wait—what?!"}],"sound_effect":"click, boing"},
        {"time":"11-14s","visual_action":"Noob reveals the real blue key while Pro sits in foam blocks.","camera":"low angle then key reveal","dialogue":[{"character":"Noob","line":"You stole my decoy."}],"sound_effect":"soft bounce"},
        {"time":"14-16s","visual_action":"Noob opens vault and reveals a tiny trophy; Pro groans.","camera":"quick reveal","dialogue":[{"character":"Noob","line":"Skill issue."}],"sound_effect":"victory chime"}],
        "opening_frame_description":"Match Scene 1 final frame exactly: Pro right holding flashing red key at chest height, Noob left with one hand behind his back, vault closed.",
        "video_prompt":"8-second vertical 9:16 continuation of the previous Roblox modern 3D blocky clip. Keep the same sunny plaza, vault, lighting and avatars: Noob yellow head, blue torso, lime legs; Pro brown hair, black jacket, blue shirt, dark pants. Start with Pro on right holding flashing red key at chest height, Noob on left with one hand behind his back, vault closed. Pro inserts key; a spring glove knocks him safely into soft foam blocks. Pro says 'Wait—what?!' Noob reveals blue key and says 'You stole my decoy.' Noob opens vault with tiny trophy; says 'Skill issue.' No reset, teleporting, outfit changes, photorealism, anime or in-frame text."},
      "twist":"The stolen key was a decoy and Noob expected the theft.",
      "ending":"Noob opens the vault and reveals a tiny trophy, embarrassing the Pro.",
      "cta":{"use_cta":False,"line":"","style":"none"},
      "subtitle_lines":[
        {"scene":1,"approx_time":"0.3-1.8s","character":"Pro","text":"TOO EASY, NOOB!"},
        {"scene":1,"approx_time":"2.4-4.4s","character":"Noob","text":"YOU SURE THAT'S THE RIGHT KEY?"},
        {"scene":2,"approx_time":"8.5-9.5s","character":"Pro","text":"WAIT—WHAT?!"},
        {"scene":2,"approx_time":"11.2-12.8s","character":"Noob","text":"YOU STOLE MY DECOY."},
        {"scene":2,"approx_time":"14.2-15.8s","character":"Noob","text":"SKILL ISSUE."}],
      "youtube":{"description":"A confident Pro tries to trick a Noob, but the Noob has a plan.","hashtags":["#Roblox","#RobloxShorts","#GamingShorts"],"tags":["Roblox story","Roblox modern","Roblox shorts","Noob vs Pro"]},
      "quality_check":{"hook_is_immediate":True,"cause_and_effect_is_clear":True,"scene2_continues_scene1":True,"character_appearance_consistent":True,"ending_pays_off_hook":True,"dialogue_fits_16_seconds":True,"notes":"Demo only; connect API for fresh stories."}
    }

def main():
    st.set_page_config(page_title=TITLE,page_icon="🎮",layout="wide")
    db_init()
    st.markdown("""<style>
    /* Light theme: calm, high contrast, comfortable on mobile */
    .stApp { background: #F4F7FB; color: #243247; }
    [data-testid="stHeader"] { background: rgba(244,247,251,.94); }
    [data-testid="stSidebar"] { background: #EAF0F7; }
    .block-container { padding-top: 1.35rem; max-width: 1200px; }
    h1, h2, h3, h4 { color: #172B4D !important; }
    p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: #34445B; }
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #FFFFFF !important; color: #1F2937 !important;
        border-color: #CBD5E1 !important; border-radius: 10px !important;
    }
    div.stButton > button, div[data-testid="stDownloadButton"] button {
        border-radius: 10px; font-weight: 700; min-height: 2.7rem;
        border: 1px solid #CBD5E1;
    }
    div[data-testid="stAlert"] { border-radius: 12px; }
    div[data-testid="stMetric"] {
        background: #FFFFFF; padding: 12px; border-radius: 12px;
        border: 1px solid #E2E8F0;
    }
    </style>""", unsafe_allow_html=True)
    st.title("🎮 Roblox Modern Story Studio")
    st.caption("Global Shorts · Roblox Modern 3D Blocky · 16 seconds · 2 connected scenes × 8 seconds")
    with st.sidebar:
        page=st.radio("Menu",["Generate Story","Story History","Character & Prompt Rules","Settings"])
        st.divider()
        st.caption("Target mix")
        for k,v in CATEGORIES.items(): st.write(f"{v}% · {k}")
    history=history_rows()
    if page=="Generate Story":
        theme=st.text_input("Idea / theme (optional)",placeholder="Kosongkan agar AI membuat ide sendiri")
        avoid=st.text_input("Yang ingin dihindari (opsional)")
        c1,c2,c3=st.columns([2,2,1])
        with c1: category_choice=st.selectbox("Kategori",["Auto (mengikuti persentase)"]+list(CATEGORIES))
        with c2: model=st.selectbox("Model ClarioHub",MODELS,index=9)
        with c3: temp=st.slider("Kreativitas",0.4,1.2,0.95,0.05)
        saved_key = api_key()
        with st.expander("🔑 Koneksi API ClarioHub", expanded=not bool(saved_key)):
            base=st.text_input("Base URL",value=os.getenv("CLARIO_BASE_URL", BASE_URL_DEFAULT))
            key=st.text_input(
                "API key ClarioHub (opsional jika sudah disimpan di Secrets)",
                value="",
                type="password",
                help="Isi hanya jika belum menyimpan key di Streamlit Secrets."
            )
            if saved_key:
                st.success("API key terdeteksi dari Secrets/environment. Nilainya disembunyikan.")
            else:
                st.error("API key BELUM terdeteksi. Periksa Manage app → Settings → Secrets, lalu simpan dan Reboot app.")
                st.code('CLARIO_API_KEY = "API_KEY_ASLI_KAMU"\nCLARIO_BASE_URL = "https://clariohub.id/v1"', language="toml")
                st.caption("Pastikan nama variabel tepat CLARIO_API_KEY; jangan tempel key mentah tanpa nama variabel.")
            st.caption("Jangan masukkan placeholder dokumentasi atau membagikan key ke publik.")
        use_demo=st.checkbox("Demo mode (tanpa API)",value=not bool(key or saved_key))
        st.info("Gunakan frame akhir Scene 1 sebagai referensi visual Scene 2 di Google Flow jika fitur tersebut tersedia.")
        if st.button("✨ GENERATE STORY",type="primary",use_container_width=True):
            category=random.choices(list(CATEGORIES),weights=list(CATEGORIES.values()),k=1)[0] if category_choice.startswith("Auto") else category_choice
            actual_key=key.strip() or saved_key
            if use_demo:
                story=demo_story(category); is_demo=True
            else:
                if not actual_key or "YOUR_API_KEY_HERE" in actual_key:
                    st.error("Aplikasi tidak menemukan API key. Pastikan Secrets berisi CLARIO_API_KEY = \"key-asli\" lalu pilih Manage app → Reboot app. Jangan masukkan key ke chat."); st.stop()
                try:
                    with st.spinner(f"Menghubungi {model}..."):
                        story=ask_clario(base,actual_key,model,prompt_for(category,theme,history,avoid),temp)
                    if not all(x in story for x in ["title","premise","scene1","scene2","continuity_bible","youtube"]):
                        raise RuntimeError("Respons model belum lengkap. Coba model lain.")
                    is_demo=False
                except Exception as e:
                    st.error(f"Gagal membuat cerita: {e}")
                    st.info("Periksa API key, saldo/paket, model ID, dan Base URL. Model yang tersedia bisa berbeda sesuai paket.")
                    st.stop()
            st.session_state.story=story; st.session_state.category=category; st.session_state.demo=is_demo
            save_story(story,category); st.success("Cerita siap!")
        story=st.session_state.get("story")
        if story:
            st.divider(); st.header(story.get("title","Untitled")); st.caption(f"{story.get('category','')} · 16 detik · 9:16")
            st.write(story.get("premise",""))
            if st.session_state.get("demo"): st.warning("Demo mode menampilkan contoh tetap. Matikan Demo mode untuk menghasilkan cerita baru lewat API.")
            tabs=st.tabs(["🎥 Scene 1 · 0–8s","🎥 Scene 2 · 8–16s","🧍 Karakter & Continuity","💬 Dialog & Subtitle","📦 YouTube Pack"])
            for idx,scene_key in enumerate(["scene1","scene2"]):
                with tabs[idx]:
                    scene=story.get(scene_key,{})
                    st.subheader("Scene 1 — Hook + konflik" if idx==0 else "Scene 2 — lanjutan + payoff")
                    if idx==1: st.warning("Scene 2 harus dimulai dari frame akhir Scene 1. Gunakan frame referensi di Flow jika bisa.")
                    for beat in scene.get("timeline",[]):
                        st.markdown(f"**{beat.get('time','')}** · {beat.get('visual_action','')}")
                        for d in beat.get("dialogue",[]) or []: st.write(f"🗣️ {d.get('character','')}: “{d.get('line','')}”")
                        if beat.get("sound_effect"): st.caption("SFX: "+beat["sound_effect"])
                    st.write(scene.get("end_frame_description") if idx==0 else scene.get("opening_frame_description"))
                    prompt=scene.get("video_prompt","")
                    st.text_area(f"Prompt Google Flow — Scene {idx+1}",value=prompt,height=200,key=f"prompt{idx}")
                    st.download_button(f"Download Scene {idx+1} prompt",prompt,file_name=f"scene{idx+1}_prompt.txt")
            with tabs[2]:
                st.subheader("Character Bible"); st.json(story.get("characters",[]))
                st.subheader("Continuity Lock"); st.json(story.get("continuity_bible",{}))
            with tabs[3]:
                dialogue=[]
                for sn in (1,2):
                    for b in story.get(f"scene{sn}",{}).get("timeline",[]):
                        for d in b.get("dialogue",[]) or []: dialogue.append(f"Scene {sn} | {b.get('time','')} | {d.get('character','')}: {d.get('line','')}")
                st.text_area("Semua dialog", "\n".join(dialogue),height=140)
                subs=story.get("subtitle_lines",[]); st.json(subs)
                st.caption("Timing subtitle adalah perkiraan AI; periksa dan sinkronkan sebelum publikasi.")
                import re
                def stamp(sec):
                    sec=max(0,float(sec)); h=int(sec//3600); m=int(sec%3600//60); s=int(sec%60); ms=int((sec-int(sec))*1000)
                    return f"{h:02}:{m:02}:{s:02},{ms:03}"
                out=[]
                for i,x in enumerate(subs,1):
                    nums=re.findall(r"\d+(?:\.\d+)?",str(x.get("approx_time","")))
                    start=float(nums[0]) if nums else (0 if x.get("scene")==1 else 8)
                    end=float(nums[1]) if len(nums)>1 else start+1.5
                    out.append(f"{i}\n{stamp(start)} --> {stamp(end)}\n{x.get('text','')}\n")
                srt="\n".join(out); st.text_area("SRT draft",srt,height=170)
                st.download_button("Download subtitles .srt",srt,file_name="roblox_subtitles.srt")
            with tabs[4]:
                yt=story.get("youtube",{})
                st.text_input("Title",value=story.get("title",""),key="yt_title")
                st.text_area("Description",value=yt.get("description",""),key="yt_desc",height=100)
                st.write("Hashtags: "+" ".join(yt.get("hashtags",[])))
                st.write("Tags: "+", ".join(yt.get("tags",[])))
                pack=f"TITLE: {story.get('title','')}\\n\\nDESCRIPTION:\\n{yt.get('description','')}\\n\\nHASHTAGS: {' '.join(yt.get('hashtags',[]))}\\n\\nTAGS: {', '.join(yt.get('tags',[]))}\\n"
                st.download_button("Download YouTube pack",pack,file_name="youtube_pack.txt")
                st.json(story.get("quality_check",{}))
    elif page=="Story History":
        st.header("📚 Riwayat Cerita")
        if not history: st.info("Belum ada cerita tersimpan.")
        for x in history:
            with st.expander(f"#{x['id']} · {x['title']} · {x['category']} · {x['created']}"):
                st.write(x["premise"])
                st.download_button("Download story JSON",x["data"],file_name=f"story_{x['id']}.json",key=f"h{x['id']}")
    elif page=="Character & Prompt Rules":
        st.header("🧍 Character & Prompt Rules")
        st.markdown("""- Roblox Modern 3D blocky, map detail dan warna jelas, format 9:16.
- Desain avatar, pakaian, aksesori, skala, dan warna tidak boleh berubah.
- Scene 2 dimulai dari posisi terakhir Scene 1; tidak boleh reset, teleport, atau mengulang aksi.
- Jangan meminta AI video menulis teks. Tambahkan subtitle saat editing.
- Gunakan frame akhir Scene 1 sebagai referensi Scene 2 bila tersedia.
- Akhir Scene 2: dua detik terakhir menyelesaikan aksi dengan gerakan berkelanjutan, follow-through kecil, kamera terkendali, tanpa berhenti mendadak, freeze, pose kaku, atau aksi menggantung.""")
        st.table([{"Kategori":k,"Target":f"{v}%"} for k,v in CATEGORIES.items()])
    else:
        st.header("⚙️ Settings")
        st.write("Base URL default:"); st.code(BASE_URL_DEFAULT)
        st.write("Install dan jalankan:"); st.code("pip install -r requirements.txt\\nstreamlit run app.py",language="bash")
        st.write("Streamlit Cloud Secrets (direkomendasikan):")
        st.code('CLARIO_API_KEY = "API_KEY_ASLI_KAMU"\\nCLARIO_BASE_URL = "https://clariohub.id/v1"', language="toml")
        st.caption("Di Streamlit Cloud: Manage app → Settings → Secrets. Simpan sekali; aplikasi akan membacanya otomatis.")
        st.write("Linux/macOS/Termux:"); st.code("export CLARIO_API_KEY='API_KEY_ASLI'\\nexport CLARIO_BASE_URL='https://clariohub.id/v1'\\nstreamlit run app.py",language="bash")
        st.write("Windows PowerShell:"); st.code('$env:CLARIO_API_KEY="API_KEY_ASLI"\\n$env:CLARIO_BASE_URL="https://clariohub.id/v1"\\nstreamlit run app.py',language="powershell")
        st.warning("Jangan taruh API key asli di source code atau ZIP publik. Daftar model berasal dari screenshot; akses aktual tergantung paket.")
if __name__=="__main__":
    main()
