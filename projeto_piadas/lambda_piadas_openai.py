import json
import os
import urllib3

def lambda_handler(event, context):
    print("🎭 Iniciando lambda_handler de piadas...")

    try:
        # GET: Pegar tema da query string
        query_params = event.get('queryStringParameters', {}) or {}
        tema = query_params.get('tema', 'aws')
        print(f"🔍 Parâmetros da query: {query_params}")

        # POST: Pegar tema do body JSON
        # body = json.loads(event.get('body', '{}'))
        # tema = body.get('tema', 'aws')
        # print(f"📋 Body da requisição: {body}")

        # Cria piada usando API de IA
        piada = gerar_piada_openai(tema)

        print("✅ Piada gerada com sucesso!")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'tema': tema,
                'piada': piada,
            }, ensure_ascii=False)
        }

    except Exception as e:
        print(f"❌ Erro: {str(e)}")

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'erro': 'Erro ao gerar piada',
                'detalhes': str(e)
            })
        }

def gerar_piada_openai(tema):
    """Chama API de IA para gerar piada personalizada"""

    # Configurações das variáveis de ambiente
    api_key = os.environ.get('OPENAI_API_KEY')
    api_url = os.environ.get('OPENAI_API_URL', 'https://api.openai.com/v1')
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        raise Exception("OPENAI_API_KEY não encontrada!")

    print(f"🤖 Chamando IA - Modelo: {model}")
    print(f"🌐 URL: {api_url}")

    url = f"{api_url}/chat/completions"

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Você é um comediante brasileiro profissional. Crie piadas curtas, engraçadas e apropriadas para todas as idades. Use humor inteligente e evite temas sensíveis."
            },
            {
                "role": "user",
                "content": f"Crie uma piada curta e engraçada sobre: {tema}"
            }
        ],
        "max_tokens": 150,
        "temperature": 0.9
    }

    # Faz requisição HTTP
    http = urllib3.PoolManager()

    try:
        response = http.request(
            'POST',
            url,
            body=json.dumps(data),
            headers=headers,
            timeout=30
        )

        print(f"📡 Status da resposta: {response.status}")

        if response.status != 200:
            raise Exception(f"Erro na API: Status {response.status}")

        # Processa resposta
        response_data = json.loads(response.data.decode('utf-8'))
        piada = response_data['choices'][0]['message']['content'].strip()

        print(f"🎭 Piada recebida: {piada[:50]}...")

        return piada

    except Exception as e:
        print(f"💥 Erro na chamada da API: {str(e)}")
        raise e