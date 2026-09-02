#!/usr/bin/env python3

import subprocess
import sys
import os
import re


# ============================================================
# CONFIGURATION
# ============================================================

NVME_RAID_DEVICE = "/dev/md0"
NVME_RAID_SIZE_GB = 480

SAS_RAID_VD_NAME = "SAS_RAID5"
SAS_RAID_SIZE_GB = 6706

# NVMe devices
NVME_DRIVES = [
    "/dev/nvme0n1",
    "/dev/nvme1n1"
]

# SAS physical drives
# IMPORTANT:
# Replace these with the actual drive IDs reported by storcli.
SAS_DRIVES = [
    "252:0",
    "252:1",
    "252:2",
    "252:3"
]

STORCLI = "/usr/local/bin/storcli64"


# ============================================================
# RUN COMMAND
# ============================================================

def run_command(command, check=True):

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

    if check and result.returncode != 0:
        print(f"ERROR: Command failed with exit code {result.returncode}")
        sys.exit(1)

    return result


# ============================================================
# ROOT CHECK
# ============================================================

def check_root():

    if os.geteuid() != 0:
        print("ERROR: This script must be run as root.")
        print("Run:")
        print("    sudo python3 create_raid.py")
        sys.exit(1)


# ============================================================
# CHECK REQUIRED PROGRAMS
# ============================================================

def check_programs():

    if not os.path.exists(STORCLI):
        print(f"ERROR: storcli not found: {STORCLI}")
        sys.exit(1)

    result = subprocess.run(
        ["which", "mdadm"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("ERROR: mdadm is not installed.")
        print("Install it with:")
        print("    apt install mdadm")
        sys.exit(1)


# ============================================================
# SHOW CURRENT STORAGE
# ============================================================

def show_storage():

    print("\n========================================")
    print("CURRENT STORAGE")
    print("========================================")

    run_command([
        "lsblk",
        "-o",
        "NAME,SIZE,TYPE,MODEL,SERIAL"
    ])

    print("\n========================================")
    print("STORCLI PHYSICAL DRIVES")
    print("========================================")

    run_command([
        STORCLI,
        "/c0/eall/sall",
        "show"
    ])


# ============================================================
# VERIFY NVMe DRIVES
# ============================================================

def verify_nvme_drives():

    print("\n========================================")
    print("VERIFYING NVMe DRIVES")
    print("========================================")

    for drive in NVME_DRIVES:

        if not os.path.exists(drive):
            print(f"ERROR: NVMe drive not found: {drive}")
            sys.exit(1)

        print(f"Found: {drive}")

    # Make sure they are NVMe devices
    for drive in NVME_DRIVES:

        if not re.match(r"^/dev/nvme\d+n\d+$", drive):
            print(f"ERROR: Not an NVMe namespace: {drive}")
            sys.exit(1)


# ============================================================
# VERIFY SAS DRIVES
# ============================================================

def verify_sas_drives():

    print("\n========================================")
    print("VERIFYING SAS DRIVES")
    print("========================================")

    print("Configured SAS drives:")

    for drive in SAS_DRIVES:
        print(f"    {drive}")

    print("\nVerify these IDs match the four intended SAS HDDs.")


# ============================================================
# CREATE NVMe RAID 1
# ============================================================

def create_nvme_raid1():

    print("\n========================================")
    print("CREATING NVMe RAID 1")
    print("========================================")

    print("Drives:")

    for drive in NVME_DRIVES:
        print(f"    {drive}")

    print(f"\nRAID device: {NVME_RAID_DEVICE}")
    print(f"Requested size: {NVME_RAID_SIZE_GB} GB")

    # Stop existing array if present
    run_command(
        ["mdadm", "--stop", NVME_RAID_DEVICE],
        check=False
    )

    # Clear old RAID metadata
    for drive in NVME_DRIVES:

        run_command(
            ["mdadm", "--zero-superblock", "--force", drive],
            check=False
        )

    # Create RAID 1
    run_command([
        "mdadm",
        "--create",
        NVME_RAID_DEVICE,
        "--level=1",
        "--raid-devices=2",
        *NVME_DRIVES
    ])

    print("\nNVMe RAID 1 created.")

    # Show status
    run_command([
        "mdadm",
        "--detail",
        NVME_RAID_DEVICE
    ])


# ============================================================
# CREATE SAS RAID 5
# ============================================================

def create_sas_raid5():

    print("\n========================================")
    print("CREATING SAS RAID 5")
    print("========================================")

    print("SAS drives:")

    for drive in SAS_DRIVES:
        print(f"    {drive}")

    print(f"\nVirtual Drive: {SAS_RAID_VD_NAME}")
    print(f"Requested size: {SAS_RAID_SIZE_GB} GB")

    # --------------------------------------------------------
    # Create RAID 5
    # --------------------------------------------------------

    command = [
        STORCLI,
        "/c0",
        "add",
        "vd",
        "r5",
        "name=" + SAS_RAID_VD_NAME,
        "drives=" + ",".join(SAS_DRIVES),
        "size=" + str(SAS_RAID_SIZE_GB) + "GB"
    ]

    run_command(command)

    print("\nSAS RAID 5 created.")

    # Show virtual drives
    run_command([
        STORCLI,
        "/c0/vall",
        "show"
    ])


# ============================================================
# VERIFY RESULTS
# ============================================================

def verify_results():

    print("\n========================================")
    print("VERIFYING RAID CONFIGURATION")
    print("========================================")

    print("\n--- NVMe RAID ---")

    run_command([
        "cat",
        "/proc/mdstat"
    ])

    print("\n--- NVMe RAID Detail ---")

    run_command([
        "mdadm",
        "--detail",
        NVME_RAID_DEVICE
    ])

    print("\n--- SAS RAID ---")

    run_command([
        STORCLI,
        "/c0/vall",
        "show"
    ])

    print("\n--- Linux Block Devices ---")

    run_command([
        "lsblk",
        "-o",
        "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT"
    ])


# ============================================================
# CONFIRMATION
# ============================================================

def get_confirmation():

    print()
    print("============================================================")
    print("WARNING: RAID CREATION WILL DESTROY DATA")
    print("============================================================")

    print("\nNVMe drives:")
    for drive in NVME_DRIVES:
        print(f"    {drive}")

    print("\nSAS drives:")
    for drive in SAS_DRIVES:
        print(f"    {drive}")

    print("\nThe configuration will create:")
    print("    2 x NVMe  -> RAID 1  -> ~480 GB")
    print("    4 x SAS   -> RAID 5  -> ~6706 GB")

    print("\nALL EXISTING DATA ON THESE DRIVES MAY BE DESTROYED.")

    response = input(
        "\nType CREATE-RAID to continue: "
    )

    if response != "CREATE-RAID":
        print("Operation cancelled.")
        sys.exit(0)


# ============================================================
# MAIN
# ============================================================

def main():

    check_root()
    check_programs()

    show_storage()

    verify_nvme_drives()
    verify_sas_drives()

    get_confirmation()

    create_nvme_raid1()
    create_sas_raid5()

    verify_results()

    print("\n========================================")
    print("RAID CONFIGURATION COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()