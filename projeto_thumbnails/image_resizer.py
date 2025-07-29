import json
import boto3
import os
from PIL import Image
from io import BytesIO
import urllib.parse

# Cliente AWS
s3_client = boto3.client('s3')

# Configurações de redimensionamento (largura máxima)
SIZES = {
    'small': 300,   # Para thumbnails
    'medium': 800   # Para visualização normal
}

def resize_image(image, max_width):
    """Redimensiona imagem mantendo proporção"""
    # Se a imagem já é menor que o máximo, não redimensiona
    if image.width <= max_width:
        return image

    # Calcula nova altura mantendo proporção
    ratio = max_width / image.width
    new_height = int(image.height * ratio)

    # Redimensiona
    return image.resize((max_width, new_height), Image.Resampling.LANCZOS)

def lambda_handler(event, context):
    print("🚀 Iniciando processamento de imagem...")

    # Processa cada registro do evento S3
    for record in event['Records']:
        # Extrai informações do evento
        bucket_name = record['s3']['bucket']['name']
        object_key = urllib.parse.unquote_plus(
            record['s3']['object']['key'],
            encoding='utf-8'
        )

        print(f"📁 Bucket: {bucket_name}")
        print(f"🖼️  Arquivo: {object_key}")

        # Só processa se for da pasta 'original/'
        if not object_key.startswith('original/'):
            print("⏭️  Arquivo não está na pasta 'original/', ignorando...")
            continue

        try:
            # Baixa imagem original do S3
            print("⬇️  Baixando imagem original...")
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            image_data = response['Body'].read()

            # Abre imagem com Pillow
            original_image = Image.open(BytesIO(image_data))
            print(f"📐 Dimensões originais: {original_image.size}")

            # Converte para RGB se necessário (para JPEGs)
            if original_image.mode != 'RGB':
                original_image = original_image.convert('RGB')

            # Extrai nome do arquivo
            file_name = os.path.basename(object_key)

            # Redimensiona para cada tamanho
            for size_name, max_width in SIZES.items():
                print(f"🔄 Redimensionando para {size_name} (max {max_width}px)...")

                # Redimensiona mantendo proporção
                resized_image = resize_image(original_image.copy(), max_width)
                print(f"📏 Novas dimensões: {resized_image.size}")

                # Converte para bytes
                output_buffer = BytesIO()
                resized_image.save(output_buffer, format='JPEG', quality=85)
                output_buffer.seek(0)

                # Caminho de destino
                destination_key = f"{size_name}/{file_name}"

                # Upload para S3
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=destination_key,
                    Body=output_buffer.getvalue(),
                    ContentType='image/jpeg'
                )

                print(f"✅ Salvo: {destination_key}")

            print("🎉 Processamento concluído com sucesso!")

        except Exception as e:
            print(f"❌ Erro ao processar {object_key}: {str(e)}")
            raise e

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Imagens redimensionadas com sucesso!',
            'processed_files': len(event['Records'])
        })
    }