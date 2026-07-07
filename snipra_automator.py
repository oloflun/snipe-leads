import time
import os
from typing import List, Dict

import pyperclip
import typer
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from rich.prompt import Prompt, Confirm

STATE_FILE = ".snipra-auth-state.json"

app = typer.Typer(
    name="snipra-automation",
    help="Automate Snipra Email Studio for testing and quick iterations.",
    add_completion=False,
)
console = Console()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Launch interactive mode for Email Studio"
    ),
    email: str = typer.Option(None, help="Email for auto-login (used with --interactive)"),
    password: str = typer.Option(None, help="Password for auto-login (used with --interactive)"),
):
    """Main entrypoint. Supports --interactive for guided automation."""
    if interactive:
        interactive_mode(email=email, password=password)
        ctx.exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        ctx.exit()

ACTIONS = [
    "Kortare",
    "Skriv om",
    "Förbättra",
    "Personalisera",
    "Översätt",
    "A/B-varianter",
    "Uppföljning",
    "Analysera",
]

def get_playwright_context(p, headless: bool):
    """Get browser, context (with stored auth if available), and page."""
    browser = p.chromium.launch(headless=headless)
    context_args = {}
    if os.path.exists(STATE_FILE):
        context_args["storage_state"] = STATE_FILE
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page

def _get_editor_locators(page):
    """Locate the subject input and body textarea."""
    subject = page.locator("input[aria-label='Ämnesrad']")
    body = page.locator("textarea[aria-label='Mejltext']")
    return subject, body

def _find_action_button(page, label: str):
    """Find a refine button by its visible Swedish label."""
    return page.locator(f"button:has-text('{label}')")


def interactive_mode(
    url: str = "http://localhost:3000/emails",
    headless: bool = True,
    email: str = None,
    password: str = None,
):
    """Interactive mode: connect to Email Studio and let user choose actions one by one."""
    console.print("[bold blue]Starting interactive Email Studio automation...[/]")

    with sync_playwright() as p:
        browser, context, page = get_playwright_context(p, headless)

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            current_url = page.url
            is_login_page = "login" in current_url.lower() or page.get_by_text("Logga in").count() > 0 or page.locator('button[type="submit"]').count() > 0
            if is_login_page:
                if email and password:
                    console.print("[yellow]Redirected to login - attempting auto-login...[/]")
                    try:
                        page.locator('input[type="email"]').fill(email)
                        page.locator('input[type="password"]').fill(password)
                        page.locator('button[type="submit"]').click()
                        page.wait_for_url("**/emails**", timeout=15000)
                        # Save state after successful login
                        context.storage_state(path=STATE_FILE)
                        console.print(f"[green]Logged in and state saved to {STATE_FILE}[/]")
                    except Exception as e:
                        console.print(f"[red]Auto-login attempt failed: {e}[/]")
                        console.print("[yellow]Tip: Use demo mode to log in manually in visible browser.[/]")
                else:
                    console.print("[yellow]Redirected to login page (no credentials provided).[/]")
                    console.print("[yellow]For auto-login: python snipra_automator.py --interactive --email you@example.com --password yourpass[/]")
                    console.print("[yellow]Or run 'demo' to open visible browser and log in yourself first.[/]")
                    browser.close()
                    return
            # Wait for editor only if not on login
            page.wait_for_selector("textarea[aria-label='Mejltext']", timeout=15000)
            console.print("[green]Connected to Email Studio.[/]")

            subject, body = _get_editor_locators(page)

            while True:
                console.print("\n[bold]Available actions:[/]")
                for i, act in enumerate(ACTIONS, 1):
                    console.print(f"  {i}. {act}")
                console.print("  0. Quit / Exit interactive")

                choice = Prompt.ask(
                    "Select action number",
                    choices=[str(i) for i in range(len(ACTIONS) + 1)],
                    default="0",
                )

                if choice == "0":
                    break

                action = ACTIONS[int(choice) - 1]

                before_sub = subject.input_value()
                before_body = body.input_value()

                console.print(f"\n[cyan]Running:[/] {action} ...")
                btn = _find_action_button(page, action)
                if btn.count() == 0:
                    console.print("[red]Button not found![/]")
                    continue

                btn.click()

                try:
                    loading = page.locator("text=Agenten omskriver")
                    if loading.count() > 0:
                        loading.wait_for(state="hidden", timeout=15000)
                    else:
                        page.wait_for_timeout(2500)
                except PlaywrightTimeout:
                    console.print("[yellow]No loading indicator or timeout.[/]")

                after_sub = subject.input_value()
                after_body = body.input_value()

                changed = (after_sub != before_sub) or (after_body != before_body)
                status = "[green]✓ Changed[/]" if changed else "[yellow]No change (check LLM key?)[/]"

                console.print(Panel(f"[bold]New subject:[/]\n{after_sub}", title=f"After {action}", border_style="green"))
                console.print(Panel(f"[bold]New body (preview):[/]\n{after_body[:250]}...", title="Body", border_style="green"))
                console.print(status)

                if changed and Confirm.ask("Copy this result to clipboard?", default=False):
                    pyperclip.copy(f"Subject: {after_sub}\n\n{after_body}")
                    console.print("[green]Copied to clipboard![/]")

                if not Confirm.ask("Run another action?", default=True):
                    break

        except Exception as e:
            console.print(f"[red]Error during interactive session: {e}[/]")
        finally:
            browser.close()

    console.print("[bold]Interactive session ended.[/]")

