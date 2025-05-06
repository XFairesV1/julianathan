# pip install Flask SQLAlchemy psycopg2-binary

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

# ───── Flask app setup ─────────────────────────────────────────────────────────
app = Flask(__name__, static_url_path='', static_folder='static')

# ───── Database setup (PostgreSQL via Railway) ─────────────────────────────────
DATABASE_URL = os.environ['DATABASE_URL']
engine       = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base         = declarative_base()

# ───── Models ───────────────────────────────────────────────────────────────────
class Score(Base):
    __tablename__ = 'scores'
    id        = Column(Integer, primary_key=True, index=True)
    player    = Column(String,  index=True, nullable=False)
    game      = Column(String,  index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

class Reset(Base):
    __tablename__ = 'resets'
    id        = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

# Cria as tabelas se não existirem
Base.metadata.create_all(engine)

# ───── Helper functions ─────────────────────────────────────────────────────────
def get_last_reset_date():
    sess = SessionLocal()
    rst  = sess.query(Reset).order_by(Reset.timestamp.desc()).first()
    sess.close()
    return rst.timestamp if rst else None


def get_total_scores():
    sess       = SessionLocal()
    last_reset = get_last_reset_date()
    qry = sess.query(
        Score.player,
        Score.game,
        func.count(Score.id).label('cnt')
    )
    if last_reset:
        qry = qry.filter(Score.timestamp >= last_reset)
    results = qry.group_by(Score.player, Score.game).all()
    sess.close()

    # Monta o dicionário no formato esperado pelo front-end
    scores = {f'{p}-{g}': cnt for p, g, cnt in results}
    for p in ['jonathan','juliana']:
        for g in ['game1','game2','game3']:
            scores.setdefault(f'{p}-{g}', 0)
    return scores

# ───── Endpoints ───────────────────────────────────────────────────────────────
@app.route('/site.webmanifest')
def serve_manifest():
    return send_from_directory('.', 'site.webmanifest', mimetype='application/manifest+json')


@app.route('/')
def index():
    scores       = get_total_scores()
    viewing_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('index.html', scores=scores, viewing_date=viewing_date)


@app.route('/add_point', methods=['POST'])
def add_point():
    player = request.form['player']
    game   = request.form['game']

    sess = SessionLocal()
    sess.add(Score(player=player, game=game, timestamp=datetime.utcnow()))
    sess.commit()
    sess.close()

    totals     = get_total_scores()
    key        = f'{player}-{game}'
    total_user = sum(totals[f'{player}-game{i}'] for i in range(1,4))
    return jsonify({'score': totals[key], 'total_player': total_user})


@app.route('/remove_point', methods=['POST'])
def remove_point():
    player = request.form['player']
    game   = request.form['game']

    sess       = SessionLocal()
    last_reset = get_last_reset_date()
    qry = sess.query(Score).filter_by(player=player, game=game)
    if last_reset:
        qry = qry.filter(Score.timestamp >= last_reset)
    to_delete = qry.order_by(Score.timestamp.desc()).first()

    if not to_delete:
        sess.close()
        return jsonify({'error': 'A pontuação não pode ser menor que zero.'}), 400

    sess.delete(to_delete)
    sess.commit()
    sess.close()

    totals     = get_total_scores()
    key        = f'{player}-{game}'
    total_user = sum(totals[f'{player}-game{i}'] for i in range(1,4))
    return jsonify({'score': totals[key], 'total_player': total_user})


@app.route('/reset_scores', methods=['POST'])
def reset_scores():
    sess = SessionLocal()
    sess.add(Reset(timestamp=datetime.utcnow()))
    sess.commit()
    sess.close()
    return jsonify({'status': 'success'})


@app.route('/load_history', methods=['POST'])
def load_history():
    date_str = request.form['date']  # formato 'YYYY-MM-DD'
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    start    = datetime.combine(date_obj, datetime.min.time())
    end      = datetime.combine(date_obj, datetime.max.time())

    sess    = SessionLocal()
    results = (
        sess.query(Score.player, Score.game, func.count(Score.id).label('cnt'))
            .filter(Score.timestamp.between(start, end))
            .group_by(Score.player, Score.game)
            .all()
    )
    sess.close()

    scores = {f'{p}-{g}': cnt for p, g, cnt in results}
    for p in ['jonathan','juliana']:
        for g in ['game1','game2','game3']:
            scores.setdefault(f'{p}-{g}', 0)

    if results:
        return jsonify({'scores': scores})
    else:
        return jsonify({'error': 'Nenhum registro para esta data.'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
