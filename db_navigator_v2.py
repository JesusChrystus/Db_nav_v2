import requests
import time
from rich.console import Console
from rich.live import Live
from rich.table import Table

API_BASE_URL = "https://v6.db.transport.rest"


def search_station(station_name):
    try:
        response = requests.get(f"{API_BASE_URL}/stations", params={"query": station_name, "limit": 5})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei der Sendersuche: {e}")
        return None


def get_departures(station_id):
    try:
        response = requests.get(f"{API_BASE_URL}/stations/{station_id}/departures", params={"duration": 120})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Abfahrten: {e}")
        return None


def get_journeys(from_station_id, to_station_id):
    try:
        response = requests.get(f"{API_BASE_URL}/journeys", params={"from": from_station_id, "to": to_station_id})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Fahrten: {e}")
        return None


def generate_departures_table(departures):
    if not departures or 'departures' not in departures:
        return "Keine Abfahrtsinformationen verfügbar."

    table = Table(title="Abfahrten")
    table.add_column("Zeit", style="cyan")
    table.add_column("Zug")
    table.add_column("Richtung")
    table.add_column("Gleis")
    table.add_column("Verspätung (min)", style="red")

    for dep in departures['departures']:
        when = dep.get('when')
        if when:
            parsed_time = time.strptime(when, '%Y-%m-%dT%H:%M:%S%z')
            departure_time = time.strftime('%H:%M', parsed_time)
        else:
            departure_time = "N/A"

        delay = dep.get('delay')
        delay_minutes = int(delay / 60) if delay is not None else 0

        table.add_row(
            departure_time,
            dep['line']['name'],
            dep['direction'],
            dep.get('platform', 'N/A'),
            str(delay_minutes) if delay_minutes > 0 else ""
        )
    return table


def generate_journeys_table(journeys):
    if not journeys or 'journeys' not in journeys:
        return "Keine Fahrtinformationen verfügbar."

    table = Table(title="Fahrten")
    table.add_column("Abfahrt", style="cyan")
    table.add_column("Ankunft", style="cyan")
    table.add_column("Umstiege")
    table.add_column("Dauer (min)")
    table.add_column("Produkte")

    for journey in journeys['journeys']:
        departure_leg = journey['legs'][0]
        arrival_leg = journey['legs'][-1]

        departure_iso = departure_leg['departure']
        arrival_iso = arrival_leg['arrival']

        departure_time = time.strftime('%H:%M', time.strptime(departure_iso, '%Y-%m-%dT%H:%M:%S%z'))
        arrival_time = time.strftime('%H:%M', time.strptime(arrival_iso, '%Y-%m-%dT%H:%M:%S%z'))

        transfers = len(journey['legs']) - 1
        
        duration_seconds = time.mktime(time.strptime(arrival_iso, '%Y-%m-%dT%H:%M:%S%z')) - time.mktime(time.strptime(departure_iso, '%Y-%m-%dT%H:%M:%S%z'))
        duration_minutes = duration_seconds / 60

        products = ", ".join([leg['line']['product'] for leg in journey['legs']])

        table.add_row(
            departure_time,
            arrival_time,
            str(transfers),
            str(int(duration_minutes)),
            products
        )
    return table


def select_station(prompt_text):
    station_name = input(prompt_text)
    stations = search_station(station_name)
    if not stations:
        print("Keine Bahnhöfe gefunden.")
        return None

    for i, station in enumerate(stations):
        print(f"[{i}] {station['name']}")

    try:
        choice = int(input("Wählen Sie einen Bahnhof nach Nummer aus: "))
        return stations[choice]
    except (ValueError, IndexError):
        print("Ungültige Auswahl.")
        return None


def show_departures():
    console = Console()
    selected_station = select_station("Geben Sie einen Bahnhofsnamen für die Suche ein: ")
    if not selected_station:
        return

    station_id = selected_station['id']

    with Live(generate_departures_table(get_departures(station_id)), refresh_per_second=1, screen=True) as live:
        console.print(f"Abfahrten für {selected_station['name']} werden angezeigt. Drücken Sie Strg+C, um zum Menü zurückzukehren.")
        while True:
            try:
                time.sleep(60)
                live.update(generate_departures_table(get_departures(station_id)))
            except KeyboardInterrupt:
                break


def find_journeys():
    console = Console()
    from_station = select_station("Geben Sie den Abfahrtsbahnhof ein: ")
    if not from_station:
        return

    to_station = select_station("Geben Sie den Ankunftsbahnhof ein: ")
    if not to_station:
        return

    journeys = get_journeys(from_station['id'], to_station['id'])
    console.print(generate_journeys_table(journeys))


def main():
    console = Console()
    while True:
        console.print("\n[bold]DB Navigator CLI[/bold]")
        console.print("1. Abfahrten für einen Bahnhof anzeigen")
        console.print("2. Fahrten zwischen zwei Bahnhöfen finden")
        console.print("3. Beenden")
        choice = input("Geben Sie Ihre Wahl ein: ")

        if choice == '1':
            show_departures()
        elif choice == '2':
            find_journeys()
        elif choice == '3':
            print("Wird beendet.")
            break
        else:
            console.print("Ungültige Auswahl. Bitte versuchen Sie es erneut.", style="bold red")


if __name__ == "__main__":
    main()