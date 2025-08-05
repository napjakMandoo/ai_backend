import logging

from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"message": "pong"})

@app.route('/echo', methods=['POST'])
def echo():
    data = request.get_json(force=True)
    return jsonify(data), 201

@app.route('/')
def hello_world():
    return 'Hello World!'

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info("==========앱 시작 ===========")
    app.run(host='0.0.0.0', port=5000, debug=True)
