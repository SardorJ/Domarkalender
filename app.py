from flask import Flask, Response
from icalendar import Calendar, Event, Alarm
from datetime import datetime, timedelta
import pytz
import csv

app = Flask(__name__)

@app.route("/sardor-jurayev.ics")
def serve_calendar():
    cal = Calendar()
    cal.add("prodid", "-//Sardor Jurayevs Domarschema//")
    cal.add("version", "2.0")

    with open("schema_fogis.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            event = Event()
            start_str = f"{row['Datum']} {row['Tid']}"
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            start_dt = pytz.timezone("Europe/Stockholm").localize(start_dt)

            event.add("summary", f"{row['Lag 1']} vs {row['Lag 2']}")
            event.add("dtstart", start_dt)
            event.add("dtend", start_dt + timedelta(hours=2))  # 2 timmar lång match
            event.add("location", row["Arena"])
            event.add("description", f"Match mellan {row['Lag 1']} och {row['Lag 2']} på {row['Arena']}")

            # 🔔 Notis – 1 dag före match
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", "Påminnelse: Match imorgon!")
            alarm.add("trigger", timedelta(days=-1))
            event.add_component(alarm)

            cal.add_component(event)

    return Response(cal.to_ical(), mimetype="text/calendar")

if __name__ == "__main__":
    app.run(port=5050)
