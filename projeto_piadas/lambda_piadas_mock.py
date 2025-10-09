import json
import random

# Banco de piadas em cache (carregado uma vez por container Lambda)
PIADAS_POR_TEMA = {
    'programação': [
        "Por que os programadores preferem o modo escuro? Porque a luz atrai bugs!",
        "Como você chama um programador que não comenta o código? Um artista abstrato!",
        "Por que o programador foi ao médico? Porque estava com bug!",
        "O que acontece quando você cruza um programador com um vampiro? Um código que só funciona à noite!",
        "Por que programadores odeiam natureza? Porque tem muitos bugs e nenhum debugger!"
    ],
    'javascript': [
        "Por que JavaScript é tão confuso? Porque '1' + '1' é '11', mas '1' - '1' é 0!",
        "Por que JavaScript é como um relacionamento complicado? Porque você nunca sabe se vai retornar undefined ou null!",
        "O que o programador JavaScript disse quando terminou o namoro? 'Isso é undefined!'",
        "Por que arrays em JavaScript começam em 0? Porque os programadores levaram 0 tempo para pensar nisso!",
        "Por que JavaScript foi ao psicólogo? Porque tinha problemas de closure!"
    ],
    'aws': [
        "Por que os desenvolvedores AWS dormem bem? Porque eles têm CloudWatch!",
        "O que o Lambda disse para o API Gateway? 'Você me completa... na requisição!'",
        "Por que S3 é o melhor lugar para guardar segredos? Porque é um bucket list infinito!",
        "Por que o DynamoDB nunca fica estressado? Porque ele escala automaticamente!",
        "O que o EC2 falou para o Lambda? 'Você é serverless, mas eu sou timeless!'"
    ],
    'python': [
        "Por que Python foi ao psicólogo? Porque tinha problemas com indentação!",
        "O que o Python disse para o Java? 'Você tem muitas classes, mas eu tenho mais estilo!'",
        "Por que cobras Python são boas programadoras? Porque elas não precisam de ponto e vírgula!",
        "Por que Python é a linguagem mais zen? Porque 'import this' revela a filosofia!",
        "O que acontece quando Python encontra Java? Um café com cobra!"
    ],
    'café': [
        "Por que programadores bebem tanto café? Porque sem ele, o código fica em modo sleep!",
        "O que o café falou para o programador? 'Sem mim, você é só um comentário!'",
        "Por que o café é como JavaScript? Porque ambos te mantêm acordado a noite toda!",
        "Como o programador faz café? Com Java, obviamente!",
        "Por que o café nunca dá erro? Porque ele sempre compila na primeira tentativa!"
    ],
    'trabalho': [
        "Por que o desenvolvedor levou uma escada para o trabalho? Porque queria subir de nível!",
        "O que o Scrum Master falou para a equipe? 'Vamos fazer um sprint... para o café!'",
        "Por que a reunião de daily foi cancelada? Porque ninguém tinha updates!",
        "Como se chama um desenvolvedor que trabalha de casa? Home office... ou home bug?",
        "Por que o código review é como terapia de casal? Porque sempre tem alguém apontando os problemas!"
    ],
    'geral': [
        "Por que o computador foi ao médico? Porque tinha um vírus!",
        "O que um byte disse para o outro? 'Você está OK?' 'Não, estou meio bit...'",
        "Por que os computadores nunca têm fome? Porque já vêm com chips!",
        "Como se chama um computador que canta? Um Dell!",
        "Por que o mouse foi ao psicólogo? Porque estava com problemas de clique!"
    ]
}

def lambda_handler(event, context):
    print("🎭 Iniciando geração de piada mock...")

    try:
        # GET: Pegar tema da query string
        query_params = event.get('queryStringParameters', {}) or {}
        tema = query_params.get('tema', 'geral')
        print(f"🔍 Parâmetros da query: {query_params}")

        # POST: Pegar tema do body JSON
        # body = json.loads(event.get('body', '{}'))
        # tema = body.get('tema', 'geral')
        # print(f"📋 Body da requisição: {body}")

        print(f"🎯 Tema solicitado: {tema}")

        # Busca piada aleatória do banco em cache
        piada = gerar_piada_mock(tema)

        print("✅ Piada selecionada com sucesso!")

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

def gerar_piada_mock(tema):
    """Seleciona piada aleatória do banco em cache"""
    piadas_tema = PIADAS_POR_TEMA.get(tema.lower(), PIADAS_POR_TEMA['geral'])
    piada_selecionada = random.choice(piadas_tema)

    print(f"🎭 Piada selecionada: {piada_selecionada[:30]}...")

    return piada_selecionada