def run_automation(
    url: str = "http://localhost:3000/emails",
    headless: bool = True,
    copy_last: bool = False,
    timeout: int = 30000,
    email: str = None,
    password: str = None,
) -> List[Dict]:
    """Core automation logic. Returns list of results for each action."""
    results = []

    with sync_playwright() as p:
        browser, context, page = get_playwright_context(p, headless)

        console.print(f"[bold]Navigating to[/] {url}")
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout)
        except PlaywrightTimeout:
            console.print("[red]Failed to load Email Studio. Is the dev server running?[/]")
            browser.close()
            return results

        # Handle auth redirect to login
        if "login" in page.url and email and password:
            console.print("[yellow]Redirected to login, attempting auto-login...[/]")
            try:
                page.locator('input[type="email"]').fill(email)
                page.locator('input[type="password"]').fill(password)
                page.locator('button[type="submit"]').click()
                page.wait_for_url("**/emails**", timeout=15000)
                # Save state after successful login
                context.storage_state(path=STATE_FILE)
                console.print(f"[green]Logged in and state saved to {STATE_FILE}[/]")
            except Exception as e:
                console.print(f"[red]Auto-login failed: {e}[/]")
                console.print("[yellow]Continuing anyway (may not reach editor).[/]")

        # Handle if on onboarding (after login with state)
        if "onboarding" in page.url:
            console.print("[yellow]On onboarding page, completing with dummy data...[/]")
            fields = {
                "product": "Testprodukt för automation",
                "targetAudience": "Småföretag i Sverige",
                "industries": "Tech, Konsult",
                "geography": "Sverige",
                "tone": "Professionell och hjälpsam",
                "offer": "Automatiserad leadgenerering",
                "cta": "Boka demo",
                "contactRoles": "VD, Marknadschef"
            }
            for name, value in fields.items():
                try:
                    inp = page.locator(f'input[name="{name}"], textarea[name="{name}"]')
                    if inp.count() > 0:
                        inp.fill(value)
                except:
                    pass
            submit = page.locator('button[type="submit"], button:has-text("Spara"), button:has-text("Fortsätt")')
            if submit.count() > 0:
                submit.first.click()
                page.wait_for_url("**/emails**", timeout=15000)
            context.storage_state(path=STATE_FILE)

        subject, body = _get_editor_locators(page)

        try:
            page.wait_for_selector("textarea[aria-label='Mejltext']", timeout=15000)
        except PlaywrightTimeout:
            console.print("[red]Email Studio editor not found on page.[/]")
            console.print(f"Current URL: {page.url}")
            console.print(f"Page title: {page.title()}")
            try:
                body_text = page.inner_text('body')[:300] if page.locator('body').count() > 0 else "no body"
                console.print(f"Body text sample: {body_text}")
            except:
                pass
            if "login" in page.url:
                console.print("[yellow]You are still on the login page. Provide --email and --password or log in manually first.[/]")
            browser.close()
            return results

        console.print("[green]Email Studio loaded.[/]\n")

        initial_subject = subject.input_value()
        initial_body = body.input_value()

        console.print(Panel(f"[bold]Initial Subject:[/]\n{initial_subject}", title="Before", border_style="blue"))
        console.print(Panel(f"[bold]Initial Body (truncated):[/]\n{initial_body[:200]}...", title="Before", border_style="blue"))

        for action in ACTIONS:
            console.print(f"\n[bold cyan]→ Running action:[/] {action}")

            btn = _find_action_button(page, action)
            if btn.count() == 0:
                console.print(f"  [red]Button '{action}' not found![/]")
                continue

            before_sub = subject.input_value()
            before_body = body.input_value()

            btn.click()

            # Wait for the "Agenten omskriver..." loading indicator (if present)
            try:
                loading = page.locator("text=Agenten omskriver")
                if loading.count() > 0:
                    loading.wait_for(state="hidden", timeout=15000)
                else:
                    page.wait_for_timeout(2500)
            except PlaywrightTimeout:
                console.print("  [yellow]Timed out waiting for update. Continuing...[/]")

            after_sub = subject.input_value()
            after_body = body.input_value()

            changed = (after_sub != before_sub) or (after_body != before_body)

            status = "[green]CHANGED[/]" if changed else "[yellow]NO CHANGE[/]"
            console.print(f"  Subject: {status}")
            console.print(f"  Body length: {len(after_body)} chars")

            results.append({
                "action": action,
                "changed": changed,
                "before_subject": before_sub,
                "after_subject": after_sub,
                "before_body": before_body,
                "after_body": after_body,
            })

            time.sleep(0.8)

        browser.close()

    # Summary table
    table = Table(title="Email Studio Automation Results")
    table.add_column("Action", style="cyan")
    table.add_column("Changed?", style="green")
    table.add_column("New Subject (preview)")

    for r in results:
        changed_str = "✓" if r["changed"] else "✗"
        preview = r["after_subject"][:70] + "..." if len(r["after_subject"]) > 70 else r["after_subject"]
        table.add_row(r["action"], changed_str, preview)

    console.print("\n")
    console.print(table)

    if copy_last and results:
        last = results[-1]
        text = f"Subject: {last['after_subject']}\n\n{last['after_body']}"
        pyperclip.copy(text)
        console.print("[green]Last result copied to clipboard![/]")

    return results

