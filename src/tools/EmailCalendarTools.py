import subprocess
from typing import Optional

from langchain_core.tools import tool


MACOS_CLIENT_ALIASES = {"macos", "mail", "apple_mail", "apple mail", "calendar", "apple_calendar", "apple calendar"}


@tool
def read_unread_emails_tool(limit: int = 10, email_client: str = "macos") -> str:
    """Read unread email messages from the user's email client. Currently supports macOS Mail."""
    if _normalize_client(email_client) != "macos":
        return _unsupported_client_message(email_client, "email")

    message_limit = _bounded_int(limit, default=10, minimum=1, maximum=50)
    script = """
on run argv
    set messageLimit to (item 1 of argv) as integer
    tell application "Mail"
        set unreadMessages to messages of inbox whose read status is false
        set unreadCount to count of unreadMessages
        if unreadCount is 0 then return "No unread messages found in the inbox."

        if unreadCount < messageLimit then set messageLimit to unreadCount
        set outputText to "Unread emails found: " & unreadCount & linefeed & linefeed

        repeat with messageIndex from 1 to messageLimit
            set theMessage to item messageIndex of unreadMessages
            set subjectText to subject of theMessage as string
            set senderText to sender of theMessage as string
            set dateText to date received of theMessage as string
            set contentText to content of theMessage as string
            if (length of contentText) > 2500 then set contentText to text 1 thru 2500 of contentText

            set outputText to outputText & "Email " & messageIndex & linefeed
            set outputText to outputText & "From: " & senderText & linefeed
            set outputText to outputText & "Subject: " & subjectText & linefeed
            set outputText to outputText & "Received: " & dateText & linefeed
            set outputText to outputText & "Body:" & linefeed & contentText & linefeed & linefeed
        end repeat

        return outputText
    end tell
end run
""".strip()
    return _run_osascript(script, args=[str(message_limit)])


@tool
def search_emails_tool(
    query: str,
    limit: int = 10,
    mailbox: str = "inbox",
    email_client: str = "macos",
) -> str:
    """Search email messages by sender, subject, or body text. Currently supports macOS Mail."""
    if _normalize_client(email_client) != "macos":
        return _unsupported_client_message(email_client, "email")

    if not query.strip():
        return "Cannot search email without a non-empty query."

    message_limit = _bounded_int(limit, default=10, minimum=1, maximum=50)
    mailbox_name = "sent" if mailbox.lower().strip() == "sent" else "inbox"
    script = """
on run argv
    set queryText to item 1 of argv
    set messageLimit to (item 2 of argv) as integer
    set mailboxName to item 3 of argv
    set outputText to ""
    set matchedCount to 0
    set scannedCount to 0

    tell application "Mail"
        if mailboxName is "sent" then
            set sourceMessages to messages of sent mailbox
        else
            set sourceMessages to messages of inbox
        end if

        repeat with theMessage in sourceMessages
            set scannedCount to scannedCount + 1
            if scannedCount > 250 then exit repeat

            set subjectText to subject of theMessage as string
            set senderText to sender of theMessage as string
            set dateText to date received of theMessage as string
            try
                set contentText to content of theMessage as string
            on error
                set contentText to ""
            end try

            if subjectText contains queryText or senderText contains queryText or contentText contains queryText then
                set matchedCount to matchedCount + 1
                if (length of contentText) > 1800 then set contentText to text 1 thru 1800 of contentText

                set outputText to outputText & "Email " & matchedCount & linefeed
                set outputText to outputText & "From: " & senderText & linefeed
                set outputText to outputText & "Subject: " & subjectText & linefeed
                set outputText to outputText & "Received: " & dateText & linefeed
                set outputText to outputText & "Body:" & linefeed & contentText & linefeed & linefeed

                if matchedCount >= messageLimit then exit repeat
            end if
        end repeat
    end tell

    if matchedCount is 0 then return "No matching emails found in " & mailboxName & " for: " & queryText
    return "Matching emails found: " & matchedCount & linefeed & linefeed & outputText
end run
""".strip()
    return _run_osascript(script, args=[query, str(message_limit), mailbox_name])


