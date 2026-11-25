# Highlight Clip Maker

Video ka link do. Sabse zyada dekha gaya hissa (most replayed) dhundh kar chhota clip banta hai,
saath me bolne wale shabdon ka caption bhi.

## Folder me kya hai

| File / folder | Kaam |
|---|---|
| `docs/` | Website ka front-page (GitHub Pages yahi dikhata hai) |
| `docs/config.js` | Server ka link yahan daalte hain (Tarika 2 ke liye) |
| `app.py` | Server (Python) jo website ke liye clip banata hai |
| `clipper.py` | Clip banane ka asli kaam (video kaatna, caption) |
| `clip_cli.py` | Command-line se clip banata hai (GitHub Actions yahi chalata hai) |
| `.github/workflows/clip.yml` | GitHub Actions: GitHub par hi clip banane ka button |
| `Dockerfile` | Server ko online (Render) daalne ke liye |

## GitHub par kaise daalein

1. github.com par free account banao.
2. Upar **+** > **New repository**. Naam do (jaise `highlight-clip-maker`), **Public** chuno, **Create repository**.
3. **uploading an existing file** par click karo. Is folder ki **saari files aur folders** drag karke daalo
   (`.github` folder bhi, wo chhupa hua ho sakta hai) aur **Commit changes** dabao.

## Tarika 1: GitHub Actions (server ki zaroorat nahi)

GitHub khud tumhare liye clip banata hai.

1. Apni repository me **Actions** tab kholo.
2. Left me **Clip banao** chuno, phir **Run workflow** dabao.
3. Video ka link daalo, caption / vertical chuno, **Run workflow** dabao.
4. 3 se 10 minute baad us run ko kholo. Neeche **Artifacts** me `highlight-clip` mil jayega. Download karo (zip hoga, andar video aur `.srt`).

Dhyan do: GitHub ke servers ko bhi YouTube kabhi kabhi block karta hai (neeche dekho).

## Tarika 2: Website (GitHub Pages) + server

GitHub Pages sirf front-page dikha sakta hai. Video process karne ke liye ek server chahiye.

1. **Server Render par daalo:** render.com par **New > Web Service**, apni repository jodo, **Docker** chuno, deploy karo.
   Render ka link milega, jaise `https://meri-site.onrender.com`.
2. **Link config me daalo:** repository me `docs/config.js` kholo, **edit** karke likho:
   `window.API_URL = "https://meri-site.onrender.com";` aur commit karo.
3. **Pages chalu karo:** repository **Settings > Pages**. *Source:* **Deploy from a branch**, *Branch:* **main**, folder **/docs**, **Save**.
4. 1-2 minute me tumhari site `https://TUMHARA-NAAM.github.io/REPO-NAAM/` par khul jayegi.

(Seedha `https://meri-site.onrender.com` kholne par bhi wahi website khulti hai, kyunki server `docs/` dikhata hai.)

## Apne computer par chalao

1. Python aur **ffmpeg** install karo (ffmpeg.org).
2. Folder me CMD kholo: `pip install -r requirements.txt`
3. `python app.py` phir browser me `http://localhost:5000`

Ya sirf command se: `python clip_cli.py --url "LINK" --length 45 --captions`

## Settings (environment variables)

| Naam | Matlab | Default |
|---|---|---|
| `WHISPER_MODEL` | `tiny` / `base` / `small` (bada = behtar caption, zyada memory) | `base` |
| `ALLOWED_HOSTS` | kaunsi sites allowed hain, comma se alag. Sab ke liye `*` | `youtube.com,youtu.be,twitch.tv` |
| `CORS_ORIGIN` | GitHub Pages ka link (jaise `https://naam.github.io`), safe rakhne ke liye | `*` |
| `MAX_CLIP_SECONDS` | clip ki sabse badi lambai | `120` |
| `MAX_ACTIVE_JOBS` | ek saath kitne clip ban sakte hain | `2` |
| `YT_COOKIES` | cookies.txt ka path | khaali |

## Sach batayein to (limits)

- **YouTube block:** GitHub aur Render jaise servers ko YouTube aksar "Sign in to confirm you're not a bot" bol ke rok deta hai. Aisa ho to cookies chahiye (`cookies.txt`, apne browser se export kiya hua) aur wo bhi hamesha kaam nahi karta. Ye is code ki galti nahi, YouTube ki rok hai.
- **Live stream:** abhi chal rahi live ka clip nahi banta. Live khatam hone ke baad (jab recording ban jaye) link do.
- **Free server:** kam memory aur dheemi speed. Caption banana lamba ho sakta hai. Zyada logon ke liye paid plan chahiye.
- **Apni cookies kabhi public repository me mat daalo.** `.gitignore` me `cookies.txt` pehle se hai.
- **Copyright:** doosron ke video ka clip upload karne se pehle permission ya credit ka dhyan rakho.
