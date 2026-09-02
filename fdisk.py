#!/usr/bin/env python3

import subprocess
import sys
import os


# ============================================================
# CONFIGURATION
# ============================================================

DRIVES = [
    "/dev/sdb",
    "/dev/sdc",
    "/dev/sdd",
    "/dev/sde"
]


# ============================================================
# RUN COMMAND
# ============================================================

def run_command(command):
    print(f"\n> {' '.join(command)}")

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"ERROR: Command failed with exit code {result.returncode}")
        sys.exit(1)

    return result.stdout


# ============================================================
# CHECK ROOT
# ============================================================

def check_root():
    if os.geteuid() != 0:
        print("ERROR: This script must be run as root.")
        print("Run:")
        print("    sudo python3 diskpart.py")
        sys.exit(1)


# ============================================================
# CHECK DRIVE
# ============================================================

def check_drive(drive):

    if not os.path.exists(drive):
        print(f"ERROR: Drive does not exist: {drive}")
        sys.exit(1)

    if not os.path.exists(f"/sys/block/{os.path.basename(drive)}"):
        print(f"ERROR: {drive} is not a block device.")
        sys.exit(1)

    print(f"Found drive: {drive}")


# ============================================================
# GET DRIVE SIZE
# ============================================================

def get_drive_size(drive):

    output = run_command([
        "lsblk",
        "-dn",
        "-o",
        "SIZE",
        drive
    ])

    return output.strip()


# ============================================================
# PREPARE DRIVE
# ============================================================

def prepare_drive(drive):

    print("\n" + "=" * 60)
    print(f"Preparing {drive}")
    print("=" * 60)

    check_drive(drive)

    size = get_drive_size(drive)

    print(f"Drive size: {size}")

    # Remove filesystem signatures
    run_command([
        "wipefs",
        "--all",
        "--force",
        drive
    ])

    # Create GPT partition table
    run_command([
        "parted",
        "-s",
        drive,
        "mklabel",
        "gpt"
    ])

    # Create one partition using entire drive
    run_command([
        "parted",
        "-s",
        drive,
        "mkpart",
        "primary",
        "0%",
        "100%"
    ])

    # Tell Linux to reread partition table
    run_command([
        "partprobe",
        drive
    ])

    print(f"\nSUCCESS: {drive} prepared.")


# ============================================================
# MAIN
# ============================================================

def main():

    check_root()

    if len(DRIVES) != 4:
        print("ERROR: Exactly 4 drives must be configured.")
        sys.exit(1)

    print("=" * 60)
    print("Linux Disk Preparation")
    print("=" * 60)

    print("\nDrives to be modified:")

    for drive in DRIVES:
        print(f"  {drive}")

    print("\nWARNING:")
    print("ALL PARTITION INFORMATION ON THESE DRIVES WILL BE ERASED.")

    response = input("\nType ERASE to continue: ")

    if response != "ERASE":
        print("Operation cancelled.")
        sys.exit(0)

    for drive in DRIVES:
        prepare_drive(drive)

    print("\n" + "=" * 60)
    print("ALL 4 DRIVES HAVE BEEN PREPARED")
    print("=" * 60)

    run_command([
        "lsblk",
        "-o",
        "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT"
    ])


if __name__ == "__main__":
    main()