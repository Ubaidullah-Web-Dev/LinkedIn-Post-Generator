```text
    __    ___ 
   / /   /   |
  / /   / /| |
 / /___/ ___ |
/_____/_/  |_|
```

# 🚀 LinkedIn Post Automator (v2.5 Enterprise)

A fully automated, terminal-based GUI (TUI) application to generate and schedule high-quality LinkedIn posts. 

Features:
- **Beautiful Terminal UI**: Built with Textual, featuring a fully interactive dashboard and compact ASCII aesthetics.
- **Dynamic Content**: Uses advanced AI prompting to avoid generic, robotic text.
- **Premium Infographics (v2.5)**: A deterministic visual engine powered by Python PIL and NumPy. Features 7 robust templates (Quote Cards, Step Flows, Code Snippets, etc.) and 5 gorgeous color themes with frosted glassmorphism.
- **SQLite Database**: Robust background queueing, thread-safe WAL mode, and draft saving.
- **Config Hardening**: Secure secret management using `.env` files.
- **Multi-Model Support**: Failover system across OpenRouter, Gemini, OpenAI, and Pollinations.

---

## 🛠️ Beginner's Setup Guide (Linux)

Follow these steps from start to finish to get the app running on your machine.

### Step 1: Install Python and Git
Before you can run the app, you need Python and Git installed on your system. 

Open your terminal and run the command for your specific Linux distribution:

**For Ubuntu / Debian / Pop!_OS / Mint:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y
```

**For Arch Linux / Manjaro / EndeavourOS:**
```bash
sudo pacman -Syu python python-pip git
```

**For Fedora:**
```bash
sudo dnf install python3 python3-pip git
```

---

### Step 2: Clone the Repository
Download the project to your computer using Git:

```bash
# Clone the repository
git clone https://github.com/Ubaidullah-Web-Dev/LinkedIn-Post-Generator.git

# Navigate into the project folder
cd LinkedIn-Post-Generator
```

---

### Step 3: Set up a Virtual Environment
It's a Python best practice to install dependencies in an isolated "virtual environment" so they don't conflict with your system.

```bash
# Create a virtual environment named "venv"
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```
*Note: You must run `source venv/bin/activate` every time you open a new terminal to run the app.*

---

### Step 4: Install Dependencies
Now, install all the required Python libraries for the app to function (like `textual` for the UI, `Pillow` and `NumPy` for the graphics, and `python-dotenv` for secrets).

```bash
pip install -r requirements.txt
```

---

### Step 5: Configuration Setup (Secured via .env)
The app needs your API keys and LinkedIn session cookies to work. We use a `.env` file to keep these secure.

1. Create a `.env` file in the root of the project:
   ```bash
   touch .env
   ```

2. Open `.env` in a text editor (like `nano .env` or VSCode).

3. Fill in your credentials:
   ```env
   # Required for posting
   LI_AT=your_linkedin_li_at_cookie
   JSESSIONID=your_linkedin_jsessionid_cookie

   # Required for AI text generation (pick at least one)
   OPENROUTER_API_KEY=your_openrouter_key
   GEMINI_API_KEY=your_gemini_key
   OPENAI_API_KEY=your_openai_key
   ```
   
   *To get your LinkedIn cookies:*
   - Go to LinkedIn in your browser.
   - Open Developer Tools (F12) -> Application -> Cookies -> `www.linkedin.com`.
   - Copy the values for `li_at` and `JSESSIONID`.

*(Optional: You can still copy `example_config.json` to `config.json` to configure non-secret settings like your bio, websites, and default token limits).*

---

### Step 6: Run the App! 🎉
Once everything is configured, simply run the main script to launch the beautiful terminal GUI:

```bash
python main.py
```

### 💡 Troubleshooting
- **Command Not Found**: If `python` doesn't work, try running `python3 main.py` instead.
- **Images looking weird?** By default, the system uses the new deterministic Infographic engine (`template_only`). If you select `ai_only` or `hybrid`, the AI image generation might produce unpredictable results. Stick to the built-in templates for professional visuals!
