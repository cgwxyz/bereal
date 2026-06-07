from flask import Flask, jsonify, request, render_template
from playground.watermark import gen_watermark
import traceback

app = Flask(__name__)


@app.route('/')
def index():
  return render_template('index.html')


@app.route('/manual')
def manual():
  return render_template('manual.html')


@app.route('/healthcheck')
def healthcheck():
  return '', 200


@app.route('/watermark', methods=['POST'])
def watermark():
  params = request.get_json()
  personal_token = params.get('personal_token', '')
  app_token = params.get('app_token', '')
  table_id = params.get('table_id', '')
  if not personal_token or not app_token or not table_id:
    return jsonify({'sta': -1, "msg": "no auth params assigned"})

  record_id = params.get('record_id', '')
  source_field = params.get('source_field', '')
  t_submit_field = params.get('t_submit_field', '')
  if not t_submit_field:
    return jsonify({'sta': -1, "msg": "no t_submit field assigned"})
  if not source_field:
    return jsonify({'sta': -1, "msg": "no source field assigned"})

  target_field = params.get('target_field', '')
  if not target_field:
    return jsonify({'sta': -1, "msg": "no target field assigned"})
  location_field = params.get('location_field', '')
  watermark_fields = params.get('watermark_fields', [])
  if isinstance(watermark_fields, str):
    watermark_fields = [watermark_fields] if watermark_fields else []
  try:
    gen_watermark(personal_token, app_token, table_id, record_id,
                  t_submit_field, source_field, target_field, location_field,
                  watermark_fields)
  except Exception as e:
    print('get excep:%s,%s' % (e, traceback.format_exc()))
  return jsonify({'sta': 1, "msg": "ok"})


app.run(host='0.0.0.0', port=81)
