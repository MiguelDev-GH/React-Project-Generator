python
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app_universal = Flask(__name__)
CORS(app_universal)

app_generico = {
    "status_sistema": "ativo",
    "colecao_dados": []
}

app_universal.config['JSON_AS_ASCII'] = False
app_universal.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'universal_secret_key_9988')

@app_universal.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "app": "Universal App Service",
        "version": "1.0.0",
        "endpoints_disponiveis": ["/", "/api/v1/data"],
        "contexto": "app_generico"
    }), 200

@app_universal.route('/api/v1/data', methods=['GET'])
def get_data():
    try:
        return jsonify({
            "sucesso": True,
            "data": "Dados recuperados com sucesso do app_universal.",
            "colecao": app_generico
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app_universal.route('/api/v1/submit', methods=['POST'])
def submit_data():
    if not request.is_json:
        return jsonify({"erro": "O payload deve ser JSON"}), 400
    
    dados_recebidos = request.get_json()
    app_generico["colecao_dados"].append(dados_recebidos)
    
    return jsonify({
        "status": "processado",
        "recebido": dados_recebidos,
        "total_registros": len(app_generico["colecao_dados"])
    }), 201

@app_universal.errorhandler(404)
def handle_404(e):
    return jsonify({"erro": "Rota não encontrada"}), 404

@app_universal.errorhandler(500)
def handle_500(e):
    return jsonify({"erro": "Erro interno no servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app_universal.run(host='0.0.0.0', port=port, debug=True)