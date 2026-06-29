import os
import sys
import subprocess

SERVICE_TEMPLATE = """[Unit]
Description=LinkedIn Post Automator Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory={work_dir}
ExecStart={python_bin} {main_script} --daemon
Restart=on-failure
RestartSec=60
StandardOutput=append:{work_dir}/daemon.log
StandardError=append:{work_dir}/daemon.log

[Install]
WantedBy=default.target
"""

class ServiceManager:
    def __init__(self):
        self.service_name = "linkedin-automator.service"
        self.systemd_user_dir = os.path.expanduser("~/.config/systemd/user")
        self.service_path = os.path.join(self.systemd_user_dir, self.service_name)
        self.work_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.python_bin = os.path.join(self.work_dir, "venv", "bin", "python")
        self.main_script = os.path.join(self.work_dir, "main.py")

    def install(self):
        os.makedirs(self.systemd_user_dir, exist_ok=True)
        content = SERVICE_TEMPLATE.format(
            work_dir=self.work_dir,
            python_bin=self.python_bin,
            main_script=self.main_script
        )
        with open(self.service_path, "w") as f:
            f.write(content)
            
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", self.service_name], check=False)
        subprocess.run(["systemctl", "--user", "start", self.service_name], check=False)

    def uninstall(self):
        subprocess.run(["systemctl", "--user", "stop", self.service_name], check=False)
        subprocess.run(["systemctl", "--user", "disable", self.service_name], check=False)
        if os.path.exists(self.service_path):
            os.remove(self.service_path)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)

    def status(self) -> str:
        res = subprocess.run(
            ["systemctl", "--user", "status", self.service_name],
            capture_output=True, text=True
        )
        return res.stdout if res.stdout else res.stderr
