import logging
import os
from datetime import datetime

import paramiko
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("username")
password = os.getenv("password")
hosts = ["RHEL2"]


def execute_remote_command(client, command, timeout=30):
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if error:
            logging.error(f"Command error: {error}")
            return None
        return output
    except Exception as e:
        logging.error(f"Command execution failed: {str(e)}")
        return None


def get_remote_cron_stats(hostname, username, password):
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=username, password=password, timeout=10)

        # Get user's cron jobs
        job_list = execute_remote_command(client, "crontab -l 2>/dev/null")

        # Get cron service status
        job_status = execute_remote_command(
            client,
            "systemctl is-active crond || service cron status | grep -E 'Active|running'",
        )

        # Get detailed execution info for each job
        detailed_jobs = []
        if job_list:
            for job in job_list.split("\n"):
                if job.strip() and not job.startswith("#"):
                    parts = job.split()
                    if len(parts) >= 6:
                        cmd = " ".join(parts[5:])
                        # Get last execution info from cron log
                        last_execution = execute_remote_command(
                            client, f"grep -a 'CMD ({cmd})' /var/log/cron | tail -1"
                        )
                        # Get success/failure status
                        status = "Unknown"
                        exit_status = execute_remote_command(
                            client,
                            f"grep -a 'CMD ({cmd})' /var/log/cron | grep -o 'exit status [0-9]\\+' | tail -1",
                        )
                        if exit_status:
                            status = (
                                "Success"
                                if "exit status 0" in exit_status
                                else "Failed"
                            )

                        # Get execution time
                        execution_time = "Never"
                        if last_execution:
                            execution_time = last_execution.split("(")[0].strip()

                        detailed_jobs.append(
                            {
                                "schedule": " ".join(parts[:5]),
                                "command": cmd,
                                "last_execution": execution_time,
                                "status": status,
                            }
                        )

        return {
            "user_cron_jobs": detailed_jobs,
            "cron_service_status": job_status,
        }

    except Exception as e:
        logging.error(f"Connection failed: {str(e)}")
        return None
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    for host in hosts:
        print(f"{host} Checking remote cron jobs...\n")

        # Get cron jobs stats
        cron_stats = get_remote_cron_stats(host, username, password)

        if cron_stats:
            print("=== User Cron Jobs ===")
            if cron_stats["user_cron_jobs"]:
                for job in cron_stats["user_cron_jobs"]:
                    print(f"\nSchedule: {job['schedule']}")
                    print(f"Command: {job['command']}")
                    print(f"Last Execution: {job['last_execution']}")
                    print(f"Status: {job['status']}")
                    print("-" * 50)
            else:
                print("No user cron jobs")

            print("\n=== Cron Service Status ===")
            print(cron_stats["cron_service_status"])
