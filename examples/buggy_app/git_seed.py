"""
Seed realistic Git commits for AIBD demonstration.
"""

import subprocess
import os

def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

def seed_git():
    if not os.path.exists(".git"):
        run("git init")
        run("git config user.name 'DevOps Bot'")
        run("git config user.email 'devops@example.com'")

    run("git add .")
    run("git commit -m 'Initial project structure and aidbg architecture' --allow-empty")

    # Commit simulating pool change
    run("git commit -m 'Change database worker concurrency from 4 -> 16 and update pool' --allow-empty")

    # Commit simulating auth controller changes
    run("git commit -m 'Refactor login endpoint and database user lookup' --allow-empty")
    print("Git repository seeded with realistic commits successfully.")

if __name__ == "__main__":
    seed_git()
