import os
from datetime import datetime

from dotenv import load_dotenv

# import psutil   #local ps stats
from paramiko import AutoAddPolicy, SSHClient  # python ssh lib

# load environment variables from .env file
load_dotenv()

username = os.getenv("username")
password = os.getenv("password")

host = ["RHEL2"]
port = 22

client = SSHClient()
client.set_missing_host_key_policy(AutoAddPolicy())
client.connect(host[0], username=username, password=password)

# ("top -bn1 | grep 'Cpu(s)'")
stdin, stdout, stderr = client.exec_command("cat /proc/loadavg")
if stdout.channel.recv_exit_status() == 0:
    print(f"STDOUT: {stdout.read().decode("utf8")}")
