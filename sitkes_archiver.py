import os
import time
import requests
import subprocess
import shutil
import json
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import print as rprint

# --- Configuration & Styling ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = "https://api.github.com"
OUTPUT_DIR = r"C:\Users\Admin\Desktop\Morningstar\nexus_archives"
MAX_WORKERS = 5

console = Console()

def print_banner():
    banner_text = Text(r"""
   _____ _ _   _  __                    
  / ____(_) | | |/ /                    
 | (___  _| |_| ' / ___ ___             
  \___ \| | __|  < / _ \/ __|           
  ____) | | |_| . \  __/\__ \           
 |_____/|_|\__|_|\_\___||___/           
                                        
    S I T K E S   A R C H I V E R       
    Premium GitHub Backup Tool v9.0
    """, style="bold magenta")
    console.print(Panel(banner_text, border_style="magenta"))

def get_all_repositories(token):
    repos = []
    page = 1
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    with console.status("[bold green]Scanning GitHub Network...", spinner="dots"):
        while True:
            url = f"{BASE_URL}/user/repos?page={page}&per_page=100&affiliation=owner&visibility=all"
            try:
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    console.print(f"[bold red]![/bold red] Access Denied: {response.status_code}")
                    break
                
                data = response.json()
                if not data:
                    break
                
                repos.extend(data)
                page += 1
            except Exception as e:
                console.print(f"[bold red]![/bold red] Connection Error: {e}")
                break
    
    return repos

def clone_single_repo(repo, token, output_dir, progress, task_id):
    repo_name = repo['name']
    clone_url = repo['clone_url'].replace("https://", f"https://{token}@")
    target_path = os.path.join(output_dir, repo_name)
    
    if os.path.exists(target_path):
        progress.update(task_id, description=f"[yellow]Skipped[/yellow] {repo_name}", advance=1)
        return "skipped"

    try:
        subprocess.run(["git", "clone", clone_url, target_path], check=True, capture_output=True)
        progress.update(task_id, description=f"[cyan]Cloned[/cyan] {repo_name}", advance=1)
        return "success"
    except Exception as e:
        progress.update(task_id, description=f"[red]Failed[/red] {repo_name}", advance=1)
        return "failed"

def main():
    print_banner()

    if not GITHUB_TOKEN or "YOUR_GITHUB" in GITHUB_TOKEN:
        console.print("[bold red]CRITICAL ERROR:[/bold red] Missing Authentication Token.")
        return

    # 1. Fetch Repositories
    repos = get_all_repositories(GITHUB_TOKEN)
    if not repos:
        console.print("[bold yellow]No repositories found to archive.[/bold yellow]")
        return
    
    console.print(f"[bold white]Found {len(repos)} repositories aligned for extraction.[/bold white]")
    print()

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 2. Clone/Backup
    results = {"success": 0, "skipped": 0, "failed": 0}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task("[green]Archiving...", total=len(repos))
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_repo = {
                executor.submit(clone_single_repo, repo, GITHUB_TOKEN, OUTPUT_DIR, progress, task): repo 
                for repo in repos
            }
            
            for future in future_to_repo:
                res = future.result()
                results[res] += 1

    # 3. Final Report
    table = Table(title="Archival Summary", border_style="green")
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="white")
    
    table.add_row("Successfully Archived", str(results['success']))
    table.add_row("Previously Cached (Skipped)", str(results['skipped']))
    table.add_row("Failed", str(results['failed']))
    
    console.print(Panel(table, title="[bold green]Mission Complete[/bold green]", border_style="green"))
    console.print(f"[italic grey50]Archives stored in: {OUTPUT_DIR}[/italic grey50]")

if __name__ == "__main__":
    main()
