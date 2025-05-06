from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
from datetime import datetime

app = Flask(__name__, static_url_path='', static_folder='static')

STORAGE_PATH = os.environ.get('STORAGE_PATH', '/app/data')
os.makedirs(STORAGE_PATH, exist_ok=True)

DATA_FILE = os.path.join(STORAGE_PATH, 'scores.json')
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'  # Include time in the date format


def load_data():
    data = None
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {
            'total_scores': {
                'jonathan-game1': 0, 'juliana-game1': 0,
                'jonathan-game2': 0, 'juliana-game2': 0,
                'jonathan-game3': 0, 'juliana-game3': 0
            },
            'daily_scores': {},
            'last_reset_date': None
        }

    # Recalculate total_scores from daily_scores, considering last_reset_date
    total_scores = {
        'jonathan-game1': 0, 'juliana-game1': 0,
        'jonathan-game2': 0, 'juliana-game2': 0,
        'jonathan-game3': 0, 'juliana-game3': 0
    }

    last_reset_date_str = data.get('last_reset_date')
    if last_reset_date_str:
        last_reset_date = datetime.strptime(last_reset_date_str, DATE_FORMAT)
    else:
        last_reset_date = None

    for date_str, scores in data['daily_scores'].items():
        date_obj = datetime.strptime(date_str, DATE_FORMAT)
        if last_reset_date is None or date_obj >= last_reset_date:
            for key, value in scores.items():
                total_scores[key] += value

    data['total_scores'] = total_scores
    return data


def save_data(data):
    # Recalculate total_scores from daily_scores, considering last_reset_date
    total_scores = {
        'jonathan-game1': 0, 'juliana-game1': 0,
        'jonathan-game2': 0, 'juliana-game2': 0,
        'jonathan-game3': 0, 'juliana-game3': 0
    }

    last_reset_date_str = data.get('last_reset_date')
    if last_reset_date_str:
        last_reset_date = datetime.strptime(last_reset_date_str, DATE_FORMAT)
    else:
        last_reset_date = None

    for date_str, scores in data['daily_scores'].items():
        date_obj = datetime.strptime(date_str, DATE_FORMAT)
        if last_reset_date is None or date_obj >= last_reset_date:
            for key, value in scores.items():
                total_scores[key] += value

    data['total_scores'] = total_scores
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


@app.route('/site.webmanifest')
def serve_manifest():
    return send_from_directory('.', 'site.webmanifest', mimetype='application/manifest+json')


@app.route('/')
def index():
    # Display the total accumulated scores
    data = load_data()
    scores = data.get('total_scores', {
        'jonathan-game1': 0, 'juliana-game1': 0,
        'jonathan-game2': 0, 'juliana-game2': 0,
        'jonathan-game3': 0, 'juliana-game3': 0
    })
    viewing_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('index.html', scores=scores, viewing_date=viewing_date)


@app.route('/add_point', methods=['POST'])
def add_point():
    data = load_data()
    player = request.form['player']
    game = request.form['game']
    date = request.form.get('date', datetime.now().strftime(DATE_FORMAT))

    # Update daily_scores
    daily_scores = data.get('daily_scores', {})
    if date not in daily_scores:
        daily_scores[date] = {
            'jonathan-game1': 0, 'juliana-game1': 0,
            'jonathan-game2': 0, 'juliana-game2': 0,
            'jonathan-game3': 0, 'juliana-game3': 0
        }
    key = f'{player}-{game}'
    daily_scores[date][key] += 1
    data['daily_scores'] = daily_scores

    save_data(data)

    total_player = sum(data['total_scores'].get(f'{player}-game{i}', 0) for i in range(1, 4))

    return jsonify({'score': data['total_scores'][key], 'total_player': total_player})


@app.route('/remove_point', methods=['POST'])
def remove_point():
    data = load_data()
    player = request.form['player']
    game = request.form['game']
    date = request.form.get('date', datetime.now().strftime(DATE_FORMAT))

    # Update daily_scores
    daily_scores = data.get('daily_scores', {})
    if date not in daily_scores:
        return jsonify({'error': 'Nenhuma pontuação para esta data para remover.'}), 400

    key = f'{player}-{game}'
    if daily_scores[date][key] > 0:
        daily_scores[date][key] -= 1
        data['daily_scores'] = daily_scores
        save_data(data)

        total_player = sum(data['total_scores'].get(f'{player}-game{i}', 0) for i in range(1, 4))

        return jsonify({'score': data['total_scores'][key], 'total_player': total_player})
    else:
        return jsonify({'error': 'A pontuação não pode ser menor que zero.'}), 400


@app.route('/reset_scores', methods=['POST'])
def reset_scores():
    data = load_data()
    # Set the last reset date with time
    data['last_reset_date'] = datetime.now().strftime(DATE_FORMAT)
    save_data(data)
    return jsonify({'status': 'success'})


@app.route('/load_history', methods=['POST'])
def load_history():
    data = load_data()
    date = request.form['date']
    daily_scores = data.get('daily_scores', {})

    # Initialize an empty score dictionary
    aggregated_scores = {
        'jonathan-game1': 0, 'juliana-game1': 0,
        'jonathan-game2': 0, 'juliana-game2': 0,
        'jonathan-game3': 0, 'juliana-game3': 0
    }

    # Aggregate scores for the selected date
    found = False
    for date_str, score_data in daily_scores.items():
        date_obj = datetime.strptime(date_str, DATE_FORMAT)
        if date_obj.strftime('%Y-%m-%d') == date:
            found = True
            for key, value in score_data.items():
                aggregated_scores[key] += value

    if found:
        return jsonify({'scores': aggregated_scores})
    else:
        return jsonify({'error': 'Nenhum registro para esta data.'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
