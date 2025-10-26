import json
import boto3
import uuid
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key, Attr

# 🔍 X-Ray Imports e Configuração
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Instrumentar automaticamente AWS SDK (DynamoDB, etc.)
patch_all()

# Configuração DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Tasks')

@xray_recorder.capture('lambda_handler')
def lambda_handler(event, context):
    """
    📝 Tasks CRUD API com X-Ray Tracing
    Estrutura da tabela:
    - Partition Key: user_id (ex: "user001")
    - Sort Key: created_at (timestamp ISO)
    - Atributos: uuid (UUID), description, done
    """

    # 🔍 X-Ray: Adicionar informações do request
    xray_recorder.put_annotation('http_method', event['httpMethod'])
    xray_recorder.put_annotation('user_agent', event.get('headers', {}).get('User-Agent', 'unknown'))

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
            # 🔍 X-Ray: Marcar erro
            xray_recorder.put_annotation('error', 'method_not_allowed')
            return error_response(405, f'Método {method} não permitido')

    except Exception as e:
        # 🔍 X-Ray: Capturar exceções
        xray_recorder.put_annotation('error', 'unhandled_exception')
        xray_recorder.put_metadata('exception_details', {
            'error_message': str(e),
            'error_type': type(e).__name__
        })

        print(f"❌ Erro não tratado: {str(e)}")
        return error_response(500, f'Erro interno: {str(e)}')

@xray_recorder.capture('create_task')
def create_task(event):
    """
    ➕ Criar nova task
    POST /tasks
    """
    # 🔍 X-Ray: Marcar operação
    xray_recorder.put_annotation('operation', 'create_task')

    print("➕ Criando nova task...")

    try:
        body = json.loads(event['body'])

        # 🔍 X-Ray: Adicionar dados do request
        xray_recorder.put_metadata('request_body', {
            'description_length': len(body.get('description', '')),
            'done': body.get('done', False)
        })

    except:
        xray_recorder.put_annotation('error', 'invalid_json')
        return error_response(400, 'JSON inválido no body da requisição')

    # Queremos sempre um description nas nossas tasks
    if 'description' not in body or not body['description'].strip():
        xray_recorder.put_annotation('error', 'missing_description')
        return error_response(400, 'Campo "description" é obrigatório')

    # Gerar timestamp para Sort Key e UUID único
    created_at = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())

    # 🔍 X-Ray: Adicionar informações da task
    xray_recorder.put_annotation('task_id', task_id)
    xray_recorder.put_metadata('task_details', {
        'uuid': task_id,
        'description': body['description'][:50] + '...' if len(body['description']) > 50 else body['description'],
        'created_at': created_at
    })

    # Estrutura profissional: user_id (PK) + created_at (SK)
    item = {
        'user_id': 'user001',                # Partition Key (mock)
        'created_at': created_at,            # Sort Key (timestamp)
        'uuid': task_id,                     # UUID único para referência
        'description': body['description'].strip(),
        'done': bool(body.get('done', False))
    }

    try:
        # 🔍 X-Ray: Subsegmento para operação DynamoDB
        with xray_recorder.in_subsegment('dynamodb_put_item'):
            table.put_item(Item=item)

        print(f"✅ Task criada: {item['description']} (ID: {task_id})")

        # 🔍 X-Ray: Marcar sucesso
        xray_recorder.put_annotation('success', True)

        return success_response(201, {
            'message': '📝 Task criada com sucesso!',
            'task': format_task_response(item)
        })

    except Exception as e:
        # 🔍 X-Ray: Marcar erro do DynamoDB
        xray_recorder.put_annotation('error', 'dynamodb_error')
        xray_recorder.put_metadata('dynamodb_error', str(e))

        print(f"❌ Erro ao salvar no DynamoDB: {str(e)}")
        return error_response(500, f'Erro ao salvar task: {str(e)}')

@xray_recorder.capture('list_tasks')
def list_tasks(event):
    """
    📋 Listar tasks do usuário com ordenação nativa
    GET /tasks
    """
    # 🔍 X-Ray: Marcar operação
    xray_recorder.put_annotation('operation', 'list_tasks')

    print("📋 Listando tasks do user001...")

    try:
        # 🔍 X-Ray: Subsegmento para query DynamoDB
        with xray_recorder.in_subsegment('dynamodb_query'):
            # Busca todas as tasks do usuário
            response = table.query(
                KeyConditionExpression=Key('user_id').eq('user001'),
                ScanIndexForward=False  # Ordem decrescente (mais recente primeiro)
            )

        items = response['Items']

        # 🔍 X-Ray: Adicionar métricas
        xray_recorder.put_annotation('tasks_count', len(items))
        xray_recorder.put_metadata('query_result', {
            'total_tasks': len(items),
            'consumed_capacity': response.get('ConsumedCapacity', 'N/A')
        })

        print(f"✅ Encontradas {len(items)} tasks (ordenadas nativamente)")

        return success_response(200, {
            'tasks': [format_task_response(item) for item in items],
            'total': len(items)
        })

    except Exception as e:
        # 🔍 X-Ray: Marcar erro
        xray_recorder.put_annotation('error', 'query_failed')
        xray_recorder.put_metadata('query_error', str(e))

        print(f"❌ Erro ao listar tasks: {str(e)}")
        return error_response(500, f'Erro ao listar tasks: {str(e)}')

