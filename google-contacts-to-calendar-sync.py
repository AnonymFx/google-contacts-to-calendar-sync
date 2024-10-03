import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the required API scopes
SCOPES = ['https://www.googleapis.com/auth/contacts.readonly', 'https://www.googleapis.com/auth/calendar']


def authenticate_google():
    """Authenticate the user using OAuth 2.0 and return the Google Contacts and Calendar services."""
    creds = None
    # Check if token.json exists and load the credentials
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If no valid credentials, request new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials to token.json for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Build the Contacts and Calendar services
    contacts_service = build('people', 'v1', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)

    return contacts_service, calendar_service


def get_birthdays_and_anniversaries(contacts_service):
    """Fetches birthdays and anniversaries from all pages of Google Contacts."""
    anniversaries = []
    page_token = None  # To track pagination

    while True:
        # Fetch a page of contacts
        results = contacts_service.people().connections().list(
            resourceName='people/me',
            pageToken=page_token,  # Pass the page token if it's available
            pageSize=100,  # Fetch 100 contacts per request (max)
            personFields='names,birthdays,events'  # Specify the fields we need
        ).execute()

        connections = results.get('connections', [])

        for person in connections:
            names = person.get('names', [])
            name = names[0]['displayName'] if names else "Unnamed"

            # Get birthdays
            birthdays_data = person.get('birthdays', [])
            for birthday in birthdays_data:
                date = birthday.get('date')
                if not date.get('year'):
                    date['year'] = 2024
                if date:
                    birthday_entry = {
                        'name': name,
                        'type': 'Birthday',
                        'date': date
                    }
                    anniversaries.append(birthday_entry)

            # Get anniversaries (stored in "events" field)
            events_data = person.get('events', [])
            for event in events_data:
                type = event.get('type').capitalize()
                date = event.get('date')
                if date:
                    anniversary_entry = {
                        'name': name,
                        'type': type,
                        'date': date
                    }
                    anniversaries.append(anniversary_entry)

        # Check if there is another page of results
        page_token = results.get('nextPageToken')
        if not page_token:
            break  # Exit the loop when there are no more pages

    return anniversaries


def create_calendar_event(service, event_name, event_date, calendar_id='primary'):
    """Create a calendar event on Google Calendar."""
    event = {
        'summary': event_name,
        'start': {
            'date': event_date,
        },
        'end': {
            'date': event_date,
        },
        'recurrence': [
            'RRULE:FREQ=YEARLY'
        ]
    }
    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"Event created: {event.get('htmlLink')}")


def transfer_to_calendar(birthdays, anniversaries, calendar_service):
    """Transfer birthdays and anniversaries to Google Calendar."""
    for birthday in birthdays:
        date = f"{birthday['date']['year']}-{birthday['date']['month']:02d}-{birthday['date']['day']:02d}"
        create_calendar_event(calendar_service, f"Birthday: {birthday['name']}", date)

    for anniversary in anniversaries:
        date = f"{anniversary['date']['year']}-{anniversary['date']['month']:02d}-{anniversary['date']['day']:02d}"
        create_calendar_event(calendar_service, f"Anniversary: {anniversary['name']}", date)


if __name__ == '__main__':
    # Authenticate and get Google Contacts and Calendar services
    contacts_service, calendar_service = authenticate_google()

    # Get birthdays and anniversaries from Google Contacts
    anniversaries = get_birthdays_and_anniversaries(contacts_service)

    print(anniversaries)

    # Transfer these events to Google Calendar
    # transfer_to_calendar(birthdays, anniversaries, calendar_service)
