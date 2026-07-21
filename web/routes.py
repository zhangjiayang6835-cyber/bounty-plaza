from flask import render_template, request, redirect, url_for
from web.game_mechanics import DailyQuests
from web.game_events import GameEvents

daily_quests = DailyQuests()
game_events = GameEvents()

@app.route('/daily_quests/<int:player_id>')
def show_daily_quests(player_id):
    quest = game_events.trigger_daily_quest_event(player_id)
    return render_template('daily_quests.html', quest=quest)

@app.route('/complete_quest', methods=['POST'])
def complete_quest():
    player_id = request.form.get('player_id')
    quest_id = request.form.get('quest_id')

    if daily_quests.complete_quest(player_id):
        # Quest completed successfully
        pass

    return redirect(url_for('show_daily_quests', player_id=player_id))