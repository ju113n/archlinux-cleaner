#!/usr/bin/env python3
"""
main.py

Interactive script for Arch Linux and derivatives.

Features:
  1) Displays explicitly installed packages (native + AUR/foreign)
  2) Displays orphaned packages (unrequired dependencies)
  3) Offers automatic removal of orphans (using -Rns)

Notes:
  - Requires pacman. yay, is optional.
  - AUR packages appear as "foreign" (pacman -Qm).
  - Uses sudo if not running as root.

Usage:
  python3 main.py
"""
import datetime
import os
import shutil
import subprocess
import sys
from typing import List


def fail(msg: str, code: int = 1) -> None:
    print(f"[error] {msg}")
    sys.exit(code)


def run(cmd: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            f'expac -t %Y-%m-%d \'%n;%d;%l\' $({cmd})',
            check=True,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        print(e.stderr.strip())
        fail(f"command failed: {' '.join(cmd)}")


def ensure_arch_like() -> None:
    if shutil.which("pacman") is None:
        fail("pacman not found. This script is for Arch Linux and derivatives.")
    if shutil.which("expac") is None:
        fail("expac not found. It shoud be installed as a mandatory dependency.")


def list_explicit_packages() -> tuple[List[tuple], List[tuple]]:
    """Return (native_explicit, foreign_explicit)."""
    # -Qqen: native explicit, -Qqem: foreign explicit
    native = [to_obj(l) for l in run("pacman -Qqen").stdout.strip().splitlines()]
    foreign = [to_obj(l) for l in run("pacman -Qqem").stdout.strip().splitlines()]

    return native, foreign


def list_orphans() -> List[tuple]:
    # -Qqdt: dependencies installed explicitly but not required by others (orphans)
    proc = run("pacman -Qqtd")

    if proc.returncode != 0:
        # pacman returns non-zero if no orphans are found
        return []

    return [to_obj(l) for l in proc.stdout.strip().splitlines()]


def to_obj(line: str) -> tuple[str, str, datetime.date]:
    pk, desc, date = line.split(";")

    return pk, desc, datetime.date.fromisoformat(date)


def print_list(title: str, items: List[tuple]) -> None:
    print("\n" + title)
    print("=" * len(title))
    if not items:
        print("(none)")
        return
    for i, obj in enumerate(sorted(items), 1):
        pk, desc, date = obj
        pk_str = BColors.BOLD + BColors.OKGREEN + pk + BColors.ENDC
        date_str = BColors.OKCYAN + date.strftime("%d %b. %Y") + BColors.ENDC
        desc_str = desc
        print(f"{i:3d}. {date_str} {pk_str:50} {desc_str}")
    print(f"\nTotal: {len(items)}")


def confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return ans in {"y", "yes", "o", "oui"}


def remove_orphans(pkgs: List[str]) -> None:
    if not pkgs:
        print("No orphan packages to remove.")
        return

    # Build pacman -Rns command
    base_cmd = 'pacman -Rns --noconfirm ' + ' '.join(pkgs)

    if os.geteuid() != 0:
        sudo = shutil.which("sudo")
        if sudo:
            cmd = sudo + ' ' + base_cmd
        else:
            cmd = None
            fail("insufficient privileges and 'sudo' not found. Please run as root.")
    else:
        cmd = base_cmd

    print("\nRemoving orphan packages:")
    print(" ", " ".join(pkgs))
    print()

    try:
        run(cmd)
    except subprocess.CalledProcessError:
        fail("removal failed.")


def main() -> None:
    ensure_arch_like()

    print("Checking pacman package database...\n")

    native, foreign = list_explicit_packages()

    print_list("Explicitly installed packages (native repositories)", native)
    print_list("Explicitly installed packages (AUR/foreign)", foreign)

    input("\nPress Enter to detect orphan packages")

    orphans = list_orphans()
    print_list("Orphan packages (unrequired dependencies)", orphans)

    if not orphans:
        print("\nNothing to clean. Your system has no orphans, congratulations.")
        return

    if confirm("\nDo you want to remove them automatically using 'pacman -Rns'?"):
        remove_orphans([pkg for pkg, _, _ in orphans])
    else:
        print("\nNo removal performed.")


class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
