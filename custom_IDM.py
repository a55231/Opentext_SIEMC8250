#!/usr/bin/env python3

import os
import sys
import subprocess
import time
import getpass


# ============================================================
# CONFIGURATION
# ============================================================

IDM_FILE = "/home/silentdefense/C8250_0019711_CustBSU.pm"

IDRAC_IP = "192.168.1.100"

IDRAC_USER = "root"

RACADM = "racadm"


# ============================================================
# RUN COMMAND
# ============================================================

def run_command(command):

    print("\n$ " + " ".join(command))

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    return result


# ============================================================
# CHECK ROOT
# ============================================================

def check_root():

    if os.geteuid() != 0:
        print("ERROR: This script should be run as root.")
        print("Example:")
        print("    sudo python3 load_idm.py")
        sys.exit(1)


# ============================================================
# CHECK IDM FILE
# ============================================================

def check_idm_file():

    if not os.path.isfile(IDM_FILE):
        print(f"ERROR: IDM file not found:")
        print(f"    {IDM_FILE}")
        sys.exit(1)

    if not IDM_FILE.lower().endswith(".pm"):
        print("ERROR: IDM file must be a .pm file.")
        sys.exit(1)

    print(f"IDM file found: {IDM_FILE}")


# ============================================================
# CHECK RACADM
# ============================================================

def check_racadm():

    result = subprocess.run(
        ["which", RACADM],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("ERROR: racadm was not found.")
        print("Install the Dell RACADM utility first.")
        sys.exit(1)

    print(f"RACADM: {result.stdout.strip()}")


# ============================================================
# GET PASSWORD
# ============================================================

def get_password():

    return getpass.getpass(
        f"Enter iDRAC password for {IDRAC_USER}: "
    )


# ============================================================
# UPLOAD IDM
# ============================================================

def upload_idm(password):

    print("\n========================================")
    print("UPLOADING CUSTOM IDM")
    print("========================================")

    command = [
        RACADM,
        "-r",
        IDRAC_IP,
        "-u",
        IDRAC_USER,
        "-p",
        password,
        "update",
        "-f",
        IDM_FILE
    ]

    result = run_command(command)

    if result.returncode != 0:
        print("\nERROR: IDM upload failed.")
        return False

    print("\nIDM upload completed successfully.")

    return True


# ============================================================
# VIEW JOB QUEUE
# ============================================================

def get_job_queue(password):

    command = [
        RACADM,
        "-r",
        IDRAC_IP,
        "-u",
        IDRAC_USER,
        "-p",
        password,
        "jobqueue",
        "view"
    ]

    return run_command(command)


# ============================================================
# WAIT FOR IDM JOB
# ============================================================

def monitor_job(password, timeout_minutes=15):

    print("\n========================================")
    print("MONITORING IDM INSTALLATION")
    print("========================================")

    start_time = time.time()

    while True:

        result = get_job_queue(password)

        output = (
            result.stdout +
            result.stderr
        ).lower()

        if "completed" in output:
            print("\nIDM job completed.")
            return True

        if "failed" in output:
            print("\nERROR: IDM job failed.")
            return False

        if "error" in output:
            print("\nERROR detected in IDM job.")
            return False

        elapsed = time.time() - start_time

        if elapsed > timeout_minutes * 60:
            print("\nERROR: IDM job timed out.")
            return False

        print("\nIDM job still running...")
        time.sleep(30)


# ============================================================
# RESET iDRAC
# ============================================================

def reset_idrac(password):

    print("\n========================================")
    print("RESETTING iDRAC")
    print("========================================")

    response = input(
        "\nReset iDRAC now? Type RESET to continue: "
    )

    if response != "RESET":
        print("iDRAC reset skipped.")
        return

    command = [
        RACADM,
        "-r",
        IDRAC_IP,
        "-u",
        IDRAC_USER,
        "-p",
        password,
        "racreset",
        "soft"
    ]

    result = run_command(command)

    if result.returncode == 0:
        print("\niDRAC reset command submitted.")
    else:
        print("\nERROR: iDRAC reset failed.")


# ============================================================
# MAIN
# ============================================================

def main():

    print("========================================")
    print("      DELL CUSTOM IDM INSTALLER")
    print("========================================")

    check_root()
    check_idm_file()
    check_racadm()

    password = get_password()

    # Upload IDM
    if not upload_idm(password):
        sys.exit(1)

    # Monitor installation
    if not monitor_job(password):
        sys.exit(1)

    print("\n========================================")
    print("       IDM INSTALLATION COMPLETE")
    print("========================================")

    reset_idrac(password)

    print("\nIMPORTANT:")
    print("After iDRAC resets, Dell's installation procedure")
    print("requires a cold reboot and CSIOR to complete the")
    print("branding process.")


if __name__ == "__main__":
    main()