@app.command()
def run(
    url: str = typer.Option("http://localhost:3000/emails", help="Target Email Studio URL"),
    headless: bool = typer.Option(True, help="Run browser headless"),
    copy: bool = typer.Option(False, "--copy", help="Copy last result to clipboard"),
    email: str = typer.Option(None, help="Email for auto-login if redirected to login page"),
    password: str = typer.Option(None, help="Password for auto-login if redirected to login page"),
):
    """Run the Email Studio automation against a running dev server."""
    run_automation(url=url, headless=headless, copy_last=copy, email=email, password=password)

@app.command()
def demo(
    email: str = typer.Option(None, help="Email for auto-login if redirected"),
    password: str = typer.Option(None, help="Password for auto-login if redirected"),
):
    """Run with visible browser (headless=False) and copy result."""
    run_automation(headless=False, copy_last=True, email=email, password=password)


@app.command(name="interactive")
def interactive_cmd(
    url: str = typer.Option("http://localhost:3000/emails", help="Target Email Studio URL"),
    headless: bool = typer.Option(True, help="Run browser headless"),
    email: str = typer.Option(None, help="Email for auto-login if redirected"),
    password: str = typer.Option(None, help="Password for auto-login if redirected"),
):
    """Interactive mode: choose and run Email Studio actions one at a time."""
    interactive_mode(url=url, headless=headless, email=email, password=password)


