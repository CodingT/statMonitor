import logging
import os
from datetime import datetime

import paramiko
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("username")
password = os.getenv("password")
hosts = ["RHEL2"]


# Set up logging with time stemp
logging.basicConfig(
    filename="remote_stats.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)


def execute_remote_command(client, command, timeout=30):
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if error:
            print(f"Command error: {error}")
            return None
        try:
            return float(output)
        except ValueError:
            print(f"Invalid output format: {output}")
            return None
    except Exception as e:
        print(f"Command execution failed: {str(e)}")
        return None


def get_remote_stats(hostname, username, password):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=username, password=password, timeout=10)

        # Get current CPU (1-second measurement)
        current_cpu = execute_remote_command(
            client, 'python3 -c "import psutil; print(psutil.cpu_percent(interval=1))"'
        )

        # Get daily CPU average using sar
        daily_avg_cpu = execute_remote_command(
            client,
            '''bash -c "sar -u -s $(date +%H:%M:%S -d 'today 00:00') | awk '/Average:/ {print 100 - \\$NF}'"''',
        )

        # Get current RAM usage (free + buffers/cache calculation)
        current_ram = execute_remote_command(
            client,
            'python3 -c "import psutil; print(psutil.virtual_memory().percent)"',
        )

        # Get daily average RAM usage using sar
        daily_avg_ram = execute_remote_command(
            client,
            '''bash -c "sar -r -s $(date +%H:%M:%S -d 'today 00:00') | awk '/Average:/ {print ((\\$3 - \\$2)/\\$3) * 100}'"''',
        )

        # Get disk usage for root (/)
        disk_root = execute_remote_command(
            client,
            '''python3 -c "import psutil; disk_root = psutil.disk_usage('/'); print(disk_root.percent)"''',
        )

        # Get disk usage for /home
        disk_home = execute_remote_command(
            client,
            '''python3 -c "import psutil; disk_home = psutil.disk_usage('/home'); print(disk_home.percent)"''',
        )

        # Get disk usage for /var
        disk_var = execute_remote_command(
            client,
            '''python3 -c "import psutil; disk_var = psutil.disk_usage('/var'); print(disk_var.percent)"''',
        )

        # Get disk usage for /tmp (optional)
        disk_tmp = execute_remote_command(
            client,
            '''python3 -c "import psutil; disk_tmp = psutil.disk_usage('/tmp'); print(disk_tmp.percent)"''',
        )

        # Current and avg network load
        current_network_load = execute_remote_command(
            client,
            '''bash -c "sar -n DEV 1 1 | grep 'wlp1s0' | tail -n 1 | awk '{print \\$9}'"''',
        )

        daily_avg_network_load = execute_remote_command(
            client,
            '''bash -c "sar -n DEV -s $(date +%H:%M:%S -d 'today 00:00') | grep 'wlp1s0' | awk '{sum += \\$9; count++} END {print sum/count}'"''',
        )

        return (
            current_cpu,
            daily_avg_cpu,
            current_ram,
            daily_avg_ram,
            disk_root,
            disk_home,
            disk_var,
            disk_tmp,
            current_network_load,
            daily_avg_network_load,
        )

    except Exception as e:
        print(f"Connection failed: {str(e)}")
        return None, None, None, None, None, None, None
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    for host in hosts:
        print(f"{host} Checking remote statistics...\n")

        # Get stats
        (
            current_cpu,
            daily_avg_cpu,
            current_ram,
            daily_avg_ram,
            disk_root,
            disk_home,
            disk_var,
            disk_tmp,
            current_network_load,
            daily_avg_network_load,
        ) = get_remote_stats(host, username, password)

        log_message = f"Results for {host}:\n"
        print(f"Results:")
        # Results output
        if current_cpu is not None and daily_avg_cpu is not None:
            print(
                f"Current CPU Usage: {current_cpu:.1f}%   Daily Average CPU Usage: {daily_avg_cpu:.2f}%"
            )
            log_message += f"Current CPU Usage: {current_cpu:.1f}%   Daily Average CPU Usage: {daily_avg_cpu:.2f}%\n"
        else:
            print("Failed to get CPU usage statistics")
            log_message += "Failed to get CPU usage statistics\n"

        if current_ram is not None and daily_avg_ram is not None:
            print(
                f"Current RAM Usage: {current_ram:.1f}%  Daily Average RAM Usage: {daily_avg_ram:.2f}%"
            )
            log_message += f"Current RAM Usage: {current_ram:.1f}%  Daily Average RAM Usage: {daily_avg_ram:.2f}%\n"
        else:
            print("Failed to get RAM usage statistics")
            log_message += "Failed to get RAM usage statistics\n"

        if disk_root is not None:
            print(
                f"Disk Usage: Root: {disk_root}% Home: {disk_home}% Var: {disk_var}% Tmp: {disk_tmp}%"
            )
            log_message += f"Disk Usage: Root: {disk_root}% Home: {disk_home}% Var: {disk_var}% Tmp: {disk_tmp}%\n"
        else:
            print("Failed to get Disk usage statistics")
            log_message += "Failed to get Disk usage statistics\n"

        if current_network_load is not None or daily_avg_network_load is not None:
            print(f"Current Network Utilization: {current_network_load}%")
            print(f"Daily Average Network Utilization: {daily_avg_network_load}%")
            log_message += f"Current Network Utilization: {current_network_load}%  Daily Average Network Utilization: {daily_avg_network_load}%\n"
        else:
            print("Failed to get Network statistics")
            log_message += "Failed to get Disk usage statistics\n"

        logging.info(log_message)