@tool
def draft_email_reply_tool(
    to: str,
    subject: str,
    body: str,
    email_client: str = "macos",
    cc: Optional[str] = None,
) -> str:
    """Create a draft email reply. This tool drafts only; it does not send email."""
    if _normalize_client(email_client) != "macos":
        return _unsupported_client_message(email_client, "email")

    if not _has_email_address(to):
        return "Cannot create an email draft without at least one valid recipient email address."
    if not subject.strip():
        return "Cannot create an email draft without a subject."
    if not body.strip():
        return "Cannot create an email draft without a body."

    script = """
on run argv
    set toText to item 1 of argv
    set subjectText to item 2 of argv
    set bodyText to item 3 of argv
    set ccText to item 4 of argv

    tell application "Mail"
        set newMessage to make new outgoing message with properties {subject:subjectText, content:bodyText, visible:true}
        tell newMessage
            repeat with addressText in my splitAddresses(toText)
                if addressText is not "" then make new to recipient at end of to recipients with properties {address:addressText}
            end repeat

            if ccText is not "" then
                repeat with addressText in my splitAddresses(ccText)
                    if addressText is not "" then make new cc recipient at end of cc recipients with properties {address:addressText}
                end repeat
            end if
        end tell
        activate
    end tell

    return "Draft email created in Apple Mail with subject: " & subjectText
end run

on splitAddresses(addressText)
    set AppleScript's text item delimiters to ","
    set addressItems to text items of addressText
    set AppleScript's text item delimiters to ""
    return addressItems
end splitAddresses
""".strip()
    return _run_osascript(script, args=[to, subject, body, cc or ""])


@tool
def check_calendar_availability_tool(
    start_datetime: str,
    end_datetime: str,
    calendar_client: str = "macos",
    calendar_name: Optional[str] = None,
) -> str:
    """Check calendar availability between two date-times. Prefer ISO 8601 strings with timezone."""
    if _normalize_client(calendar_client) != "macos":
        return _unsupported_client_message(calendar_client, "calendar")

    if not start_datetime.strip() or not end_datetime.strip():
        return "Cannot check availability without both a start date-time and an end date-time."

    script = """
function run(argv) {
    const startDate = new Date(argv[0]);
    const endDate = new Date(argv[1]);
    const calendarName = argv[2];

    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
        return "Invalid date-time input. Use ISO 8601, for example 2026-06-01T09:00:00+10:00.";
    }
    if (endDate <= startDate) {
        return "The end date-time must be after the start date-time.";
    }

    const Calendar = Application("Calendar");
    const calendar = findCalendar(Calendar, calendarName);
    if (!calendar) {
        return "Calendar not found: " + calendarName;
    }

    const conflicts = [];
    const events = calendar.events();
    for (const event of events) {
        try {
            const eventStart = event.startDate();
            const eventEnd = event.endDate();
            if (eventStart < endDate && eventEnd > startDate) {
                conflicts.push({
                    title: event.summary(),
                    start: eventStart.toString(),
                    end: eventEnd.toString()
                });
            }
        } catch (error) {
        }
    }

    if (conflicts.length === 0) {
        return "Available. No calendar conflicts found between " + startDate.toString() + " and " + endDate.toString() + ".";
    }

    let output = "Busy. Calendar conflicts found:\\n\\n";
    for (const conflict of conflicts) {
        output += "- " + conflict.title + " from " + conflict.start + " to " + conflict.end + "\\n";
    }
    return output;
}

function findCalendar(Calendar, calendarName) {
    const calendars = Calendar.calendars();
    if (!calendarName) {
        return calendars[0];
    }

    for (const calendar of calendars) {
        if (calendar.name() === calendarName) {
            return calendar;
        }
    }
    return null;
}
""".strip()
    return _run_osascript(script, language="JavaScript", args=[start_datetime, end_datetime, calendar_name or ""])


