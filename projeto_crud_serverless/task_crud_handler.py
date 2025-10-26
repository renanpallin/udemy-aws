import json
import boto3
import uuid
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key, Attr

# Configuração DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Tasks')

def lambda_handler(event, context):
    """
    📝 Tasks CRUD API
    Estrutura da tabela:
    - Partition Key: user_id (ex: "user001")
    - Sort Key: created_at (timestamp ISO)
    - Atributos: uuid (UUID), description, done
    """

    print(f"📝 Evento recebido: {json.dumps(event)}")

    method = event['httpMethod']
    path_params = event.get('pathParameters') or {}

    try:
        if method == 'POST':
            return create_task(event)
        elif method == 'GET':
            if path_params.get('uuid'):
                return get_task_by_uuid(event)
            else:
                return list_tasks(event)
        elif method == 'PUT':
            return update_task(event)
        elif method == 'DELETE':
            return delete_task(event)
        elif method == 'OPTIONS':
            return options_response()
        else:
            return error_response(405, f'Método {method} não permitido')

    except Exception as e:
        print(f"❌ Erro não tratado: {str(e)}")
        return error_response(500, f'Erro interno: {str(e)}')

def create_task(event):
    """
    ➕ Criar nova task
    POST /tasks
    """
    print("➕ Criando nova task...")

    try:
        body = json.loads(event['body'])
    except:
        return error_response(400, 'JSON inválido no body da requisição')

    # Queremos sempre um description nas nossas tasks
    if 'description' not in body or not body['description'].strip():
        return error_response(400, 'Campo "description" é obrigatório')

    # Gerar timestamp para Sort Key e UUID único
    created_at = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())

    # Estrutura profissional: user_id (PK) + created_at (SK)
    item = {
        'user_id': 'user001',                # Partition Key (mock)
        'created_at': created_at,            # Sort Key (timestamp)
        'uuid': task_id,                     # UUID único para referência
        'description': body['description'].strip(),
        'done': bool(body.get('done', False))
    }

    try:
        table.put_item(Item=item)
        print(f"✅ Task criada: {item['description']} (ID: {task_id})")

        return success_response(201, {
            'message': '📝 Task criada com sucesso!',
            'task': format_task_response(item)
        })

    except Exception as e:
        print(f"❌ Erro ao salvar no DynamoDB: {str(e)}")
        return error_response(500, f'Erro ao salvar task: {str(e)}')

def list_tasks(event):
    """
    📋 Listar tasks do usuário com ordenação nativa
    GET /tasks
    """
    print("📋 Listando tasks do user001...")

    try:
        # Busca todas as tasks do usuário
        response = table.query(
            KeyConditionExpression=Key('user_id').eq('user001'),
            ScanIndexForward=False  # Ordem decrescente (mais recente primeiro)
        )

        items = response['Items']

        print(f"✅ Encontradas {len(items)} tasks (ordenadas nativamente)")

        return success_response(200, {
            'tasks': [format_task_response(item) for item in items],
            'total': len(items)
        })

    except Exception as e:
        print(f"❌ Erro ao listar tasks: {str(e)}")
        return error_response(500, f'Erro ao listar tasks: {str(e)}')

def get_task_by_uuid(event):
    """
    🔍 Buscar task específica por UUID
    GET /tasks/{uuid}
    """
    task_id = event['pathParameters']['uuid']
    print(f"🔍 Buscando task específica: {task_id}")

    # Buscar task pelo UUID
    task = find_task_by_id(task_id)

    if not task:
        print(f"❌ Task não encontrada: {task_id}")
        return error_response(404, f'Task "{task_id}" não encontrada')

    print(f"✅ Task encontrada: {task['description']}")

    return success_response(200, {
        'task': format_task_response(task)
    })

def update_task(event):
    """
    ✏️ Atualizar task existente
    PUT /tasks/{uuid}
    """
    task_id = event['pathParameters']['uuid']
    print(f"✏️ Atualizando task: {task_id}")

    try:
        body = json.loads(event['body'])
    except:
        return error_response(400, 'JSON inválido no body da requisição')

    # Buscar task atual pelo UUID
    current_item = find_task_by_id(task_id)
    if not current_item:
        return error_response(404, f'Task "{task_id}" não encontrada')

    # Atualizar campos fornecidos
    if 'description' in body and body['description'].strip():
        current_item['description'] = body['description'].strip()

    if 'done' in body:
        current_item['done'] = bool(body['done'])

    try:
        table.put_item(Item=current_item)

        print(f"✅ Task atualizada: {current_item['description']}")

        return success_response(200, {
            'message': '✏️ Task atualizada com sucesso!',
            'task': format_task_response(current_item)
        })

    except Exception as e:
        print(f"❌ Erro ao atualizar task: {str(e)}")
        return error_response(500, f'Erro ao atualizar task: {str(e)}')

def delete_task(event):
    """
    🗑️ Deletar task
    DELETE /tasks/{uuid}
    """
    task_id = event['pathParameters']['uuid']
    print(f"🗑️ Deletando task: {task_id}")

    # Buscar task para pegar as chaves primárias
    current_item = find_task_by_id(task_id)
    if not current_item:
        return error_response(404, f'Task "{task_id}" não encontrada')

    task_description = current_item['description']

    try:
        # Deletar usando as chaves primárias (user_id + created_at)
        table.delete_item(
            Key={
                'user_id': current_item['user_id'],
                'created_at': current_item['created_at']
            }
        )

        print(f"✅ Task deletada: {task_description}")

        return success_response(200, {
            'message': f'🗑️ Task "{task_description}" removida com sucesso!',
            'deleted_uuid': task_id
        })

    except Exception as e:
        print(f"❌ Erro ao deletar task: {str(e)}")
        return error_response(500, f'Erro ao deletar task: {str(e)}')

def find_task_by_id(task_id):
    """
    🔍 Buscar task pelo UUID
    """
    try:
        response = table.query(
            KeyConditionExpression=Key('user_id').eq('user001'),
            FilterExpression=Attr('uuid').eq(task_id)
        )

        return response['Items'][0] if response['Items'] else None

    except Exception as e:
        print(f"❌ Erro ao buscar task: {str(e)}")
        return None

def format_task_response(item):
    """
    🎨 Formatar resposta para o cliente
    Converte UTC para horário brasileiro apenas na apresentação
    """
    # Converter UTC para horário brasileiro (UTC-3)
    utc_time = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
    brazil_tz = timezone(timedelta(hours=-3))
    brazil_time = utc_time.astimezone(brazil_tz)

    return {
        'uuid': item['uuid'],
        'description': item['description'],
        'done': item['done'],
        'created_at': brazil_time.strftime('%d/%m/%Y %H:%M:%S')  # Formato brasileiro legível
    }

def success_response(status_code, data):
    """
    ✅ Resposta de sucesso padronizada
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(data, default=str)
    }

def error_response(status_code, message):
    """
    ❌ Resposta de erro padronizada
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    }

def options_response():
    """
    🔧 Resposta para requisições OPTIONS (CORS preflight)
    """
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '86400'
        },
        'body': ''
    }
