
import os
import subprocess
import re

# ============================================================
# REQUIRED HARDWARE
# ============================================================

REQUIRED_HARDWARE = {
    "CPU_Count": 1,
    "TotalMemory": 96,          # GB
    "TotalDriveCount": 4,
    "NVMeDriveCount": 2,
    "OCP_Required_count": 5
}


# ============================================================
# CPU COUNT
# ============================================================

def get_cpu_count():
    result = subprocess.run(
        ["lscpu"],
        capture_output=True,
        text=True,
        check=True
    )

    for line in result.stdout.splitlines():
        if line.startswith("Socket(s):"):
            return int(line.split(":")[1].strip())

    return 0


# ============================================================
# MEMORY
# ============================================================

def get_total_memory_gb():
    with open("/proc/meminfo", "r") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return kb / (1024 * 1024)

    return 0


# ============================================================
# TOTAL DRIVE COUNT
# ============================================================

def get_drive_count():
    result = subprocess.run(
        ["lsblk", "-d", "-n", "-o", "TYPE"],
        capture_output=True,
        text=True,
        check=True
    )

    return sum(
        1 for line in result.stdout.splitlines()
        if line.strip() == "disk"
    )


# ============================================================
# NVMe DRIVE COUNT
# ============================================================

def get_nvme_drive_count():
    nvme_count = 0

    for device in os.listdir("/sys/block"):
        if device.startswith("nvme"):

            # nvme0n1, nvme1n1, etc. are actual NVMe namespaces
            # nvme0 is the controller and should not be counted
            if re.match(r"^nvme\d+n\d+$", device):
                nvme_count += 1

    return nvme_count


# ============================================================
# OCP NIC COUNT
# ============================================================

def get_ocp_nic_count():
    result = subprocess.run(
        ["lspci", "-nn"],
        capture_output=True,
        text=True,
        check=True
    )

    count = 0

    for line in result.stdout.splitlines():
        if re.search(
            r"Ethernet controller|Network controller",
            line,
            re.IGNORECASE
        ):
            count += 1

    return count


# ============================================================
# HARDWARE TEST
# ============================================================

def run_hardware_check():

    results = {}

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    actual_cpu = get_cpu_count()
    required_cpu = REQUIRED_HARDWARE["CPU_Count"]

    results["CPU"] = {
        "required": required_cpu,
        "actual": actual_cpu,
        "status": "PASS" if actual_cpu >= required_cpu else "FAIL"
    }

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    actual_memory = get_total_memory_gb()
    required_memory = REQUIRED_HARDWARE["TotalMemory"]

    results["Memory"] = {
        "required": required_memory,
        "actual": round(actual_memory, 2),
        "status": "PASS" if actual_memory >= required_memory else "FAIL"
    }

    # --------------------------------------------------------
    # TOTAL DRIVES
    # --------------------------------------------------------

    actual_drives = get_drive_count()
    required_drives = REQUIRED_HARDWARE["TotalDriveCount"]

    results["Drives"] = {
        "required": required_drives,
        "actual": actual_drives,
        "status": "PASS" if actual_drives >= required_drives else "FAIL"
    }

    # --------------------------------------------------------
    # NVMe DRIVES
    # --------------------------------------------------------

    actual_nvme = get_nvme_drive_count()
    required_nvme = REQUIRED_HARDWARE["NVMeDriveCount"]

    results["NVMe"] = {
        "required": required_nvme,
        "actual": actual_nvme,
        "status": "PASS" if actual_nvme >= required_nvme else "FAIL"
    }

    # --------------------------------------------------------
    # OCP NIC
    # --------------------------------------------------------

    actual_ocp = get_ocp_nic_count()
    required_ocp = REQUIRED_HARDWARE["OCP_Required_count"]

    results["OCP_NIC"] = {
        "required": required_ocp,
        "actual": actual_ocp,
        "status": "PASS" if actual_ocp >= required_ocp else "FAIL"
    }

    return results


# ============================================================
# DISPLAY RESULTS
# ============================================================

def display_results(results):

    print()
    print("========================================")
    print("       HARDWARE VALIDATION RESULTS")
    print("========================================")

    overall_pass = True

    for hardware, result in results.items():

        status = result["status"]

        if status == "FAIL":
            overall_pass = False

        print(
            f"{hardware:12} "
            f"Required: {result['required']} "
            f"Actual: {result['actual']} "
            f"Result: {status}"
        )

    print("========================================")

    if overall_pass:
        print("OVERALL RESULT: PASS")
    else:
        print("OVERALL RESULT: FAIL")

    print("========================================")

    return overall_pass


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    results = run_hardware_check()

    passed = display_results(results)

    # Exit code for automation
    if passed:
        exit(0)
    else:
        exit(1)