@tool
def read_calendar_events_tool(
    briefing_date: str,
    calendar_client: str = "macos",
    calendar_name: Optional[str] = None,
) -> str:
    """Read calendar events for a date. Use briefing_date as YYYY-MM-DD."""
    if _normalize_client(calendar_client) != "macos":
        return _unsupported_client_message(calendar_client, "calendar")

    if not briefing_date.strip():
        return "Cannot read calendar events without a date. Use YYYY-MM-DD."

    script = """
function run(argv) {
    const requestedDate = argv[0];
    const calendarName = argv[1];
    const bounds = dayBounds(requestedDate);
    if (!bounds) {
        return "Invalid date input. Use YYYY-MM-DD, for example 2026-06-04.";
    }

    const Calendar = Application("Calendar");
    const calendar = findCalendar(Calendar, calendarName);
    if (!calendar) {
        return "Calendar not found: " + calendarName;
    }

    const matches = [];
    const events = calendar.events();
    for (const event of events) {
        try {
            const eventStart = event.startDate();
            const eventEnd = event.endDate();
            if (eventStart < bounds.end && eventEnd > bounds.start) {
                matches.push({
                    title: event.summary(),
                    start: eventStart.toString(),
                    end: eventEnd.toString(),
                    location: event.location()
                });
            }
        } catch (error) {
        }
    }

    if (matches.length === 0) {
        return "No calendar events found for " + requestedDate + ".";
    }

    matches.sort((a, b) => new Date(a.start) - new Date(b.start));
    let output = "Calendar events for " + requestedDate + ":\\n\\n";
    for (const match of matches) {
        output += "- " + match.title + " from " + match.start + " to " + match.end;
        if (match.location) {
            output += " at " + match.location;
        }
        output += "\\n";
    }
    return output;
}

function dayBounds(value) {
    const dateOnly = /^(\\d{4})-(\\d{2})-(\\d{2})$/.exec(value);
    if (dateOnly) {
        const start = new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]));
        const end = new Date(start);
        end.setDate(start.getDate() + 1);
        return {start: start, end: end};
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return null;
    }

    const start = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
    const end = new Date(start);
    end.setDate(start.getDate() + 1);
    return {start: start, end: end};
}

function findCalendar(Calendar, calendarName) {
    const calendars = Calendar.calendars();
    if (!calendarName) {
        return calendars[0];
    }

    for (const calendar of calendars) {
        if (calendar.name() === calendarName) {
            return calendar;
        }
    }
    return null;
}
""".strip()
    return _run_osascript(script, language="JavaScript", args=[briefing_date, calendar_name or ""])


@tool
def create_calendar_event_tool(
    title: str,
    start_datetime: str,
    end_datetime: str,
    calendar_client: str = "macos",
    notes: str = "",
    location: str = "",
    calendar_name: Optional[str] = None,
) -> str:
    """Create a calendar event. Prefer ISO 8601 date-times with timezone."""
    if _normalize_client(calendar_client) != "macos":
        return _unsupported_client_message(calendar_client, "calendar")

    if not title.strip():
        return "Cannot create a calendar event without a title."
    if not start_datetime.strip() or not end_datetime.strip():
        return "Cannot create a calendar event without both a start date-time and an end date-time."

    script = """
function run(argv) {
    const title = argv[0];
    const startDate = new Date(argv[1]);
    const endDate = new Date(argv[2]);
    const notes = argv[3];
    const location = argv[4];
    const calendarName = argv[5];

    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
        return "Invalid date-time input. Use ISO 8601, for example 2026-06-01T09:00:00+10:00.";
    }
    if (endDate <= startDate) {
        return "The end date-time must be after the start date-time.";
    }

    const Calendar = Application("Calendar");
    const calendar = findCalendar(Calendar, calendarName);
    if (!calendar) {
        return "Calendar not found: " + calendarName;
    }

    const conflicts = findConflicts(calendar, startDate, endDate);
    if (conflicts.length > 0) {
        let output = "Calendar event was not created because the requested time conflicts with existing events:\\n\\n";
        for (const conflict of conflicts) {
            output += "- " + conflict.title + " from " + conflict.start + " to " + conflict.end + "\\n";
        }
        return output;
    }

    const eventProperties = {
        summary: title,
        startDate: startDate,
        endDate: endDate,
        description: notes
    };
    if (location) {
        eventProperties.location = location;
    }

    const newEvent = Calendar.Event(eventProperties);
    calendar.events.push(newEvent);
    return "Calendar event created in " + calendar.name() + ": " + title + " from " + startDate.toString() + " to " + endDate.toString() + ".";
}

function findConflicts(calendar, startDate, endDate) {
    const conflicts = [];
    const events = calendar.events();
    for (const event of events) {
        try {
            const eventStart = event.startDate();
            const eventEnd = event.endDate();
            if (eventStart < endDate && eventEnd > startDate) {
                conflicts.push({
                    title: event.summary(),
                    start: eventStart.toString(),
                    end: eventEnd.toString()
                });
            }
        } catch (error) {
        }
    }
    return conflicts;
}

function findCalendar(Calendar, calendarName) {
    const calendars = Calendar.calendars();
    if (!calendarName) {
        return calendars[0];
    }

    for (const calendar of calendars) {
        if (calendar.name() === calendarName) {
            return calendar;
        }
    }
    return null;
}
""".strip()
    return _run_osascript(
        script,
        language="JavaScript",
        args=[title, start_datetime, end_datetime, notes, location, calendar_name or ""],
    )


