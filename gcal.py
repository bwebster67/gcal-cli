#!/usr/bin/env python3
import datetime
import os.path
import argparse
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes: Read/Write access is needed for 'add'
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_service():
    """Handles authentication and returns the API service."""
    creds = None
    base_path = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_path, 'token.json')
    creds_path = os.path.join(base_path, 'credentials.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def cmd_add(service, args):
    """Adds an event using QuickAdd (Natural Language Processing)."""
    text = " ".join(args.text) # Join list into a single string
    print(f"Adding: '{text}'...")
    
    event = service.events().quickAdd(
        calendarId='primary',
        text=text
    ).execute()
    
    print(f"✅ Created event: {event.get('summary')}")
    print(f"   Link: {event.get('htmlLink')}")

def cmd_next(service, args):
    """Prints the single next upcoming event."""
    now = datetime.datetime.now(datetime.UTC).isoformat()
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=1, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print("No upcoming events found.")
    else:
        print_event(events[0], prefix="⏭️  NEXT: ")

def cmd_today(service, args):
    """Prints all remaining events for today."""
    now = datetime.datetime.now()
    # Calculate end of today (UTC is tricky, this uses local machine time logic roughly)
    end_of_day = datetime.datetime.now().replace(hour=23, minute=59, second=59)
    
    now_iso = now.isoformat() + 'Z'
    
    # We fetch slightly more to filter, or just fetch next 10 and filter visually
    # Correct way: pass timeMax. 
    # Quick way for a script: Fetch next 10, stop printing if date changes.
    
    print(f"📅 Agenda for Today ({datetime.date.today()}):")
    print("-" * 40)
    
    events_result = service.events().list(
        calendarId='primary', timeMin=now_iso,
        maxResults=20, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print("No events found.")
        return

    today_str = datetime.date.today().isoformat()
    
    count = 0
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        # Check if the event starts today (simple string check on YYYY-MM-DD)
        if start.startswith(today_str):
            print_event(event)
            count += 1
    
    if count == 0:
        print("Nothing left for today! 🎉")

def print_event(event, prefix=""):
    start = event['start'].get('dateTime', event['start'].get('date'))
    summary = event['summary']
    
    # Parse time for cleaner display
    try:
        dt = datetime.datetime.fromisoformat(start)
        time_str = dt.strftime("%I:%M %p")
    except ValueError:
        time_str = "All Day"

    # ANSI Colors: \033[96m is Cyan, \033[0m is Reset
    print(f"{prefix}\033[96m[{time_str}]\033[0m {summary}")

def main():
    parser = argparse.ArgumentParser(description="CLI Google Calendar Tool")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Subcommand: add
    parser_add = subparsers.add_parser('add', help='Add an event via natural language')
    parser_add.add_argument('text', nargs='+', help='Event description (e.g. "Dinner at 7pm")')

    # Subcommand: next
    parser_next = subparsers.add_parser('next', help='Show the immediate next event')

    # Subcommand: today
    parser_today = subparsers.add_parser('today', help='Show remaining events for today')

    args = parser.parse_args()
    
    try:
        service = get_service()
        if args.command == 'add':
            cmd_add(service, args)
        elif args.command == 'next':
            cmd_next(service, args)
        elif args.command == 'today':
            cmd_today(service, args)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