@xray_recorder.capture('get_task_by_uuid')
def get_task_by_uuid(event):
    """
    🔍 Buscar task específica por UUID
    GET /tasks/{uuid}
    """
    task_id = event['pathParameters']['uuid']

    # 🔍 X-Ray: Marcar operação e task ID
    xray_recorder.put_annotation('operation', 'get_task_by_uuid')
    xray_recorder.put_annotation('requested_task_id', task_id)

    print(f"🔍 Buscando task específica: {task_id}")

    # Buscar task pelo UUID
    task = find_task_by_id(task_id)

    if not task:
        # 🔍 X-Ray: Marcar task não encontrada
        xray_recorder.put_annotation('task_found', False)

        print(f"❌ Task não encontrada: {task_id}")
        return error_response(404, f'Task "{task_id}" não encontrada')

    # 🔍 X-Ray: Marcar sucesso
    xray_recorder.put_annotation('task_found', True)
    xray_recorder.put_metadata('found_task', {
        'description': task['description'][:50] + '...' if len(task['description']) > 50 else task['description'],
        'done': task['done']
    })

    print(f"✅ Task encontrada: {task['description']}")

    return success_response(200, {
        'task': format_task_response(task)
    })

@xray_recorder.capture('update_task')
def update_task(event):
    """
    ✏️ Atualizar task existente
    PUT /tasks/{uuid}
    """
    task_id = event['pathParameters']['uuid']

    # 🔍 X-Ray: Marcar operação
    xray_recorder.put_annotation('operation', 'update_task')
    xray_recorder.put_annotation('task_id', task_id)

    print(f"✏️ Atualizando task: {task_id}")

    try:
        body = json.loads(event['body'])

        # 🔍 X-Ray: Adicionar dados da atualização
        xray_recorder.put_metadata('update_request', {
            'fields_to_update': list(body.keys()),
            'description_changed': 'description' in body,
            'done_changed': 'done' in body
        })

    except:
        xray_recorder.put_annotation('error', 'invalid_json')
        return error_response(400, 'JSON inválido no body da requisição')

    # Buscar task atual pelo UUID
    current_item = find_task_by_id(task_id)
    if not current_item:
        xray_recorder.put_annotation('error', 'task_not_found')
        return error_response(404, f'Task "{task_id}" não encontrada')

    # Atualizar campos fornecidos
    if 'description' in body and body['description'].strip():
        current_item['description'] = body['description'].strip()

    if 'done' in body:
        current_item['done'] = bool(body['done'])

    try:
        # 🔍 X-Ray: Subsegmento para update
        with xray_recorder.in_subsegment('dynamodb_update'):
            table.put_item(Item=current_item)

        print(f"✅ Task atualizada: {current_item['description']}")

        # 🔍 X-Ray: Marcar sucesso
        xray_recorder.put_annotation('update_successful', True)

        return success_response(200, {
            'message': '✏️ Task atualizada com sucesso!',
            'task': format_task_response(current_item)
        })

    except Exception as e:
        # 🔍 X-Ray: Marcar erro
        xray_recorder.put_annotation('error', 'update_failed')
        xray_recorder.put_metadata('update_error', str(e))

        print(f"❌ Erro ao atualizar task: {str(e)}")
        return error_response(500, f'Erro ao atualizar task: {str(e)}')

@xray_recorder.capture('delete_task')
def delete_task(event):
    """
    🗑️ Deletar task
    DELETE /tasks/{uuid}
    """
    task_id = event['pathParameters']['uuid']

    # 🔍 X-Ray: Marcar operação
    xray_recorder.put_annotation('operation', 'delete_task')
    xray_recorder.put_annotation('task_id', task_id)

    print(f"🗑️ Deletando task: {task_id}")

    # Buscar task para pegar as chaves primárias
    current_item = find_task_by_id(task_id)
    if not current_item:
        xray_recorder.put_annotation('error', 'task_not_found')
        return error_response(404, f'Task "{task_id}" não encontrada')

    task_description = current_item['description']

    # 🔍 X-Ray: Adicionar informações da task a ser deletada
    xray_recorder.put_metadata('task_to_delete', {
        'description': task_description[:50] + '...' if len(task_description) > 50 else task_description,
        'done': current_item['done']
    })

    try:
        # 🔍 X-Ray: Subsegmento para delete
        with xray_recorder.in_subsegment('dynamodb_delete'):
            # Deletar usando as chaves primárias (user_id + created_at)
            table.delete_item(
                Key={
                    'user_id': current_item['user_id'],
                    'created_at': current_item['created_at']
                }
            )

        print(f"✅ Task deletada: {task_description}")

        # 🔍 X-Ray: Marcar sucesso
        xray_recorder.put_annotation('delete_successful', True)

        return success_response(200, {
            'message': f'🗑️ Task "{task_description}" removida com sucesso!',
            'deleted_uuid': task_id
        })

    except Exception as e:
        # 🔍 X-Ray: Marcar erro
        xray_recorder.put_annotation('error', 'delete_failed')
        xray_recorder.put_metadata('delete_error', str(e))

        print(f"❌ Erro ao deletar task: {str(e)}")
        return error_response(500, f'Erro ao deletar task: {str(e)}')

@xray_recorder.capture('find_task_by_id')
def find_task_by_id(task_id):
    """
    🔍 Buscar task pelo UUID
    """
    try:
        # 🔍 X-Ray: Subsegmento para busca
        with xray_recorder.in_subsegment('dynamodb_find_by_uuid'):
            response = table.query(
                KeyConditionExpression=Key('user_id').eq('user001'),
                FilterExpression=Attr('uuid').eq(task_id)
            )

        # 🔍 X-Ray: Adicionar resultado da busca
        found = len(response['Items']) > 0
        xray_recorder.put_annotation('task_found_in_search', found)

        return response['Items'][0] if response['Items'] else None

    except Exception as e:
        # 🔍 X-Ray: Marcar erro na busca
        xray_recorder.put_annotation('error', 'search_failed')
        xray_recorder.put_metadata('search_error', str(e))

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
