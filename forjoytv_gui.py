from datetime import datetime, timedelta
import calendar
# import locale
# locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

import sqlite3

from nicegui import ui

dbfile = "./forjoytv.db" 

ui.table.default_props('flat dense bordered separator="cell" hide-selected-banner="1"')

def handle_row_click(table, e):
    table.selected[:] = [e.args[1]]
    table.update()
    resultstable.refresh()

@ui.refreshable
def resultstable(cur, channeltable, daystable):
    table = ui.table(columns=None, rows=[]).props('loading')
    shows = cur.execute('SELECT * FROM shows;').fetchall()
    table.add_slot('no-data', r'''
        <div class="full-width row flex-center q-gutter-sm">
          <q-icon size="2em" name="sentiment_dissatisfied" />
          <span>
            Bitte Kanal und Tag wählen.
          </span>
        </div>''')
    table.props(remove='loading')
    #if len(channeltable.selected)==0: 
    #    ui.label("Bitte einen Kanal wählen.")
    #else:
    #    ii.label("")
    #if len(daystable.selected)==0: 
    #    ui.label("Bitte einen Tag wählen.")
    #else:
    #    ui.label("")
    #ui.label(len(shows))
    return table

@ui.page('/', title="ForJoyTV EPG")
def index():
    with ui.header(elevated=True).style('background-color: #3874c8').classes('items-center justify-between'):
        ui.label('ForJoyTV EPG Suche')
        with ui.input(placeholder='Suchbegriff eingeben (Kanäle und Sendungen)') \
               .props('input-style="width: 40em" rounded outlined dense bg-color="white" clearable white-space="nowrap" width="25%"') \
               .add_slot('prepend'):
            ui.icon(name='search').props('flat dense')
        result = ui.label()
        #ui.button(on_click=lambda: right_drawer.toggle(), icon='menu').props('flat color=white')

    con = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
   
    with ui.grid(columns=3):
        # Column 1 - Channel
        channels = cur.execute('SELECT * FROM channels;').fetchall()
        channelrows = [ {'#': number, 'name': name, 'beschreibung': description} for (number, name, description) in channels]
        channeltable = ui.table(columns=None, rows=channelrows, row_key='#', pagination=10)
        channeltable.on('rowClick', lambda e: handle_row_click(channeltable, e))
        # Column 2 - Days
        min_date, max_date = map(lambda d:datetime.fromtimestamp(d).date(),
                                cur.execute('SELECT unixepoch(min(time)) as min_time, unixepoch(max(time)) as max_time FROM shows;').fetchone())
        
        dayrows = [{'Wochentag':calendar.day_name[date.weekday()], 'Datum': date} \
                  for date in [min_date + timedelta(days=x) \
                              for x in range(0, (max_date-min_date).days)]]
        daystable=ui.table(columns=None, rows=dayrows, row_key='Datum', pagination=10)
        daystable.on('rowClick', lambda e: handle_row_click(daystable, e))

        # Column 3 - Shows
        resultstable(cur, channeltable, daystable)

ui.run(language="de-DE")