@app.command()
def login(
    email: str = typer.Argument(..., help="Email to login with"),
    password: str = typer.Argument(..., help="Password"),
    url: str = typer.Option("http://localhost:3000", help="Base URL for the app"),
    headless: bool = typer.Option(True, help="Run browser headless"),
):
    """Perform login and save auth state (so future runs are 'logged in')."""
    with sync_playwright() as p:
        # IMPORTANT: login command MUST use a FRESH context (no storage_state)
        # so that middleware does not redirect /login away to dashboard.
        # Other commands (run, interactive) load state to stay "logged in".
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        login_url = f"{url}/login"
        console.print(f"[bold]Navigating to login at[/] {login_url}")
        try:
            page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeout:
            console.print("[red]Failed to load /login page. Is dev server running?[/]")
            browser.close()
            return

        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        current_url = page.url
        console.print(f"[dim]Landed at: {current_url}[/]")

        if "login" not in current_url.lower():
            console.print("[yellow]Did not land on /login (possible prior auth redirect). Proceeding may fail.[/]")

        # Robust locator: prefer type=, fallback to placeholder from LoginForm
        email_input = page.locator('input[type="email"], input[placeholder="du@bolag.se"]')
        pw_input = page.locator('input[type="password"], input[placeholder="••••••••"]')
        submit_btn = page.locator('button[type="submit"]')

        try:
            email_input.wait_for(state="visible", timeout=45000)
            console.print("[green]Login form inputs visible.[/]")
        except PlaywrightTimeout:
            console.print("[red]Email input never became visible.[/]")
            try:
                console.print(f"Current URL: {page.url}")
                console.print(f"Title: {page.title()}")
                # Dump available inputs for debugging
                ins = page.locator('input').all()
                console.print(f"Inputs on page: {len(ins)}")
                for i, inp in enumerate(ins[:5]):
                    ph = inp.get_attribute("placeholder") or ""
                    ty = inp.get_attribute("type") or ""
                    console.print(f"  input[{i}]: type={ty} placeholder={ph}")
            except:
                pass
            browser.close()
            return

        try:
            email_input.first.fill(email)
            pw_input.first.fill(password)
            submit_btn.first.click()

            # Wait for navigation away from login page (success) or to onboarding
            try:
                page.wait_for_url(lambda u: "/login" not in u, timeout=20000)
            except PlaywrightTimeout:
                page.wait_for_load_state("networkidle", timeout=15000)

            current = page.url
            console.print(f"[dim]After submit: {current}[/]")

            if "onboarding" in current.lower():
                console.print("[yellow]First time login - completing onboarding automatically...[/]")
                fields = {
                    "product": "Testprodukt för automation",
                    "targetAudience": "Småföretag i Sverige",
                    "industries": "Tech, Konsult",
                    "geography": "Sverige",
                    "tone": "Professionell och hjälpsam",
                    "offer": "Automatiserad leadgenerering",
                    "cta": "Boka demo",
                    "contactRoles": "VD, Marknadschef"
                }
                for name, value in fields.items():
                    try:
                        inp = page.locator(f'input[name="{name}"], textarea[name="{name}"]')
                        if inp.count() > 0:
                            inp.fill(value)
                    except:
                        pass
                submit = page.locator('button[type="submit"], button:has-text("Spara"), button:has-text("Fortsätt")')
                if submit.count() > 0:
                    submit.first.click()
                    try:
                        page.wait_for_url(lambda u: "/onboarding" not in u and "/login" not in u, timeout=15000)
                    except:
                        page.wait_for_timeout(3000)

            # Save fresh logged-in state
            context.storage_state(path=STATE_FILE)
            console.print(f"[green]✓ Logged in successfully! State saved to {STATE_FILE}[/]")
            console.print(f"[green]You can now run automation commands without re-logging in.[/]")
            console.print(f"[dim]Current location: {page.url}[/]")

        except Exception as e:
            console.print(f"[red]Login failed: {e}[/]")
            try:
                console.print(f"Current URL: {page.url}")
                console.print(f"Page title: {page.title()}")
                content = page.content()[:600]
                console.print(f"Page content sample: {content}")
            except:
                pass
        finally:
            browser.close()


if __name__ == "__main__":
    app()