@tool
def find_unanswered_emails_tool(days: int = 3, limit: int = 10, email_client: str = "macos") -> str:
    """Find potential unanswered sent emails older than a number of days. Currently supports macOS Mail."""
    if _normalize_client(email_client) != "macos":
        return _unsupported_client_message(email_client, "email")

    day_count = _bounded_int(days, default=3, minimum=1, maximum=90)
    message_limit = _bounded_int(limit, default=10, minimum=1, maximum=50)
    script = """
on run argv
    set dayCount to (item 1 of argv) as integer
    set messageLimit to (item 2 of argv) as integer
    set cutoffDate to (current date) - (dayCount * 24 * 60 * 60)
    set outputText to ""
    set matchedCount to 0

    tell application "Mail"
        set sentMessages to messages of sent mailbox
        repeat with theMessage in sentMessages
            try
                set sentDate to date sent of theMessage
            on error
                set sentDate to date received of theMessage
            end try

            if sentDate < cutoffDate then
                set matchedCount to matchedCount + 1
                set subjectText to subject of theMessage as string
                set contentText to content of theMessage as string
                if (length of contentText) > 1400 then set contentText to text 1 thru 1400 of contentText

                set recipientText to ""
                repeat with recipientItem in to recipients of theMessage
                    set recipientText to recipientText & address of recipientItem & ", "
                end repeat

                set outputText to outputText & "Sent email " & matchedCount & linefeed
                set outputText to outputText & "To: " & recipientText & linefeed
                set outputText to outputText & "Subject: " & subjectText & linefeed
                set outputText to outputText & "Sent: " & (sentDate as string) & linefeed
                set outputText to outputText & "Body:" & linefeed & contentText & linefeed & linefeed

                if matchedCount >= messageLimit then exit repeat
            end if
        end repeat
    end tell

    if matchedCount is 0 then return "No sent emails older than " & dayCount & " days were found."
    return "Potential follow-up candidates older than " & dayCount & " days. Review before drafting; this local Mail tool cannot prove that every item is unanswered." & linefeed & linefeed & outputText
end run
""".strip()
    return _run_osascript(script, args=[str(day_count), str(message_limit)])


def _normalize_client(client: Optional[str]) -> str:
    if not client:
        return "macos"

    normalized = client.lower().strip().replace("-", "_")
    if normalized in MACOS_CLIENT_ALIASES:
        return "macos"

    return normalized


def _unsupported_client_message(client: str, client_type: str) -> str:
    return (
        f"The {client_type} client '{client}' is not wired into the local tools yet. "
        "This workflow is provider-shaped, so Gmail or Outlook/Microsoft 365 tools can be added later with "
        "LangChain's Gmail or Office365 toolkits."
    )


def _bounded_int(value: int, default: int, minimum: int, maximum: int) -> int:
    try:
        bounded_value = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, bounded_value))


def _has_email_address(value: str) -> bool:
    return any("@" in address and "." in address for address in value.split(","))


def _run_osascript(script: str, language: Optional[str] = None, args: Optional[list[str]] = None) -> str:
    command = ["osascript"]
    if language:
        command.extend(["-l", language])
    command.extend(["-e", script])
    command.extend(args or [])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=45,
        )
    except FileNotFoundError:
        return "Could not run osascript. These local tools require macOS."
    except subprocess.TimeoutExpired:
        return "The macOS automation request timed out."

    if result.returncode != 0:
        error_text = result.stderr.strip() or result.stdout.strip()
        return (
            "The macOS automation request failed. "
            "Make sure Terminal or your Python runner has permission to control Mail and Calendar. "
            f"Details: {error_text}"
        )

    return result.stdout.strip() or "The macOS automation request completed."
