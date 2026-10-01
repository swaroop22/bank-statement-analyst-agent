"""
Command Line Interface for the Bank Statement Spending Analyst Agent.
Enables instant parsing and analysis of Google Drive links or local files.
"""

import sys
import os
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.pipeline import SpendingAnalysisPipeline

console = Console()


def print_rich_dashboard(report):
    """Render a visually stunning summary table directly in the terminal."""
    sym = report.currency_symbol or ("₹" if report.currency == "INR" else "$")
    # 1. Executive Summary Panel
    surplus_color = "green" if report.net_cash_flow >= 0 else "red"
    summary_text = (
        f"[bold cyan]Statement Period:[/bold cyan] {report.statement_period}\n"
        f"[bold cyan]Currency:[/bold cyan] {report.currency} ({sym})\n"
        f"[bold green]Total Inflow (Income/Deposits):[/bold green] {sym}{report.total_inflow:,.2f}\n"
        f"[bold red]Total Outflow (Actual Spending):[/bold red] {sym}{report.total_outflow:,.2f}\n"
        f"[bold {surplus_color}]Net Cash Flow:[/bold {surplus_color}] {sym}{report.net_cash_flow:,.2f}\n"
        f"[bold yellow]Savings / Retention Rate:[/bold yellow] {report.savings_rate:.1f}%\n"
        f"[dim]Accounts: {', '.join(report.account_sources)}[/dim]"
    )
    console.print(Panel(summary_text, title="📊 Executive Financial Summary", border_style="bold blue"))

    # 2. Category Table
    table = Table(title="💳 Expense Category Breakdown (100% Normalized)", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan", width=28)
    table.add_column("Total Spent", justify="right", style="green", width=14)
    table.add_column("% of Spend", justify="right", style="yellow", width=12)
    table.add_column("Top 3 Merchants / Drivers", style="dim", width=42)

    for b in report.category_breakdowns:
        drivers = ", ".join([f"{m} ({sym}{amt:,.2f})" for m, amt in b.top_merchants]) if b.top_merchants else "—"
        table.add_row(
            b.category,
            f"{sym}{b.total_spent:,.2f}",
            f"{b.percentage_of_spend:.1f}%",
            drivers
        )

    sum_pct = sum(b.percentage_of_spend for b in report.category_breakdowns)
    table.add_section()
    table.add_row(
        "[bold]Total Outflow[/bold]",
        f"[bold]{sym}{report.total_outflow:,.2f}[/bold]",
        f"[bold]{sum_pct:.0f}%[/bold]",
        "[dim]Guaranteed Exact 100% Sum[/dim]"
    )
    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Bank Statement Spending Analyst Agent - Autonomous Personal Finance & Extraction System"
    )
    parser.add_argument("--drive-url", type=str, help="Google Drive shared folder or file URL")
    parser.add_argument("--file", type=str, help="Path to single statement file (PDF, CSV, XLSX)")
    parser.add_argument("--dir", type=str, help="Directory containing multiple statement files")
    parser.add_argument("--password", type=str, default=None, help="Password for encrypted statement PDFs (e.g. SBI statements)")
    parser.add_argument("--output-md", type=str, default="spending_analysis_report.md", help="Path to save markdown report")
    parser.add_argument("--output-json", type=str, default=None, help="Path to save structured JSON report")

    args = parser.parse_args()

    pipeline = SpendingAnalysisPipeline()

    if args.drive_url:
        console.print(f"[bold cyan]Connecting to Google Drive URL:[/bold cyan] {args.drive_url}")
        report, txs, md_text, err = pipeline.process_google_drive(args.drive_url, password=args.password)
        if err:
            console.print(Panel(f"[bold red]Processing Notice / Decryption Required:[/bold red]\n{err}", border_style="red"))
            console.print("\n[yellow]💡 For SBI statements, please provide --password with your 11-digit account number, DOB (DDMMYYYY), or mobile+DOB.[/yellow]")
            sys.exit(1)
    elif args.file:
        console.print(f"[bold cyan]Processing local statement:[/bold cyan] {args.file}")
        report, txs, md_text = pipeline.process_files([args.file], password=args.password)
    elif args.dir:
        files = [
            os.path.join(args.dir, f) for f in os.listdir(args.dir)
            if f.lower().endswith(('.pdf', '.csv', '.xlsx', '.xls'))
        ]
        console.print(f"[bold cyan]Processing {len(files)} statements from directory:[/bold cyan] {args.dir}")
        report, txs, md_text = pipeline.process_files(files, password=args.password)
    else:
        # Default to samples directory if no args provided
        default_dir = os.path.join(os.path.dirname(__file__), "samples")
        if os.path.exists(default_dir):
            files = [
                os.path.join(default_dir, f) for f in os.listdir(default_dir)
                if f.lower().endswith(('.pdf', '.csv', '.xlsx', '.xls'))
            ]
            console.print(f"[bold green]No input provided. Running analysis on sample multi-account statements ({len(files)} files)...[/bold green]")
            report, txs, md_text = pipeline.process_files(files, password=args.password)
        else:
            parser.print_help()
            sys.exit(1)

    # Render terminal output
    print_rich_dashboard(report)

    # Print full Markdown report
    console.print("\n" + "="*80)
    console.print(md_text)
    console.print("="*80 + "\n")

    # Save to disk
    if args.output_md:
        with open(args.output_md, "w", encoding="utf-8") as f:
            f.write(md_text)
        console.print(f"✅ Markdown report saved to [bold green]{args.output_md}[/bold green]")

    if args.output_json:
        import json
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        console.print(f"✅ JSON report saved to [bold green]{args.output_json}[/bold green]")


if __name__ == "__main__":
    main()
