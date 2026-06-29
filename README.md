# 🚀 LinkedIn Post Automator (Enterprise Edition)

A fully automated, terminal-based GUI (TUI) application to generate and schedule high-quality LinkedIn posts. 

Features:
- **Beautiful Terminal UI**: Built with Textual, featuring a fully interactive dashboard.
- **Dynamic Content**: Uses advanced AI prompting to avoid generic, robotic text.
- **Premium Infographics**: Automatically generates stunning glassmorphism comparison tables, scene cards, and tips lists.
- **SQLite Database**: Robust background queueing and draft saving.
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
git clone https://github.com/YOUR_USERNAME/linkedin-post-automator.git

# Navigate into the project folder
cd linkedin-post-automator
```
*(Make sure to replace `YOUR_USERNAME` with the actual GitHub username/URL if copying this directly!)*

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
Now, install all the required Python libraries for the app to function (like `textual` for the UI and `Pillow` for the graphics).

```bash
pip install -r requirements.txt
```

---

### Step 5: Configuration Setup
The app needs your API keys and LinkedIn session cookies to work. 

1. Copy the example configuration file to create your active config:
   ```bash
   cp example_config.json config.json
   ```

2. Open `config.json` in a text editor (like `nano config.json` or VSCode).

3. Fill in your credentials:
   - **`openrouter_api_key`**: Get one from [OpenRouter.ai](https://openrouter.ai/) (Used for text generation).
   - **`gemini_api_key`**: Get one from [Google AI Studio](https://aistudio.google.com/) (Optional, used as a fallback).
   - **`open_ai_key`**: Get one from [OpenAI](https://platform.openai.com/) (Optional).
   - **`li_at`** and **`JSESSIONID`**: These are your LinkedIn cookies required to post. 
     - Go to LinkedIn in your browser.
     - Open Developer Tools (F12) -> Application -> Cookies -> `www.linkedin.com`.
     - Copy the values for `li_at` and `JSESSIONID` and paste them into the config file.

---

### Step 6: Run the App! 🎉
Once everything is configured, simply run the main script to launch the beautiful terminal GUI:

```bash
python main.py
```

### 💡 Troubleshooting
- **Command Not Found**: If `python` doesn't work, try running `python3 main.py` instead.
- **Images looking weird?** Don't use the "Auto" generator if you only want infographics. Inside the app, change the Image Generator dropdown to **"Infographic Only"**.
